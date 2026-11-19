"""
Service layer for Notifications & Announcements in CampusOS LMS (SRS Section 3.G).
Encapsulates persistent notification records, Channels WebSocket event dispatching,
announcement audience resolution, and academic lifecycle event triggers.
"""

import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from apps.academics.models import CourseOffering, Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile
from .models import Announcement, AnnouncementScope, AudienceType, Notification, NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Coordinator for persistent notifications, real-time WebSocket delivery,
    and announcement broadcasts across institutional audiences.
    """

    @classmethod
    def _dispatch_channel_event(cls, group_name: str, message_type: str, payload: dict) -> None:
        """
        Dispatches an event to a Django Channels group.
        Safely catches exceptions so WebSocket failures never break calling transactions.
        """
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        "type": message_type,
                        payload.get("envelope_key", "notification"): payload.get("data", {}),
                    },
                )
        except Exception as exc:
            logger.warning("Channel layer dispatch failed for group %s: %s", group_name, exc)

    @classmethod
    def send_notification(
        cls,
        recipient_user_id: str,
        title: str,
        message: str,
        notification_type: str = NotificationType.GENERAL,
        data: dict = None,
    ) -> Notification:
        """
        Creates a persistent Notification row in PostgreSQL and dispatches
        a real-time event to the user's personal WebSocket group channel.
        """
        data = data or {}
        notification = Notification.objects.create(
            recipient_user_id=str(recipient_user_id),
            title=title,
            message=message,
            notification_type=notification_type,
            data=data,
        )

        payload = {
            "id": notification.id,
            "recipient_user_id": notification.recipient_user_id,
            "title": notification.title,
            "message": notification.message,
            "notification_type": notification.notification_type,
            "is_read": notification.is_read,
            "data": notification.data,
            "created_at": notification.created_at.isoformat(),
        }

        cls._dispatch_channel_event(
            group_name=f"user_{notification.recipient_user_id}",
            message_type="notification.message",
            payload={"envelope_key": "notification", "data": payload},
        )

        return notification

    @classmethod
    def send_bulk_notifications(
        cls,
        recipient_user_ids: list[str],
        title: str,
        message: str,
        notification_type: str = NotificationType.GENERAL,
        data: dict = None,
    ) -> list[Notification]:
        """
        Bulk creates persistent notifications and dispatches real-time events to each recipient.
        """
        data = data or {}
        distinct_ids = [str(uid) for uid in set(recipient_user_ids) if uid]
        if not distinct_ids:
            return []

        notifications = [
            Notification(
                recipient_user_id=uid,
                title=title,
                message=message,
                notification_type=notification_type,
                data=data,
            )
            for uid in distinct_ids
        ]
        created = Notification.objects.bulk_create(notifications)

        for notif in created:
            cls._dispatch_channel_event(
                group_name=f"user_{notif.recipient_user_id}",
                message_type="notification.message",
                payload={
                    "envelope_key": "notification",
                    "data": {
                        "id": notif.id,
                        "recipient_user_id": notif.recipient_user_id,
                        "title": notif.title,
                        "message": notif.message,
                        "notification_type": notif.notification_type,
                        "is_read": notif.is_read,
                        "data": notif.data,
                        "created_at": notif.created_at.isoformat() if notif.created_at else timezone.now().isoformat(),
                    },
                },
            )
        return created

    @classmethod
    def broadcast_announcement(cls, announcement: Announcement) -> int:
        """
        Broadcasts a published announcement to its target audience.
        Creates persistent in-app notifications and dispatches real-time events.
        """
        if not announcement.is_published:
            return 0

        target_user_ids = set()

        if announcement.scope == AnnouncementScope.COURSE:
            # Enrolled students in the CourseOffering
            if announcement.audience_type in (AudienceType.ALL, AudienceType.STUDENTS):
                student_user_ids = Enrollment.objects.filter(
                    course_offering=announcement.course_offering,
                    status=EnrollmentStatus.ENROLLED,
                ).values_list("student__auth_user_id", flat=True)
                target_user_ids.update(student_user_ids)

            # Course instructor / faculty
            if announcement.audience_type in (AudienceType.ALL, AudienceType.FACULTY):
                if announcement.course_offering and announcement.course_offering.faculty_id:
                    target_user_ids.add(str(announcement.course_offering.faculty_id))

        elif announcement.scope == AnnouncementScope.DEPARTMENT:
            dept_id = announcement.department_id
            if announcement.audience_type in (AudienceType.ALL, AudienceType.STUDENTS):
                student_user_ids = StudentProfile.objects.filter(
                    department_id=dept_id,
                    is_active=True,
                ).values_list("auth_user_id", flat=True)
                target_user_ids.update(student_user_ids)

        elif announcement.scope == AnnouncementScope.INSTITUTION:
            if announcement.audience_type in (AudienceType.ALL, AudienceType.STUDENTS):
                student_user_ids = StudentProfile.objects.filter(
                    is_active=True,
                ).values_list("auth_user_id", flat=True)
                target_user_ids.update(student_user_ids)

        if target_user_ids:
            cls.send_bulk_notifications(
                recipient_user_ids=list(target_user_ids),
                title=f"Announcement: {announcement.title}",
                message=announcement.content[:200] + ("..." if len(announcement.content) > 200 else ""),
                notification_type=NotificationType.ANNOUNCEMENT,
                data={
                    "announcement_id": announcement.id,
                    "scope": announcement.scope,
                    "course_offering_id": announcement.course_offering_id,
                    "department_id": announcement.department_id,
                },
            )

        return len(target_user_ids)

    @classmethod
    def mark_as_read(cls, notification_id: int, user_id: str) -> Notification:
        notification = Notification.objects.get(id=notification_id, recipient_user_id=str(user_id))
        notification.mark_as_read()
        return notification

    @classmethod
    def mark_all_as_read(cls, user_id: str) -> int:
        now = timezone.now()
        count = Notification.objects.filter(recipient_user_id=str(user_id), is_read=False).update(
            is_read=True, read_at=now
        )
        return count

    @classmethod
    def get_unread_count(cls, user_id: str) -> int:
        return Notification.objects.filter(recipient_user_id=str(user_id), is_read=False).count()


# --- LMS Academic Lifecycle Event Triggers ---

def trigger_assignment_published(assignment) -> int:
    """
    Triggers notifications to all enrolled students when an assignment is published.
    """
    student_user_ids = list(
        Enrollment.objects.filter(
            course_offering=assignment.course_offering,
            status=EnrollmentStatus.ENROLLED,
        ).values_list("student__auth_user_id", flat=True)
    )

    if not student_user_ids:
        return 0

    due_str = assignment.due_date.strftime("%Y-%m-%d %H:%M") if assignment.due_date else "No due date"
    notifications = NotificationService.send_bulk_notifications(
        recipient_user_ids=student_user_ids,
        title=f"New Assignment: {assignment.title}",
        message=f"A new assignment '{assignment.title}' has been published. Due: {due_str}.",
        notification_type=NotificationType.ASSIGNMENT,
        data={
            "assignment_id": assignment.id,
            "course_offering_id": assignment.course_offering_id,
            "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        },
    )
    return len(notifications)


def trigger_grade_published(grade_record) -> Notification | None:
    """
    Triggers notification to a student when a grade record is published.
    """
    student_user_id = grade_record.student.auth_user_id
    item_name = grade_record.grade_item.name
    score_str = f"{grade_record.marks_obtained}/{grade_record.grade_item.max_marks}" if grade_record.marks_obtained is not None else (grade_record.letter_grade or "Graded")

    return NotificationService.send_notification(
        recipient_user_id=student_user_id,
        title=f"Grade Published: {item_name}",
        message=f"Your grade for '{item_name}' has been published: {score_str}.",
        notification_type=NotificationType.GRADE,
        data={
            "grade_record_id": grade_record.id,
            "grade_item_id": grade_record.grade_item_id,
            "marks_obtained": str(grade_record.marks_obtained) if grade_record.marks_obtained is not None else None,
            "letter_grade": grade_record.letter_grade,
        },
    )


def trigger_attendance_alert(attendance_record) -> Notification | None:
    """
    Triggers notification when a student is marked Absent or Late.
    """
    status_val = str(attendance_record.status)
    if status_val not in ("ABSENT", "LATE"):
        return None

    student_user_id = attendance_record.student.auth_user_id
    session_date = attendance_record.session.session_date.strftime("%Y-%m-%d")
    title = f"Attendance Alert: Marked {status_val.capitalize()}"
    message = f"You were marked {status_val.lower()} for attendance session on {session_date} in Course Offering #{attendance_record.session.course_offering_id}."

    return NotificationService.send_notification(
        recipient_user_id=student_user_id,
        title=title,
        message=message,
        notification_type=NotificationType.ATTENDANCE,
        data={
            "attendance_record_id": attendance_record.id,
            "session_id": attendance_record.session_id,
            "status": status_val,
            "session_date": session_date,
        },
    )


def trigger_timetable_update(timetable_entry, action: str = "updated") -> int:
    """
    Triggers notifications to enrolled students when a timetable slot is created/updated/cancelled.
    """
    student_user_ids = list(
        Enrollment.objects.filter(
            course_offering=timetable_entry.course_offering,
            status=EnrollmentStatus.ENROLLED,
        ).values_list("student__auth_user_id", flat=True)
    )

    if not student_user_ids:
        return 0

    time_str = f"{timetable_entry.start_time.strftime('%H:%M')} - {timetable_entry.end_time.strftime('%H:%M')}"
    notifications = NotificationService.send_bulk_notifications(
        recipient_user_ids=student_user_ids,
        title=f"Timetable {action.capitalize()}: {timetable_entry.course_offering}",
        message=f"Class schedule for {timetable_entry.day_of_week} ({time_str}, Room {timetable_entry.room or 'TBD'}) was {action}.",
        notification_type=NotificationType.TIMETABLE,
        data={
            "timetable_entry_id": timetable_entry.id,
            "course_offering_id": timetable_entry.course_offering_id,
            "action": action,
        },
    )
    return len(notifications)

