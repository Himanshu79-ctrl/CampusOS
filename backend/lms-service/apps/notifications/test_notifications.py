"""
Comprehensive automated test suite for Notifications & Announcements (apps.notifications).
Implements SRS Section 3.G:
  - Course-specific, Department-level, and Institution-wide announcements.
  - Audience targeting (ALL, STUDENTS, FACULTY).
  - Author tracking, permissions, and publish/unpublish toggling.
  - Persistent in-app notifications in PostgreSQL with read/unread tracking and counts.
  - Real-time WebSocket delivery via Django Channels and JWT authentication.
  - User-specific channel isolation and cross-user eavesdropping prevention.
  - Academic lifecycle event triggers (assignments, grades, attendance, timetable).
"""

from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import (
    AcademicTerm,
    CourseOffering,
    Enrollment,
    EnrollmentStatus,
    OfferingStatus,
    TermStatus,
)
from apps.assignments.models import Assignment
from apps.assignments.services import AssignmentService
from apps.attendance.models import AttendanceRecord, AttendanceSession, AttendanceStatus
from apps.attendance.services import AttendanceService
from apps.grades.models import GradeItem, GradeItemType, GradeRecord
from apps.grades.services import GradeService
from apps.notifications.models import (
    Announcement,
    AnnouncementScope,
    AudienceType,
    Notification,
    NotificationType,
)
from apps.notifications.services import (
    NotificationService,
    trigger_assignment_published,
    trigger_attendance_alert,
    trigger_grade_published,
    trigger_timetable_update,
)
from apps.students.models import StudentProfile
from apps.timetable.models import TimetableEntry
from apps.timetable.services import TimetableService
from config.asgi import application
from config.authentication import ExternalJWTAuthentication


class AnnouncementModelTests(TestCase):
    """
    Unit tests for Announcement model validations and scopes.
    """

    def setUp(self):
        self.term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
        )
        self.offering = CourseOffering.objects.create(
            course_id="CRS_101",
            faculty_id="fac_101",
            department_id="DEPT_CS",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )

    def test_institution_wide_announcement_valid(self):
        announcement = Announcement.objects.create(
            title="Campus Holiday Notice",
            content="Campus will be closed next Monday.",
            author_user_id="adm_1",
            author_role="admin",
            scope=AnnouncementScope.INSTITUTION,
            audience_type=AudienceType.ALL,
        )
        self.assertEqual(announcement.scope, AnnouncementScope.INSTITUTION)
        self.assertIsNone(announcement.course_offering)
        self.assertIsNone(announcement.department_id)

    def test_course_level_announcement_valid(self):
        announcement = Announcement.objects.create(
            title="Quiz 1 Rescheduled",
            content="Quiz 1 is moved to Friday.",
            author_user_id="fac_101",
            author_role="faculty",
            course_offering=self.offering,
            audience_type=AudienceType.STUDENTS,
        )
        self.assertEqual(announcement.scope, AnnouncementScope.COURSE)
        self.assertEqual(announcement.course_offering, self.offering)

    def test_department_level_announcement_valid(self):
        announcement = Announcement.objects.create(
            title="CS Department Seminar",
            content="Guest lecture on AI at 3 PM.",
            author_user_id="adm_1",
            author_role="admin",
            department_id="DEPT_CS",
            audience_type=AudienceType.ALL,
        )
        self.assertEqual(announcement.scope, AnnouncementScope.DEPARTMENT)
        self.assertEqual(announcement.department_id, "DEPT_CS")

    def test_course_announcement_requires_course_offering(self):
        with self.assertRaises(ValidationError):
            Announcement(
                title="Invalid",
                content="Body",
                author_user_id="fac_101",
                scope=AnnouncementScope.COURSE,
                course_offering=None,
            ).full_clean()

    def test_department_announcement_requires_department_id(self):
        with self.assertRaises(ValidationError):
            Announcement(
                title="Invalid",
                content="Body",
                author_user_id="adm_1",
                scope=AnnouncementScope.DEPARTMENT,
                department_id=None,
            ).full_clean()


class AnnouncementAPITests(TestCase):
    """
    Integration tests for Announcement REST APIs and RBAC permissions.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin_token = ExternalJWTAuthentication.generate_token(user_id="adm_1", role="admin")
        self.faculty_token = ExternalJWTAuthentication.generate_token(user_id="fac_101", role="faculty")
        self.other_faculty_token = ExternalJWTAuthentication.generate_token(user_id="fac_999", role="faculty")
        self.student_token = ExternalJWTAuthentication.generate_token(user_id="stu_1", role="student")
        self.other_student_token = ExternalJWTAuthentication.generate_token(user_id="stu_2", role="student")

        self.term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )
        self.offering = CourseOffering.objects.create(
            course_id="CRS_101",
            faculty_id="fac_101",
            department_id="DEPT_CS",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )
        self.student1 = StudentProfile.objects.create(
            auth_user_id="stu_1",
            registration_number="REG001",
            department_id="DEPT_CS",
            admission_year=2026,
            current_semester=1,
        )
        self.student2 = StudentProfile.objects.create(
            auth_user_id="stu_2",
            registration_number="REG002",
            department_id="DEPT_EE",
            admission_year=2026,
            current_semester=1,
        )
        Enrollment.objects.create(
            student=self.student1,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )

    def test_admin_creates_institution_announcement(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        payload = {
            "title": "Semester Registration Open",
            "content": "Please complete course registration by Friday.",
            "scope": "INSTITUTION",
            "audience_type": "ALL",
            "is_published": True,
        }
        res = self.client.post("/api/notifications/announcements/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Semester Registration Open")
        self.assertEqual(res.data["author_user_id"], "adm_1")

    def test_faculty_creates_course_announcement(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        payload = {
            "title": "Assignment 1 Reminder",
            "content": "Submission closes at 11:59 PM.",
            "course_offering": self.offering.id,
            "audience_type": "STUDENTS",
            "is_published": True,
        }
        res = self.client.post("/api/notifications/announcements/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["scope"], "COURSE")
        self.assertEqual(res.data["author_user_id"], "fac_101")

    def test_unassigned_faculty_cannot_create_course_announcement(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        payload = {
            "title": "Unauthorized Notice",
            "content": "Body",
            "course_offering": self.offering.id,
        }
        res = self.client.post("/api/notifications/announcements/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_create_announcement(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        payload = {
            "title": "Student Post",
            "content": "Body",
        }
        res = self.client.post("/api/notifications/announcements/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_audience_and_enrollment_scoping(self):
        # Create institution announcement
        Announcement.objects.create(
            title="Institution Notice",
            content="Content",
            author_user_id="adm_1",
            scope=AnnouncementScope.INSTITUTION,
            audience_type=AudienceType.ALL,
            is_published=True,
        )
        # Create CS dept announcement
        Announcement.objects.create(
            title="CS Dept Notice",
            content="Content",
            author_user_id="adm_1",
            scope=AnnouncementScope.DEPARTMENT,
            department_id="DEPT_CS",
            audience_type=AudienceType.STUDENTS,
            is_published=True,
        )
        # Create EE dept announcement
        Announcement.objects.create(
            title="EE Dept Notice",
            content="Content",
            author_user_id="adm_1",
            scope=AnnouncementScope.DEPARTMENT,
            department_id="DEPT_EE",
            audience_type=AudienceType.STUDENTS,
            is_published=True,
        )
        # Create Course announcement
        Announcement.objects.create(
            title="Course Notice",
            content="Content",
            author_user_id="fac_101",
            scope=AnnouncementScope.COURSE,
            course_offering=self.offering,
            audience_type=AudienceType.STUDENTS,
            is_published=True,
        )
        # Create Unpublished announcement
        Announcement.objects.create(
            title="Draft Notice",
            content="Draft",
            author_user_id="fac_101",
            scope=AnnouncementScope.COURSE,
            course_offering=self.offering,
            is_published=False,
        )

        # Student 1 (CS dept, enrolled in offering)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        res = self.client.get("/api/notifications/announcements/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [a["title"] for a in res.data["results"]]
        self.assertIn("Institution Notice", titles)
        self.assertIn("CS Dept Notice", titles)
        self.assertIn("Course Notice", titles)
        self.assertNotIn("EE Dept Notice", titles)  # Different department
        self.assertNotIn("Draft Notice", titles)    # Unpublished

        # Student 2 (EE dept, not enrolled in offering)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_student_token}")
        res2 = self.client.get("/api/notifications/announcements/")
        titles2 = [a["title"] for a in res2.data["results"]]
        self.assertIn("Institution Notice", titles2)
        self.assertIn("EE Dept Notice", titles2)
        self.assertNotIn("CS Dept Notice", titles2)
        self.assertNotIn("Course Notice", titles2)

    def test_publish_toggle_and_broadcast(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        announcement = Announcement.objects.create(
            title="Draft Quiz Notice",
            content="Draft body",
            author_user_id="fac_101",
            scope=AnnouncementScope.COURSE,
            course_offering=self.offering,
            audience_type=AudienceType.STUDENTS,
            is_published=False,
        )

        # Toggle to published
        res = self.client.post(
            f"/api/notifications/announcements/{announcement.id}/publish/",
            {"is_published": True},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["is_published"])

        # Verify enrolled student 1 received a persistent notification
        notif = Notification.objects.filter(recipient_user_id="stu_1").first()
        self.assertIsNotNone(notif)
        self.assertIn("Draft Quiz Notice", notif.title)


class NotificationAPITests(TestCase):
    """
    Integration tests for persistent in-app Notifications, unread counts, and IDOR protection.
    """

    def setUp(self):
        self.client = APIClient()
        self.student1_token = ExternalJWTAuthentication.generate_token(user_id="stu_1", role="student")
        self.student2_token = ExternalJWTAuthentication.generate_token(user_id="stu_2", role="student")

        self.notif1 = Notification.objects.create(
            recipient_user_id="stu_1",
            title="Assignment Due Tomorrow",
            message="Please submit Assignment 1.",
            notification_type=NotificationType.ASSIGNMENT,
            is_read=False,
        )
        self.notif2 = Notification.objects.create(
            recipient_user_id="stu_1",
            title="Grade Released",
            message="Your quiz has been graded.",
            notification_type=NotificationType.GRADE,
            is_read=False,
        )
        self.notif_other = Notification.objects.create(
            recipient_user_id="stu_2",
            title="Private Alert",
            message="Only for Student 2.",
            notification_type=NotificationType.GENERAL,
            is_read=False,
        )

    def test_user_lists_own_notifications_only(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/notifications/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)
        ids = [item["id"] for item in res.data["results"]]
        self.assertIn(self.notif1.id, ids)
        self.assertIn(self.notif2.id, ids)
        self.assertNotIn(self.notif_other.id, ids)

    def test_filter_notifications_by_type_and_read_status(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/notifications/?type=ASSIGNMENT")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["title"], "Assignment Due Tomorrow")

    def test_unread_count_endpoint(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["unread_count"], 2)

    def test_mark_single_notification_read(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.post(f"/api/notifications/{self.notif1.id}/read/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["is_read"])

        # Check unread count decreased to 1
        res_count = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(res_count.data["unread_count"], 1)

    def test_idor_protection_cannot_mark_other_users_notification(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        # Student 1 attempts to mark Student 2's notification as read
        res = self.client.post(f"/api/notifications/{self.notif_other.id}/read/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_all_read_endpoint(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.post("/api/notifications/mark-all-read/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["marked_count"], 2)

        # Student 2's notification remains unread
        self.notif_other.refresh_from_db()
        self.assertFalse(self.notif_other.is_read)


class WebSocketNotificationTests(TransactionTestCase):
    """
    Tests for Django Channels WebSocket authentication, real-time message delivery,
    and cross-user group isolation.
    """

    def setUp(self):
        self.student1_token = ExternalJWTAuthentication.generate_token(user_id="ws_user_1", role="student")
        self.student2_token = ExternalJWTAuthentication.generate_token(user_id="ws_user_2", role="student")

    def test_websocket_connection_success(self):
        async def _test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/notifications/?token={self.student1_token}",
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            response = await communicator.receive_json_from()
            self.assertEqual(response["type"], "connection_established")
            self.assertEqual(response["user_id"], "ws_user_1")

            await communicator.disconnect()

        async_to_sync(_test)()

    def test_websocket_missing_token_rejected(self):
        async def _test():
            communicator = WebsocketCommunicator(application, "/ws/notifications/")
            connected, close_code = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(close_code, 4001)

        async_to_sync(_test)()

    def test_websocket_expired_token_rejected(self):
        expired_token = ExternalJWTAuthentication.generate_token(
            user_id="ws_user_1",
            role="student",
            expires_in_minutes=-10,
        )

        async def _test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/notifications/?token={expired_token}",
            )
            connected, close_code = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(close_code, 4001)

        async_to_sync(_test)()

    def test_websocket_ping_pong(self):
        async def _test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/notifications/?token={self.student1_token}",
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()  # consume welcome message

            # Send ping
            await communicator.send_json_to({"type": "ping"})
            pong = await communicator.receive_json_from()
            self.assertEqual(pong["type"], "pong")

            await communicator.disconnect()

        async_to_sync(_test)()

    def test_websocket_real_time_delivery_and_isolation(self):
        """
        Verifies that when NotificationService sends a notification to ws_user_1,
        ws_user_1 receives it, and ws_user_2 does NOT receive it.
        """
        async def _test():
            client1 = WebsocketCommunicator(
                application,
                f"/ws/notifications/?token={self.student1_token}",
            )
            client2 = WebsocketCommunicator(
                application,
                f"/ws/notifications/?token={self.student2_token}",
            )

            connected1, _ = await client1.connect()
            connected2, _ = await client2.connect()
            self.assertTrue(connected1)
            self.assertTrue(connected2)

            await client1.receive_json_from()  # consume welcome
            await client2.receive_json_from()  # consume welcome

            # Trigger notification to ws_user_1 via NotificationService
            await database_sync_to_async(NotificationService.send_notification)(
                recipient_user_id="ws_user_1",
                title="Personal Grade Alert",
                message="Your Assignment 1 score is 95/100.",
                notification_type=NotificationType.GRADE,
            )

            # Client 1 should receive the message
            event1 = await client1.receive_json_from(timeout=3)
            self.assertEqual(event1["type"], "notification")
            self.assertEqual(event1["data"]["title"], "Personal Grade Alert")
            self.assertEqual(event1["data"]["recipient_user_id"], "ws_user_1")

            # Client 2 should NOT receive any message (times out with no message)
            no_msg = await client2.receive_nothing(timeout=0.5)
            self.assertTrue(no_msg)

            await client1.disconnect()
            await client2.disconnect()

        async_to_sync(_test)()


class AcademicEventTriggersTests(TestCase):
    """
    Tests for automatic academic event notification triggers:
      - Assignment publication
      - Grade publication
      - Attendance absent/late alert
      - Timetable schedule updates
    """

    def setUp(self):
        self.term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )
        self.offering = CourseOffering.objects.create(
            course_id="CRS_202",
            faculty_id="fac_202",
            department_id="DEPT_CS",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )
        self.student = StudentProfile.objects.create(
            auth_user_id="stu_evt_1",
            registration_number="REG_EVT_1",
            department_id="DEPT_CS",
            admission_year=2026,
            current_semester=1,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )

    def test_assignment_published_trigger(self):
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Midterm Homework",
            description="Homework questions",
            due_date=timezone.now() + timedelta(days=7),
            max_marks=Decimal("50.00"),
            is_published=False,
        )
        # Publish assignment
        AssignmentService.publish_assignment(assignment, is_published=True)

        notif = Notification.objects.filter(recipient_user_id="stu_evt_1").first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.notification_type, NotificationType.ASSIGNMENT)
        self.assertIn("Midterm Homework", notif.title)

    def test_grade_published_trigger(self):
        grade_item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Lab Exam 1",
            item_type=GradeItemType.PROJECT,
            max_marks=Decimal("100.00"),
            weightage_percentage=Decimal("20.00"),
            is_published=False,
        )
        record = GradeRecord.objects.create(
            grade_item=grade_item,
            student=self.student,
            marks_obtained=Decimal("92.50"),
            letter_grade="A",
            is_published=False,
        )

        class FacultyUser:
            user_id = "fac_202"
            role = "faculty"
            is_faculty = True
            is_admin = False

        GradeService.publish_grade_item(FacultyUser(), grade_item, is_published=True)

        notif = Notification.objects.filter(recipient_user_id="stu_evt_1", notification_type=NotificationType.GRADE).first()
        self.assertIsNotNone(notif)
        self.assertIn("Lab Exam 1", notif.title)

    def test_attendance_alert_trigger(self):
        class FacultyUser:
            user_id = "fac_202"
            role = "faculty"
            is_faculty = True
            is_admin = False

        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 10),
            title="Lecture 5",
            created_by_faculty_id="fac_202",
        )

        AttendanceService.mark_or_update_session_records(
            FacultyUser(),
            session,
            records_data=[{"student_id": self.student.id, "status": AttendanceStatus.ABSENT}],
        )

        notif = Notification.objects.filter(recipient_user_id="stu_evt_1", notification_type=NotificationType.ATTENDANCE).first()
        self.assertIsNotNone(notif)
        self.assertIn("Marked Absent", notif.title)

    def test_timetable_update_trigger(self):
        class FacultyUser:
            user_id = "fac_202"
            role = "faculty"
            is_faculty = True
            is_admin = False

        from datetime import time
        entry = TimetableService.create_entry(
            FacultyUser(),
            course_offering=self.offering,
            day_of_week="MONDAY",
            start_time=time(9, 0),
            end_time=time(10, 30),
            room="Room 303",
        )

        notif = Notification.objects.filter(recipient_user_id="stu_evt_1", notification_type=NotificationType.TIMETABLE).first()
        self.assertIsNotNone(notif)
        self.assertIn("Timetable", notif.title)
