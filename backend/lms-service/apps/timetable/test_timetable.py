"""
Comprehensive automated test suite for Timetable & Calendar Management (apps.timetable).
Implements SRS Section 3.E:
  - Model constraints and time sequence validations.
  - Scheduling conflict detection (Room, Faculty, Course Offering overlaps).
  - Class schedule CRUD by assigned faculty and academic admin.
  - Show student timetable (enrolled courses only, IDOR protected).
  - Show faculty timetable (teaching slots, role protected).
  - Calendar events and announcements (institution-wide and course-specific).
"""

from datetime import date, time, timedelta
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import TestCase
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
from apps.students.models import StudentProfile
from apps.timetable.models import (
    CalendarEvent,
    CalendarEventType,
    ClassType,
    DayOfWeek,
    TimetableEntry,
)
from config.authentication import ExternalJWTAuthentication


class TimetableModelTests(TestCase):
    """
    Unit tests for model-level validation on TimetableEntry and CalendarEvent.
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
            course_id="607f1f77bcf86cd799439011",
            faculty_id="fac_101",
            department_id="607f1f77bcf86cd799439033",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )

    def test_timetable_end_time_must_be_after_start_time(self):
        """Validates that class end_time cannot be equal to or before start_time."""
        with self.assertRaises(ValidationError):
            TimetableEntry.objects.create(
                course_offering=self.offering,
                faculty_id="fac_101",
                day_of_week=DayOfWeek.MONDAY,
                start_time=time(11, 0),
                end_time=time(10, 0),  # Before start_time
                room="Room 101",
            )

    def test_calendar_event_end_date_cannot_precede_start_date(self):
        """Validates that calendar event end_date cannot precede start_date."""
        with self.assertRaises(ValidationError):
            CalendarEvent.objects.create(
                title="Invalid Date Event",
                start_date=date(2026, 9, 10),
                end_date=date(2026, 9, 5),  # Before start_date
            )

    def test_calendar_event_end_time_on_same_date(self):
        """Validates that on the same date, event end_time cannot precede start_time."""
        with self.assertRaises(ValidationError):
            CalendarEvent.objects.create(
                title="Invalid Time Event",
                start_date=date(2026, 9, 10),
                end_date=date(2026, 9, 10),
                start_time=time(14, 0),
                end_time=time(13, 0),
            )


class TimetableAPITests(TestCase):
    """
    Integration tests for Timetable & Calendar REST API endpoints and RBAC (SRS Section 3.E).
    """

    def setUp(self):
        self.client = APIClient()

        # Auth Tokens
        self.admin_token = ExternalJWTAuthentication.generate_token(user_id="adm_1", role="admin")
        self.instructor_token = ExternalJWTAuthentication.generate_token(user_id="fac_101", role="faculty")
        self.other_faculty_token = ExternalJWTAuthentication.generate_token(user_id="fac_999", role="faculty")
        self.student1_token = ExternalJWTAuthentication.generate_token(user_id="stu_1", role="student")
        self.student2_token = ExternalJWTAuthentication.generate_token(user_id="stu_2", role="student")
        self.non_enrolled_token = ExternalJWTAuthentication.generate_token(user_id="stu_99", role="student")

        # Academic Setup
        self.term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )
        self.offering1 = CourseOffering.objects.create(
            course_id="607f1f77bcf86cd799439011",
            faculty_id="fac_101",
            department_id="607f1f77bcf86cd799439033",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )
        self.offering2 = CourseOffering.objects.create(
            course_id="607f1f77bcf86cd799439022",
            faculty_id="fac_101",
            department_id="607f1f77bcf86cd799439033",
            academic_term=self.term,
            section="B",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )

        # Student Profiles
        self.student1 = StudentProfile.objects.create(
            auth_user_id="stu_1",
            registration_number="REG2026001",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=3,
        )
        self.student2 = StudentProfile.objects.create(
            auth_user_id="stu_2",
            registration_number="REG2026002",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=3,
        )

        # Student 1 enrolled in offering1
        Enrollment.objects.create(
            student=self.student1,
            course_offering=self.offering1,
            status=EnrollmentStatus.ENROLLED,
        )
        # Student 2 enrolled in offering2
        Enrollment.objects.create(
            student=self.student2,
            course_offering=self.offering2,
            status=EnrollmentStatus.ENROLLED,
        )

    # -------------------------------------------------------------------------
    # 1. Timetable Slot Creation & Management
    # -------------------------------------------------------------------------

    def test_assigned_faculty_creates_timetable_slot(self):
        """Assigned faculty can create a class slot for their course offering."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "day_of_week": "MONDAY",
            "start_time": "09:00:00",
            "end_time": "10:30:00",
            "room": "Room 101",
            "building": "Science Block",
            "entry_type": "LECTURE",
        }
        res = self.client.post(f"/api/timetable/offerings/{self.offering1.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["day_of_week"], "MONDAY")
        self.assertEqual(res.data["room"], "Room 101")
        self.assertEqual(res.data["faculty_id"], "fac_101")

    def test_unassigned_faculty_cannot_create_timetable_slot(self):
        """Faculty not assigned to the offering cannot add class slots (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        payload = {
            "day_of_week": "MONDAY",
            "start_time": "09:00:00",
            "end_time": "10:30:00",
            "room": "Room 101",
        }
        res = self.client.post(f"/api/timetable/offerings/{self.offering1.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_create_timetable_slot(self):
        """Student cannot add class slots (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {
            "day_of_week": "MONDAY",
            "start_time": "09:00:00",
            "end_time": "10:30:00",
            "room": "Room 101",
        }
        res = self.client.post(f"/api/timetable/offerings/{self.offering1.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_timetable_slot(self):
        """Academic admin can add class slots to any course offering."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        payload = {
            "day_of_week": "TUESDAY",
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "room": "Room 205",
        }
        res = self.client.post(f"/api/timetable/offerings/{self.offering1.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_update_and_delete_timetable_slot(self):
        """Assigned faculty can update and delete a timetable slot."""
        entry = TimetableEntry.objects.create(
            course_offering=self.offering1,
            faculty_id="fac_101",
            day_of_week=DayOfWeek.WEDNESDAY,
            start_time=time(10, 0),
            end_time=time(11, 0),
            room="Room 303",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")

        # Update room
        patch_res = self.client.patch(f"/api/timetable/entries/{entry.id}/", {"room": "Room 304"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["room"], "Room 304")

        # Delete slot
        del_res = self.client.delete(f"/api/timetable/entries/{entry.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        self.assertFalse(TimetableEntry.objects.filter(id=entry.id).exists())

    # -------------------------------------------------------------------------
    # 2. Scheduling Conflict Validation (SRS Requirement)
    # -------------------------------------------------------------------------

    def test_room_scheduling_conflict_detected(self):
        """Reject slot creation if room is already occupied during overlapping time."""
        # Book Room 101 on Monday 09:00 - 10:30 for offering1
        TimetableEntry.objects.create(
            course_offering=self.offering1,
            faculty_id="fac_101",
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 30),
            room="Room 101",
        )

        # Attempt to book same Room 101 on Monday 10:00 - 11:30 (overlaps 10:00 - 10:30) for offering2
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        payload = {
            "day_of_week": "MONDAY",
            "start_time": "10:00:00",
            "end_time": "11:30:00",
            "room": "Room 101",
            "faculty_id": "fac_999",  # Different faculty
        }
        res = self.client.post(f"/api/timetable/offerings/{self.offering2.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already occupied", str(res.data))

    def test_faculty_scheduling_conflict_detected(self):
        """Reject slot creation if faculty is already scheduled during overlapping time."""
        # Schedule fac_101 on Monday 09:00 - 10:30 in Room 101
        TimetableEntry.objects.create(
            course_offering=self.offering1,
            faculty_id="fac_101",
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 30),
            room="Room 101",
        )

        # Attempt to schedule same fac_101 on Monday 09:30 - 11:00 in Room 202 for offering2
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        payload = {
            "day_of_week": "MONDAY",
            "start_time": "09:30:00",
            "end_time": "11:00:00",
            "room": "Room 202",  # Different room
            "faculty_id": "fac_101",
        }
        res = self.client.post(f"/api/timetable/offerings/{self.offering2.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already scheduled", str(res.data))

    def test_course_offering_double_booking_conflict_detected(self):
        """Reject slot creation if the same course offering is already scheduled during overlapping time."""
        TimetableEntry.objects.create(
            course_offering=self.offering1,
            faculty_id="fac_101",
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 30),
            room="Room 101",
        )

        # Attempt to schedule offering1 again on Monday 10:15 - 11:45
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "day_of_week": "MONDAY",
            "start_time": "10:15:00",
            "end_time": "11:45:00",
            "room": "Lab 5",
            "faculty_id": "fac_co_instructor",
        }
        res = self.client.post(f"/api/timetable/offerings/{self.offering1.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already has a class scheduled", str(res.data))

    def test_non_overlapping_slots_allowed(self):
        """Non-overlapping consecutive slots in same room or with same faculty are allowed."""
        TimetableEntry.objects.create(
            course_offering=self.offering1,
            faculty_id="fac_101",
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            room="Room 101",
        )

        # Adjacent non-overlapping slot: 10:00 - 11:00 in same Room 101
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "day_of_week": "MONDAY",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "room": "Room 101",
        }
        res = self.client.post(f"/api/timetable/offerings/{self.offering2.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    # -------------------------------------------------------------------------
    # 3. Show Student Timetable (SRS Requirement) & IDOR Protection
    # -------------------------------------------------------------------------

    def test_student_retrieves_own_weekly_timetable(self):
        """Enrolled student can view weekly timetable for their enrolled courses."""
        TimetableEntry.objects.create(
            course_offering=self.offering1,
            faculty_id="fac_101",
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            room="Room 101",
        )
        TimetableEntry.objects.create(
            course_offering=self.offering2,  # Student 1 NOT enrolled in offering2
            faculty_id="fac_101",
            day_of_week=DayOfWeek.TUESDAY,
            start_time=time(11, 0),
            end_time=time(12, 0),
            room="Room 202",
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/timetable/my-timetable/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["course_offering"], self.offering1.id)
        self.assertEqual(res.data[0]["room"], "Room 101")

    def test_non_enrolled_student_cannot_view_offering_timetable(self):
        """Student cannot view class schedule for a course offering they are not enrolled in (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        # Student 1 tries to access offering2 timetable
        res = self.client.get(f"/api/timetable/offerings/{self.offering2.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_view_timetable_slot_of_non_enrolled_course(self):
        """Student cannot view detail of a timetable slot for a non-enrolled course (403 IDOR protection)."""
        entry2 = TimetableEntry.objects.create(
            course_offering=self.offering2,
            faculty_id="fac_101",
            day_of_week=DayOfWeek.TUESDAY,
            start_time=time(11, 0),
            end_time=time(12, 0),
            room="Room 202",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get(f"/api/timetable/entries/{entry2.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 4. Show Faculty Timetable (SRS Requirement)
    # -------------------------------------------------------------------------

    def test_faculty_retrieves_own_teaching_timetable(self):
        """Faculty retrieves their personal teaching timetable across assigned offerings."""
        TimetableEntry.objects.create(
            course_offering=self.offering1,
            faculty_id="fac_101",
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            room="Room 101",
        )
        TimetableEntry.objects.create(
            course_offering=self.offering2,
            faculty_id="fac_101",
            day_of_week=DayOfWeek.WEDNESDAY,
            start_time=time(14, 0),
            end_time=time(15, 30),
            room="Lab 2",
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        res = self.client.get("/api/timetable/faculty-timetable/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_student_cannot_access_faculty_timetable_endpoint(self):
        """Student cannot access faculty timetable endpoint (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/timetable/faculty-timetable/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_query_any_faculty_timetable(self):
        """Academic admin can query timetable for any faculty ID."""
        TimetableEntry.objects.create(
            course_offering=self.offering1,
            faculty_id="fac_101",
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
            room="Room 101",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res = self.client.get("/api/timetable/faculty-timetable/?faculty_id=fac_101")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    # -------------------------------------------------------------------------
    # 5. Calendar Events & Announcements (SRS Requirement)
    # -------------------------------------------------------------------------

    def test_admin_creates_institutional_calendar_event(self):
        """Academic admin can create an institution-wide calendar event."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        payload = {
            "title": "Semester Mid-Term Exams",
            "description": "Mid-term examination window for all departments.",
            "event_type": "EXAM",
            "start_date": "2026-10-15",
            "end_date": "2026-10-22",
            "academic_term_id": self.term.id,
        }
        res = self.client.post("/api/timetable/calendar/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Semester Mid-Term Exams")
        self.assertEqual(res.data["event_type"], "EXAM")

    def test_faculty_creates_course_specific_calendar_event(self):
        """Assigned faculty can create an event specific to their course offering."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "title": "Guest Lecture on Distributed Systems",
            "description": "Industry speaker session.",
            "event_type": "EVENT",
            "start_date": "2026-09-25",
            "end_date": "2026-09-25",
            "start_time": "15:00:00",
            "end_time": "17:00:00",
            "course_offering_id": self.offering1.id,
        }
        res = self.client.post("/api/timetable/calendar/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Guest Lecture on Distributed Systems")

    def test_faculty_cannot_create_institutional_calendar_event(self):
        """Faculty cannot create institution-wide (course_offering=None) calendar events (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "title": "Unauthorized Institutional Holiday",
            "event_type": "HOLIDAY",
            "start_date": "2026-11-01",
            "end_date": "2026-11-01",
        }
        res = self.client.post("/api/timetable/calendar/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_sees_institutional_and_enrolled_course_events(self):
        """Student sees published institutional events and events for enrolled courses only."""
        # Institutional event (all students see)
        CalendarEvent.objects.create(
            title="University Annual Sports Day",
            event_type=CalendarEventType.EVENT,
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 21),
            is_published=True,
        )
        # Event for offering 1 (Student 1 enrolled, Student 2 NOT)
        CalendarEvent.objects.create(
            title="Offering 1 Project Showcase",
            course_offering=self.offering1,
            event_type=CalendarEventType.EVENT,
            start_date=date(2026, 11, 25),
            end_date=date(2026, 11, 25),
            is_published=True,
        )
        # Event for offering 2 (Student 1 NOT enrolled)
        CalendarEvent.objects.create(
            title="Offering 2 Lab Hackathon",
            course_offering=self.offering2,
            event_type=CalendarEventType.EVENT,
            start_date=date(2026, 11, 26),
            end_date=date(2026, 11, 26),
            is_published=True,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/timetable/calendar/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [e["title"] for e in res.data]
        self.assertIn("University Annual Sports Day", titles)
        self.assertIn("Offering 1 Project Showcase", titles)
        self.assertNotIn("Offering 2 Lab Hackathon", titles)

    # -------------------------------------------------------------------------
    # 5. Faculty Cross-Service MongoDB ID Authorization Regression Tests
    # -------------------------------------------------------------------------

    @patch("apps.academics.faculty_matcher._get_admin_faculty_records")
    def test_assigned_faculty_with_mongodb_object_id_creates_timetable_slot(self, mock_get_faculty):
        """
        Regression test: When a CourseOffering stores a MongoDB ObjectId faculty_id
        ('6b001d4b79943f38bdcb47f2'), the authenticated faculty user with integer Auth
        service user_id='2' (Dr. Anurag Sewak) is recognized via faculty_matcher and can
        successfully create a timetable slot.
        """
        mock_get_faculty.return_value = [
            {
                "_id": "6b001d4b79943f38bdcb47f2",
                "name": "Dr. Anurag Sewak",
                "employeeId": "FAC-CSE-201",
                "email": "anurag@campusos.edu",
                "username": "dr_anurag",
                "authUserId": "2",
            }
        ]

        # Course offering with Dr. Anurag Sewak's MongoDB ObjectId
        anurag_offering = CourseOffering.objects.create(
            course_id="6b002d29e5fc4d2ec633113d",
            faculty_id="6b001d4b79943f38bdcb47f2",
            department_id="6afff8960979ad733ef114d0",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )

        anurag_token = ExternalJWTAuthentication.generate_token(user_id="2", role="faculty")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {anurag_token}")

        payload = {
            "day_of_week": "MONDAY",
            "start_time": "10:00:00",
            "end_time": "11:30:00",
            "room": "Room 402",
            "building": "Academic Block 1",
            "entry_type": "LECTURE",
        }
        res = self.client.post(f"/api/timetable/offerings/{anurag_offering.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["day_of_week"], "MONDAY")
        self.assertEqual(res.data["room"], "Room 402")
        self.assertEqual(res.data["faculty_id"], "6b001d4b79943f38bdcb47f2")

        # Verify faculty can retrieve this slot on their faculty timetable
        res_tt = self.client.get("/api/timetable/faculty-timetable/")
        self.assertEqual(res_tt.status_code, status.HTTP_200_OK)
        slot_ids = [s["id"] for s in res_tt.data]
        self.assertIn(res.data["id"], slot_ids)

    @patch("apps.academics.faculty_matcher._get_admin_faculty_records")
    def test_unassigned_faculty_cannot_create_timetable_slot_for_another_instructor(self, mock_get_faculty):
        """
        Regression test: An unassigned faculty member (Dr. Kalpana Singh, authUserId='17')
        cannot create timetable slots for Dr. Anurag Sewak's course offering (returns 403 Forbidden).
        """
        mock_get_faculty.return_value = [
            {
                "_id": "6b001d4b79943f38bdcb47f2",
                "name": "Dr. Anurag Sewak",
                "employeeId": "FAC-CSE-201",
                "email": "anurag@campusos.edu",
                "username": "dr_anurag",
                "authUserId": "2",
            },
            {
                "_id": "6afc347ed9e74d0557163928",
                "name": "Dr. Kalpana Singh",
                "employeeId": "FAC-CSE-001",
                "email": "kalpana@campusos.edu",
                "username": "dr_kalpana",
                "authUserId": "17",
            },
        ]

        anurag_offering = CourseOffering.objects.create(
            course_id="6b002d29e5fc4d2ec633113d",
            faculty_id="6b001d4b79943f38bdcb47f2",
            department_id="6afff8960979ad733ef114d0",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )

        kalpana_token = ExternalJWTAuthentication.generate_token(user_id="17", role="faculty")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {kalpana_token}")

        payload = {
            "day_of_week": "MONDAY",
            "start_time": "10:00:00",
            "end_time": "11:30:00",
            "room": "Room 402",
        }
        res = self.client.post(f"/api/timetable/offerings/{anurag_offering.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Only the assigned instructor or an administrator", res.data.get("detail", ""))

    @patch("apps.academics.faculty_matcher._get_admin_faculty_records")
    def test_faculty_cannot_spoof_faculty_id_in_create_timetable_slot(self, mock_get_faculty):
        """
        Security test: A faculty member cannot override the assigned instructor
        by supplying a spoofed faculty_id in the request payload.
        """
        mock_get_faculty.return_value = [
            {
                "_id": "6b001d4b79943f38bdcb47f2",
                "name": "Dr. Anurag Sewak",
                "employeeId": "FAC-CSE-201",
                "email": "anurag@campusos.edu",
                "username": "dr_anurag",
                "authUserId": "2",
            }
        ]

        anurag_offering = CourseOffering.objects.create(
            course_id="6b002d29e5fc4d2ec633113d",
            faculty_id="6b001d4b79943f38bdcb47f2",
            department_id="6afff8960979ad733ef114d0",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )

        anurag_token = ExternalJWTAuthentication.generate_token(user_id="2", role="faculty")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {anurag_token}")

        payload = {
            "day_of_week": "TUESDAY",
            "start_time": "10:00:00",
            "end_time": "11:30:00",
            "room": "Room 402",
            "faculty_id": "malicious_spoofed_fac_id",
        }
        res = self.client.post(f"/api/timetable/offerings/{anurag_offering.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["faculty_id"], "6b001d4b79943f38bdcb47f2")
        self.assertNotEqual(res.data["faculty_id"], "malicious_spoofed_fac_id")

    def test_admin_can_explicitly_set_faculty_id_on_timetable_slot(self):
        """
        Legitimate admin test: An administrator can explicitly set or override
        the faculty_id when creating a timetable slot.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")

        payload = {
            "day_of_week": "WEDNESDAY",
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "room": "Lab 201",
            "faculty_id": "fac_custom_assigned",
        }
        res = self.client.post(f"/api/timetable/offerings/{self.offering1.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["faculty_id"], "fac_custom_assigned")

    @patch("apps.academics.faculty_matcher._get_admin_faculty_records")
    def test_permission_checks_course_offering_assigned_faculty_not_overridden_entry_faculty(self, mock_get_faculty):
        """
        Security test: When TimetableEntry.faculty_id has an overridden value, authorization
        still strictly validates against CourseOffering.faculty_id.
        - An attacker matching the entry's faculty_id is denied access (403).
        - The legitimate assigned instructor is granted access (200) and entry is sanitized.
        """
        mock_get_faculty.return_value = [
            {
                "_id": "6b001d4b79943f38bdcb47f2",
                "name": "Dr. Anurag Sewak",
                "employeeId": "FAC-CSE-201",
                "email": "anurag@campusos.edu",
                "username": "dr_anurag",
                "authUserId": "2",
            }
        ]

        anurag_offering = CourseOffering.objects.create(
            course_id="6b002d29e5fc4d2ec633113d",
            faculty_id="6b001d4b79943f38bdcb47f2",
            department_id="6afff8960979ad733ef114d0",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )

        entry = TimetableEntry.objects.create(
            course_offering=anurag_offering,
            faculty_id="attacker_fake_id",
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 30),
            room="Room 402",
        )

        # 1. Attacker matching entry.faculty_id attempts to edit
        attacker_token = ExternalJWTAuthentication.generate_token(user_id="attacker_fake_id", role="faculty")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {attacker_token}")
        res_attacker = self.client.patch(
            f"/api/timetable/entries/{entry.id}/",
            {"room": "Room 666"},
            format="json",
        )
        self.assertEqual(res_attacker.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Legitimate assigned instructor (Dr. Anurag Sewak) edits
        anurag_token = ExternalJWTAuthentication.generate_token(user_id="2", role="faculty")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {anurag_token}")
        res_anurag = self.client.patch(
            f"/api/timetable/entries/{entry.id}/",
            {"room": "Room 405"},
            format="json",
        )
        self.assertEqual(res_anurag.status_code, status.HTTP_200_OK)
        self.assertEqual(res_anurag.data["room"], "Room 405")
        # Entry faculty_id must also be sanitized to the offering's instructor
        self.assertEqual(res_anurag.data["faculty_id"], "6b001d4b79943f38bdcb47f2")

    @patch("apps.academics.faculty_matcher._get_admin_faculty_records")
    def test_faculty_calendar_visibility_scopes_to_assigned_courses_and_published_institutional(self, mock_get_faculty):
        """
        Security test: Faculty can only see published institutional events and events
        for course offerings assigned to them.
        Draft institutional events and other courses' events are hidden and return 403 on direct access.
        """
        mock_get_faculty.return_value = [
            {
                "_id": "6b001d4b79943f38bdcb47f2",
                "name": "Dr. Anurag Sewak",
                "employeeId": "FAC-CSE-201",
                "email": "anurag@campusos.edu",
                "username": "dr_anurag",
                "authUserId": "2",
            },
            {
                "_id": "6afc347ed9e74d0557163928",
                "name": "Dr. Kalpana Singh",
                "employeeId": "FAC-CSE-001",
                "email": "kalpana@campusos.edu",
                "username": "dr_kalpana",
                "authUserId": "17",
            },
        ]

        anurag_offering = CourseOffering.objects.create(
            course_id="6b002d29e5fc4d2ec633113d",
            faculty_id="6b001d4b79943f38bdcb47f2",
            department_id="6afff8960979ad733ef114d0",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )
        kalpana_offering = CourseOffering.objects.create(
            course_id="6b002d29e5fc4d2ec633113e",
            faculty_id="6afc347ed9e74d0557163928",
            department_id="6afff8960979ad733ef114d0",
            academic_term=self.term,
            section="B",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )

        # 1. Published institutional event
        pub_inst = CalendarEvent.objects.create(
            title="Campus Job Fair",
            event_type=CalendarEventType.EVENT,
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 21),
            is_published=True,
        )
        # 2. Draft institutional event
        draft_inst = CalendarEvent.objects.create(
            title="Internal Staff Meeting",
            event_type=CalendarEventType.EVENT,
            start_date=date(2026, 11, 22),
            end_date=date(2026, 11, 22),
            is_published=False,
        )
        # 3. Anurag's course event
        anurag_event = CalendarEvent.objects.create(
            title="Control System Midterm Review",
            course_offering=anurag_offering,
            event_type=CalendarEventType.EXAM,
            start_date=date(2026, 11, 23),
            end_date=date(2026, 11, 23),
            is_published=True,
        )
        # 4. Kalpana's course event
        kalpana_event = CalendarEvent.objects.create(
            title="Data Structures Coding Contest",
            course_offering=kalpana_offering,
            event_type=CalendarEventType.EXAM,
            start_date=date(2026, 11, 24),
            end_date=date(2026, 11, 24),
            is_published=True,
        )

        anurag_token = ExternalJWTAuthentication.generate_token(user_id="2", role="faculty")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {anurag_token}")

        # Faculty list query
        res = self.client.get("/api/timetable/calendar/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [e["title"] for e in res.data]
        self.assertIn("Campus Job Fair", titles)
        self.assertIn("Control System Midterm Review", titles)
        self.assertNotIn("Internal Staff Meeting", titles)
        self.assertNotIn("Data Structures Coding Contest", titles)

        # Direct access to another faculty's course event returns 403
        res_kalpana = self.client.get(f"/api/timetable/calendar/{kalpana_event.id}/")
        self.assertEqual(res_kalpana.status_code, status.HTTP_403_FORBIDDEN)

        # Direct access to draft institutional event returns 403
        res_draft = self.client.get(f"/api/timetable/calendar/{draft_inst.id}/")
        self.assertEqual(res_draft.status_code, status.HTTP_403_FORBIDDEN)

        # Admin sees all 4 events
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res_admin = self.client.get("/api/timetable/calendar/")
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        admin_titles = [e["title"] for e in res_admin.data]
        self.assertIn("Campus Job Fair", admin_titles)
        self.assertIn("Internal Staff Meeting", admin_titles)
        self.assertIn("Control System Midterm Review", admin_titles)
        self.assertIn("Data Structures Coding Contest", admin_titles)

