"""
Service layer for Timetable & Calendar Management in CampusOS LMS.
Encapsulates business rules for scheduling conflict validation, timetable slot management,
faculty & student schedule queries, and calendar events (SRS Section 3.E).
"""

from datetime import date, time
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from apps.academics.models import CourseOffering, Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile
from .models import CalendarEvent, CalendarEventType, DayOfWeek, TimetableEntry


class TimetableService:
    """
    Business logic coordinator for Timetable entries, conflict detection,
    and institutional calendar events.
    """

    @classmethod
    def check_faculty_or_admin_permission(cls, user, course_offering: CourseOffering) -> None:
        """
        Validates that requesting user is an academic admin or assigned course faculty.
        """
        if getattr(user, "is_admin", False):
            return

        if getattr(user, "is_faculty", False):
            if str(course_offering.faculty_id) == str(user.user_id):
                return
            raise PermissionDenied("You are not the assigned instructor for this course offering.")

        raise PermissionDenied("Only faculty instructors or administrators can manage timetables.")

    @classmethod
    def validate_scheduling_conflicts(
        cls,
        course_offering: CourseOffering,
        faculty_id: str,
        day_of_week: str,
        start_time: time,
        end_time: time,
        room: str,
        exclude_entry_id: int = None,
    ) -> None:
        """
        Validates that the proposed slot does not cause room, faculty, or section conflicts.
        Overlapping condition: start_time < other.end_time AND end_time > other.start_time.
        """
        overlapping_qs = TimetableEntry.objects.filter(
            is_active=True,
            day_of_week=day_of_week,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )

        if exclude_entry_id:
            overlapping_qs = overlapping_qs.exclude(pk=exclude_entry_id)

        # 1. Room Conflict
        room_conflict = overlapping_qs.filter(room=room).select_related("course_offering").first()
        if room_conflict:
            raise ValidationError(
                {
                    "room": (
                        f"Room '{room}' is already occupied on {day_of_week} "
                        f"between {room_conflict.start_time.strftime('%H:%M')} and {room_conflict.end_time.strftime('%H:%M')} "
                        f"by Course Offering #{room_conflict.course_offering_id}."
                    )
                }
            )

        # 2. Faculty Conflict
        faculty_conflict = overlapping_qs.filter(faculty_id=faculty_id).select_related("course_offering").first()
        if faculty_conflict:
            raise ValidationError(
                {
                    "faculty_id": (
                        f"Faculty '{faculty_id}' is already scheduled for another class on {day_of_week} "
                        f"between {faculty_conflict.start_time.strftime('%H:%M')} and {faculty_conflict.end_time.strftime('%H:%M')}."
                    )
                }
            )

        # 3. Section / Course Offering Conflict
        offering_conflict = overlapping_qs.filter(course_offering=course_offering).first()
        if offering_conflict:
            raise ValidationError(
                {
                    "course_offering": (
                        f"Course Offering #{course_offering.id} already has a class scheduled on {day_of_week} "
                        f"between {offering_conflict.start_time.strftime('%H:%M')} and {offering_conflict.end_time.strftime('%H:%M')}."
                    )
                }
            )

    @classmethod
    def create_entry(
        cls,
        user,
        course_offering: CourseOffering,
        day_of_week: str,
        start_time: time,
        end_time: time,
        room: str,
        building: str = "",
        entry_type: str = "LECTURE",
        faculty_id: str = None,
    ) -> TimetableEntry:
        """
        Creates a new TimetableEntry with conflict validation.
        """
        cls.check_faculty_or_admin_permission(user, course_offering)

        eff_faculty_id = faculty_id or str(course_offering.faculty_id)

        if end_time <= start_time:
            raise ValidationError({"end_time": "Class end time must be strictly after the start time."})

        cls.validate_scheduling_conflicts(
            course_offering=course_offering,
            faculty_id=eff_faculty_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            room=room,
        )

        with transaction.atomic():
            entry = TimetableEntry(
                course_offering=course_offering,
                faculty_id=eff_faculty_id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                room=room.strip(),
                building=building.strip(),
                entry_type=entry_type,
                is_active=True,
            )
            entry.save()
            try:
                from apps.notifications.services import trigger_timetable_update
                trigger_timetable_update(entry, action="scheduled")
            except Exception:
                pass
            return entry

    @classmethod
    def update_entry(
        cls,
        user,
        entry: TimetableEntry,
        **attrs,
    ) -> TimetableEntry:
        """
        Updates an existing TimetableEntry with conflict validation.
        """
        cls.check_faculty_or_admin_permission(user, entry.course_offering)

        eff_day = attrs.get("day_of_week", entry.day_of_week)
        eff_start = attrs.get("start_time", entry.start_time)
        eff_end = attrs.get("end_time", entry.end_time)
        eff_room = attrs.get("room", entry.room)
        eff_faculty = attrs.get("faculty_id", entry.faculty_id)

        if eff_end <= eff_start:
            raise ValidationError({"end_time": "Class end time must be strictly after the start time."})

        cls.validate_scheduling_conflicts(
            course_offering=entry.course_offering,
            faculty_id=eff_faculty,
            day_of_week=eff_day,
            start_time=eff_start,
            end_time=eff_end,
            room=eff_room,
            exclude_entry_id=entry.id,
        )

        with transaction.atomic():
            for key, val in attrs.items():
                if hasattr(entry, key):
                    setattr(entry, key, val)
            entry.save()
            try:
                from apps.notifications.services import trigger_timetable_update
                trigger_timetable_update(entry, action="updated")
            except Exception:
                pass
            return entry

    @classmethod
    def delete_entry(cls, user, entry: TimetableEntry) -> None:
        """
        Deletes a timetable schedule slot.
        """
        cls.check_faculty_or_admin_permission(user, entry.course_offering)
        entry.delete()

    @classmethod
    def get_student_timetable(
        cls,
        student_profile: StudentProfile,
        term_id: int = None,
        day_of_week: str = None,
    ):
        """
        Returns weekly class schedule for all courses in which the student is actively enrolled.
        """
        enrolled_offering_ids = Enrollment.objects.filter(
            student=student_profile,
            status=EnrollmentStatus.ENROLLED,
        ).values_list("course_offering_id", flat=True)

        qs = TimetableEntry.objects.filter(
            is_active=True,
            course_offering_id__in=enrolled_offering_ids,
        ).select_related("course_offering", "course_offering__academic_term")

        if term_id:
            qs = qs.filter(course_offering__academic_term_id=term_id)
        if day_of_week:
            qs = qs.filter(day_of_week=day_of_week.upper())

        return qs.order_by("day_of_week", "start_time")

    @classmethod
    def get_faculty_timetable(
        cls,
        faculty_id: str,
        term_id: int = None,
        day_of_week: str = None,
    ):
        """
        Returns weekly teaching schedule for a faculty member.
        """
        qs = TimetableEntry.objects.filter(
            is_active=True,
            faculty_id=faculty_id,
        ).select_related("course_offering", "course_offering__academic_term")

        if term_id:
            qs = qs.filter(course_offering__academic_term_id=term_id)
        if day_of_week:
            qs = qs.filter(day_of_week=day_of_week.upper())

        return qs.order_by("day_of_week", "start_time")

    @classmethod
    def create_calendar_event(
        cls,
        user,
        title: str,
        start_date: date,
        end_date: date,
        event_type: str = CalendarEventType.EVENT,
        description: str = "",
        start_time: time = None,
        end_time: time = None,
        academic_term=None,
        course_offering: CourseOffering = None,
        is_published: bool = True,
    ) -> CalendarEvent:
        """
        Creates a calendar event.
        Course-specific events can be created by the assigned faculty or admin.
        Global or term-wide events require academic admin privileges.
        """
        if course_offering:
            cls.check_faculty_or_admin_permission(user, course_offering)
        else:
            if not getattr(user, "is_admin", False):
                raise PermissionDenied("Only academic administrators can create institution-wide calendar events.")

        if end_date < start_date:
            raise ValidationError({"end_date": "Event end date cannot precede start date."})

        if start_date == end_date and start_time and end_time:
            if end_time <= start_time:
                raise ValidationError({"end_time": "Event end time must be after the start time on the same date."})

        event = CalendarEvent(
            title=title.strip(),
            description=description.strip(),
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            academic_term=academic_term,
            course_offering=course_offering,
            created_by_user_id=str(user.user_id),
            is_published=is_published,
        )
        event.save()
        return event

    @classmethod
    def get_calendar_events(
        cls,
        user,
        term_id: int = None,
        offering_id: int = None,
        start_date: date = None,
        end_date: date = None,
    ):
        """
        Returns calendar events scoped to the requesting user's role and enrollments.
        """
        qs = CalendarEvent.objects.all().select_related("academic_term", "course_offering")

        if getattr(user, "is_student", False):
            profile = StudentProfile.objects.filter(auth_user_id=str(user.user_id)).first()
            if profile:
                enrolled_offering_ids = list(
                    Enrollment.objects.filter(
                        student=profile, status=EnrollmentStatus.ENROLLED
                    ).values_list("course_offering_id", flat=True)
                )
                qs = qs.filter(
                    is_published=True
                ).filter(
                    Q(course_offering__isnull=True) | Q(course_offering_id__in=enrolled_offering_ids)
                )
            else:
                qs = qs.none()

        elif getattr(user, "is_faculty", False):
            qs = qs.filter(
                Q(course_offering__isnull=True)
                | Q(course_offering__faculty_id=str(user.user_id))
                | Q(is_published=True)
            )

        if term_id:
            qs = qs.filter(academic_term_id=term_id)
        if offering_id:
            qs = qs.filter(course_offering_id=offering_id)
        if start_date:
            qs = qs.filter(end_date__gte=start_date)
        if end_date:
            qs = qs.filter(start_date__lte=end_date)

        return qs.order_by("start_date", "start_time")

