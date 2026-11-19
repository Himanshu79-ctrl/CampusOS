"""
Comprehensive automated test suite for Attendance Management (apps.attendance).
Implements SRS Section 3.D:
  - AttendanceSession and AttendanceRecord model validations and constraints.
  - Faculty session creation, updating, and deletion permissions.
  - Enrolled student eligibility and non-enrolled rejection.
  - Bulk and individual attendance marking (Present, Absent, Late).
  - Attendance correction with mandatory audit reason.
  - Course-wise attendance reports with configurable thresholds.
  - Student subject-wise attendance percentages and chronological history.
  - Student data isolation and IDOR protection.
"""

from datetime import date, time, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
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
from apps.attendance.models import AttendanceRecord, AttendanceSession, AttendanceStatus
from apps.students.models import StudentProfile
from config.authentication import ExternalJWTAuthentication


class AttendanceModelTests(TestCase):
    """
    Unit tests for model-level constraints and validation on AttendanceSession and AttendanceRecord.
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
        self.student = StudentProfile.objects.create(
            auth_user_id="stu_101",
            registration_number="REG2026_101",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=3,
        )
        self.non_enrolled_student = StudentProfile.objects.create(
            auth_user_id="stu_999",
            registration_number="REG2026_999",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=3,
        )
        # Actively enroll student in offering
        Enrollment.objects.create(
            student=self.student,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )

    def test_session_end_time_must_be_after_start_time(self):
        """Validates that session end_time cannot be equal to or before start_time."""
        with self.assertRaises(ValidationError):
            AttendanceSession.objects.create(
                course_offering=self.offering,
                session_date=date(2026, 9, 1),
                start_time=time(10, 0),
                end_time=time(9, 30),  # Before start_time
            )

    def test_non_enrolled_student_cannot_have_attendance_record(self):
        """Validates that a non-enrolled student raises ValidationError when creating AttendanceRecord."""
        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 1),
            title="Lecture 1",
        )
        with self.assertRaises(ValidationError):
            AttendanceRecord.objects.create(
                session=session,
                student=self.non_enrolled_student,
                status=AttendanceStatus.PRESENT,
            )

    def test_unique_student_session_attendance_constraint(self):
        """Enforces that a student cannot have duplicate attendance records in the same session."""
        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 1),
            title="Lecture 1",
        )
        AttendanceRecord.objects.create(
            session=session,
            student=self.student,
            status=AttendanceStatus.PRESENT,
        )
        with self.assertRaises((ValidationError, IntegrityError)):
            AttendanceRecord.objects.create(
                session=session,
                student=self.student,
                status=AttendanceStatus.ABSENT,
            )


class AttendanceAPITests(TestCase):
    """
    Integration tests for Attendance Management REST API endpoints and RBAC (SRS Section 3.D).
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
        self.offering = CourseOffering.objects.create(
            course_id="607f1f77bcf86cd799439011",
            faculty_id="fac_101",
            department_id="607f1f77bcf86cd799439033",
            academic_term=self.term,
            section="A",
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
        self.non_enrolled_student = StudentProfile.objects.create(
            auth_user_id="stu_99",
            registration_number="REG2026099",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=3,
        )

        # Active Enrollments
        Enrollment.objects.create(
            student=self.student1,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )
        Enrollment.objects.create(
            student=self.student2,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )

    # -------------------------------------------------------------------------
    # 1. Attendance Session Creation & Management
    # -------------------------------------------------------------------------

    def test_assigned_faculty_creates_session_successfully(self):
        """Assigned faculty can create an attendance session."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "session_date": "2026-09-01",
            "title": "Lecture 1: Introduction to Data Structures",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "description": "Course overview and asymptotic complexity.",
        }
        res = self.client.post(f"/api/attendance/offerings/{self.offering.id}/sessions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Lecture 1: Introduction to Data Structures")
        self.assertEqual(res.data["created_by_faculty_id"], "fac_101")

    def test_assigned_faculty_creates_session_with_initial_records(self):
        """Assigned faculty can atomically create a session and mark initial attendance."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "session_date": "2026-09-02",
            "title": "Lecture 2: Arrays & Linked Lists",
            "records": [
                {"student_id": self.student1.id, "status": "PRESENT"},
                {"student_id": self.student2.id, "status": "LATE", "remarks": "Arrived 10 mins late"},
            ],
        }
        res = self.client.post(f"/api/attendance/offerings/{self.offering.id}/sessions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["records_count"], 2)

    def test_unassigned_faculty_cannot_create_session(self):
        """Faculty not assigned to the offering cannot create attendance sessions (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        payload = {"session_date": "2026-09-01", "title": "Unauthorized Session"}
        res = self.client.post(f"/api/attendance/offerings/{self.offering.id}/sessions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_create_session(self):
        """Student cannot create an attendance session (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"session_date": "2026-09-01", "title": "Student Session"}
        res = self.client.post(f"/api/attendance/offerings/{self.offering.id}/sessions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_session(self):
        """Academic admin can create an attendance session for any offering."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        payload = {"session_date": "2026-09-03", "title": "Admin Created Session"}
        res = self.client.post(f"/api/attendance/offerings/{self.offering.id}/sessions/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_update_and_delete_session(self):
        """Assigned faculty can update and delete an attendance session."""
        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 1),
            title="Initial Title",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")

        # Update title
        patch_res = self.client.patch(f"/api/attendance/sessions/{session.id}/", {"title": "Updated Title"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["title"], "Updated Title")

        # Delete session
        del_res = self.client.delete(f"/api/attendance/sessions/{session.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        self.assertFalse(AttendanceSession.objects.filter(id=session.id).exists())

    # -------------------------------------------------------------------------
    # 2. Attendance Marking & Student Enrollment Eligibility
    # -------------------------------------------------------------------------

    def test_assigned_faculty_bulk_marks_attendance(self):
        """Assigned faculty marks Present, Absent, and Late for enrolled students."""
        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 1),
            title="Lecture 1",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "records": [
                {"student_id": self.student1.id, "status": "PRESENT"},
                {"student_id": self.student2.id, "status": "ABSENT", "remarks": "Unexcused absence"},
            ]
        }
        res = self.client.post(f"/api/attendance/sessions/{session.id}/mark/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        statuses = {r["student"]: r["status"] for r in res.data}
        self.assertEqual(statuses[self.student1.id], AttendanceStatus.PRESENT)
        self.assertEqual(statuses[self.student2.id], AttendanceStatus.ABSENT)

    def test_non_enrolled_student_marking_rejected(self):
        """Attempting to mark attendance for a student not actively enrolled is rejected with 400."""
        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 1),
            title="Lecture 1",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "records": [
                {"student_id": self.non_enrolled_student.id, "status": "PRESENT"},
            ]
        }
        res = self.client.post(f"/api/attendance/sessions/{session.id}/mark/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not actively enrolled", str(res.data))

    def test_invalid_status_choice_rejected(self):
        """Invalid attendance status choice is rejected with 400."""
        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 1),
            title="Lecture 1",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "records": [
                {"student_id": self.student1.id, "status": "EXCUSED_LEAVE"},
            ]
        }
        res = self.client.post(f"/api/attendance/sessions/{session.id}/mark/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_mark_attendance(self):
        """Student cannot call the mark attendance endpoint (403)."""
        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 1),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"records": [{"student_id": self.student1.id, "status": "PRESENT"}]}
        res = self.client.post(f"/api/attendance/sessions/{session.id}/mark/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 3. Attendance Correction with Audit Reason (SRS Requirement)
    # -------------------------------------------------------------------------

    def test_correct_attendance_with_audit_reason(self):
        """Assigned faculty can correct an attendance record with an audit reason."""
        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 1),
        )
        record = AttendanceRecord.objects.create(
            session=session,
            student=self.student1,
            status=AttendanceStatus.ABSENT,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "status": "PRESENT",
            "audit_reason": "Student was marked absent by mistake; attended online stream.",
            "remarks": "Rectified after verifying lab log.",
        }
        res = self.client.patch(f"/api/attendance/records/{record.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], AttendanceStatus.PRESENT)
        self.assertEqual(res.data["audit_reason"], "Student was marked absent by mistake; attended online stream.")
        self.assertEqual(res.data["recorded_by_user_id"], "fac_101")

    def test_correct_attendance_requires_audit_reason(self):
        """Correction without audit reason is rejected with 400 Bad Request."""
        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 1),
        )
        record = AttendanceRecord.objects.create(
            session=session,
            student=self.student1,
            status=AttendanceStatus.ABSENT,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "status": "PRESENT",
            "audit_reason": "",  # Empty
        }
        res = self.client.patch(f"/api/attendance/records/{record.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_correct_attendance(self):
        """Student cannot correct attendance records (403)."""
        session = AttendanceSession.objects.create(
            course_offering=self.offering,
            session_date=date(2026, 9, 1),
        )
        record = AttendanceRecord.objects.create(
            session=session,
            student=self.student1,
            status=AttendanceStatus.ABSENT,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"status": "PRESENT", "audit_reason": "I was there!"}
        res = self.client.patch(f"/api/attendance/records/{record.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 4. Course-wise Attendance Reports & Configurable Thresholds
    # -------------------------------------------------------------------------

    def test_faculty_generates_course_attendance_report(self):
        """Assigned faculty generates course-wise attendance report with threshold flagging."""
        # Create 4 sessions
        s1 = AttendanceSession.objects.create(course_offering=self.offering, session_date=date(2026, 9, 1))
        s2 = AttendanceSession.objects.create(course_offering=self.offering, session_date=date(2026, 9, 2))
        s3 = AttendanceSession.objects.create(course_offering=self.offering, session_date=date(2026, 9, 3))
        s4 = AttendanceSession.objects.create(course_offering=self.offering, session_date=date(2026, 9, 4))

        # Student 1 attended 3 of 4 (75%)
        AttendanceRecord.objects.create(session=s1, student=self.student1, status=AttendanceStatus.PRESENT)
        AttendanceRecord.objects.create(session=s2, student=self.student1, status=AttendanceStatus.PRESENT)
        AttendanceRecord.objects.create(session=s3, student=self.student1, status=AttendanceStatus.LATE)
        AttendanceRecord.objects.create(session=s4, student=self.student1, status=AttendanceStatus.ABSENT)

        # Student 2 attended 1 of 4 (25%)
        AttendanceRecord.objects.create(session=s1, student=self.student2, status=AttendanceStatus.PRESENT)
        AttendanceRecord.objects.create(session=s2, student=self.student2, status=AttendanceStatus.ABSENT)
        AttendanceRecord.objects.create(session=s3, student=self.student2, status=AttendanceStatus.ABSENT)
        AttendanceRecord.objects.create(session=s4, student=self.student2, status=AttendanceStatus.ABSENT)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        # Test report with configurable threshold = 70.0%
        res = self.client.get(f"/api/attendance/offerings/{self.offering.id}/report/?threshold=70.0")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_sessions"], 4)
        self.assertEqual(len(res.data["students"]), 2)

        stu_map = {s["student_id"]: s for s in res.data["students"]}
        # Student 1: 75% -> above threshold 70%
        self.assertEqual(stu_map[self.student1.id]["attendance_percentage"], 75.0)
        self.assertFalse(stu_map[self.student1.id]["below_threshold"])

        # Student 2: 25% -> below threshold 70%
        self.assertEqual(stu_map[self.student2.id]["attendance_percentage"], 25.0)
        self.assertTrue(stu_map[self.student2.id]["below_threshold"])

    def test_student_cannot_view_course_attendance_report(self):
        """Student cannot view the aggregate class attendance report (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get(f"/api/attendance/offerings/{self.offering.id}/report/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unassigned_faculty_cannot_view_course_report(self):
        """Unassigned faculty cannot view the course attendance report (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        res = self.client.get(f"/api/attendance/offerings/{self.offering.id}/report/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 5. Student Personal Attendance & IDOR Protection
    # -------------------------------------------------------------------------

    def test_student_views_subject_wise_attendance_summary(self):
        """Student retrieves subject-wise attendance percentages for enrolled courses."""
        s1 = AttendanceSession.objects.create(course_offering=self.offering, session_date=date(2026, 9, 1))
        s2 = AttendanceSession.objects.create(course_offering=self.offering, session_date=date(2026, 9, 2))
        AttendanceRecord.objects.create(session=s1, student=self.student1, status=AttendanceStatus.PRESENT)
        AttendanceRecord.objects.create(session=s2, student=self.student1, status=AttendanceStatus.LATE)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/attendance/my-summary/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["course_offering_id"], self.offering.id)
        self.assertEqual(res.data[0]["total_sessions"], 2)
        self.assertEqual(res.data[0]["attended_count"], 2)
        self.assertEqual(res.data[0]["attendance_percentage"], 100.0)

    def test_student_views_attendance_history(self):
        """Student retrieves chronological attendance history."""
        s1 = AttendanceSession.objects.create(course_offering=self.offering, session_date=date(2026, 9, 1), title="Intro")
        rec = AttendanceRecord.objects.create(session=s1, student=self.student1, status=AttendanceStatus.PRESENT)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/attendance/my-history/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], rec.id)
        self.assertEqual(res.data[0]["status"], AttendanceStatus.PRESENT)

    def test_idor_protection_student_cannot_access_other_student_record(self):
        """Student 2 cannot view Student 1's attendance record (403 IDOR Protection)."""
        s1 = AttendanceSession.objects.create(course_offering=self.offering, session_date=date(2026, 9, 1))
        rec1 = AttendanceRecord.objects.create(session=s1, student=self.student1, status=AttendanceStatus.ABSENT)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student2_token}")
        res = self.client.get(f"/api/attendance/records/{rec1.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_view_own_attendance_record(self):
        """Student 1 can view their own individual attendance record (200)."""
        s1 = AttendanceSession.objects.create(course_offering=self.offering, session_date=date(2026, 9, 1))
        rec1 = AttendanceRecord.objects.create(session=s1, student=self.student1, status=AttendanceStatus.PRESENT)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get(f"/api/attendance/records/{rec1.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], rec1.id)
        self.assertEqual(res.data["status"], AttendanceStatus.PRESENT)

    def test_non_enrolled_student_cannot_list_course_sessions(self):
        """Student not enrolled in the offering cannot view its session list (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.non_enrolled_token}")
        res = self.client.get(f"/api/attendance/offerings/{self.offering.id}/sessions/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

