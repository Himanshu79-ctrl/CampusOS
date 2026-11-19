"""
Comprehensive automated test suite for Reports & Analytics (apps.reports).
Implements SRS Section 3.16 / 3.H:
  - Admin Institutional Overview KPI Reports.
  - Admin Student Demographic, Progress, and Performance Reports.
  - HOD Department Analytics & Departmental Data Scoping.
  - Faculty Course Offering Progress, Attendance, and Assessment Reports.
  - Role-scoped Attendance Analytics & Threshold Filtering.
  - CSV and JSON Export Functionality with Strict RBAC.
  - Empty dataset handling and external integration status reporting.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
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
from apps.assignments.models import Assignment, AssignmentSubmission, SubmissionStatus
from apps.attendance.models import AttendanceRecord, AttendanceSession, AttendanceStatus
from apps.grades.models import FinalCourseGrade, GradeItem, GradeItemType, GradeRecord
from apps.learning.models import CourseModule, LearningResource, Lesson
from apps.students.models import StudentProfile
from config.authentication import ExternalJWTAuthentication


class ReportsBaseTestCase(TestCase):
    """
    Base test case with rich academic setup: terms, departments, offerings,
    faculty, students, attendance, assignments, and grades.
    """

    def setUp(self):
        self.client = APIClient()

        # Auth Tokens
        self.admin_token = ExternalJWTAuthentication.generate_token(user_id="adm_1", role="admin")
        self.super_admin_token = ExternalJWTAuthentication.generate_token(user_id="sup_1", role="super_admin")
        self.faculty_token = ExternalJWTAuthentication.generate_token(
            user_id="fac_101", role="faculty", email="hod.cs@campusos.edu", department_id="DEPT_CS"
        )
        self.ordinary_faculty_token = ExternalJWTAuthentication.generate_token(
            user_id="fac_102", role="faculty", email="ordinary.cs@campusos.edu", department_id="DEPT_CS"
        )
        self.other_faculty_token = ExternalJWTAuthentication.generate_token(
            user_id="fac_999", role="faculty", email="fac.ee@campusos.edu", department_id="DEPT_EE"
        )
        self.no_email_faculty_token = ExternalJWTAuthentication.generate_token(
            user_id="fac_103", role="faculty", email="", department_id="DEPT_CS"
        )
        self.student1_token = ExternalJWTAuthentication.generate_token(user_id="stu_1", role="student", email="stu1@campusos.edu")
        self.student2_token = ExternalJWTAuthentication.generate_token(user_id="stu_2", role="student", email="stu2@campusos.edu")

        # Academic Terms
        self.term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )

        # Course Offerings
        self.offering_cs = CourseOffering.objects.create(
            course_id="CRS_CS101",
            faculty_id="fac_101",
            department_id="DEPT_CS",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )
        self.offering_ee = CourseOffering.objects.create(
            course_id="CRS_EE201",
            faculty_id="fac_999",
            department_id="DEPT_EE",
            academic_term=self.term,
            section="B",
            capacity=40,
            status=OfferingStatus.PUBLISHED,
        )

        # Students
        self.student1 = StudentProfile.objects.create(
            auth_user_id="stu_1",
            registration_number="REG2026_001",
            department_id="DEPT_CS",
            admission_year=2026,
            current_semester=1,
            is_active=True,
        )
        self.student2 = StudentProfile.objects.create(
            auth_user_id="stu_2",
            registration_number="REG2026_002",
            department_id="DEPT_CS",
            admission_year=2026,
            current_semester=1,
            is_active=True,
        )
        self.student3_ee = StudentProfile.objects.create(
            auth_user_id="stu_3",
            registration_number="REG2026_003",
            department_id="DEPT_EE",
            admission_year=2025,
            current_semester=3,
            is_active=False,
        )

        # Enrollments
        self.enr1 = Enrollment.objects.create(
            student=self.student1, course_offering=self.offering_cs, status=EnrollmentStatus.ENROLLED
        )
        self.enr2 = Enrollment.objects.create(
            student=self.student2, course_offering=self.offering_cs, status=EnrollmentStatus.ENROLLED
        )
        self.enr3 = Enrollment.objects.create(
            student=self.student3_ee, course_offering=self.offering_ee, status=EnrollmentStatus.ENROLLED
        )

        # Attendance Sessions and Records
        self.session1 = AttendanceSession.objects.create(
            course_offering=self.offering_cs,
            session_date=date(2026, 9, 1),
            title="Lecture 1",
            created_by_faculty_id="fac_101",
        )
        self.session2 = AttendanceSession.objects.create(
            course_offering=self.offering_cs,
            session_date=date(2026, 9, 3),
            title="Lecture 2",
            created_by_faculty_id="fac_101",
        )
        # Student 1: 2 present -> 100%
        AttendanceRecord.objects.create(
            session=self.session1, student=self.student1, status=AttendanceStatus.PRESENT
        )
        AttendanceRecord.objects.create(
            session=self.session2, student=self.student1, status=AttendanceStatus.PRESENT
        )
        # Student 2: 1 absent, 1 late -> 50% attended
        AttendanceRecord.objects.create(
            session=self.session1, student=self.student2, status=AttendanceStatus.ABSENT
        )
        AttendanceRecord.objects.create(
            session=self.session2, student=self.student2, status=AttendanceStatus.LATE
        )

        # Learning Module and Lessons
        self.module = CourseModule.objects.create(
            course_offering=self.offering_cs, title="Introduction to CS", order=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module, title="Lesson 1: Overview", content="Welcome", order=1
        )
        self.resource = LearningResource.objects.create(
            module=self.module, title="Syllabus", resource_type="LINK", external_url="https://example.com"
        )

        # Assignments & Submissions
        self.assignment = Assignment.objects.create(
            course_offering=self.offering_cs,
            title="Assignment 1",
            max_marks=Decimal("100.00"),
            due_date=timezone.now() + timedelta(days=7),
            is_published=True,
        )
        self.sub1 = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student1,
            submission_text="My submission",
            status=SubmissionStatus.GRADED,
            marks_obtained=Decimal("95.00"),
            graded_by_faculty_id="fac_101",
        )

        # Grades
        self.grade_item = GradeItem.objects.create(
            course_offering=self.offering_cs,
            name="Assignment 1 Score",
            item_type=GradeItemType.ASSIGNMENT,
            max_marks=Decimal("100.00"),
            weightage_percentage=Decimal("30.00"),
            is_published=True,
        )
        self.grade_rec1 = GradeRecord.objects.create(
            grade_item=self.grade_item,
            student=self.student1,
            marks_obtained=Decimal("95.00"),
            letter_grade="A",
            is_published=True,
            graded_by_faculty_id="fac_101",
        )
        self.final_grade1 = FinalCourseGrade.objects.create(
            course_offering=self.offering_cs,
            student=self.student1,
            total_marks_obtained=Decimal("95.00"),
            total_max_marks=Decimal("100.00"),
            percentage=Decimal("95.00"),
            final_letter_grade="A",
            is_published=True,
            graded_by_faculty_id="fac_101",
        )


class AdminOverviewReportTests(ReportsBaseTestCase):
    """
    Tests for GET /api/admin/reports/overview/
    """

    def test_admin_retrieves_overview_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res = self.client.get("/api/admin/reports/overview/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertIn("institution_metrics", data)
        self.assertIn("attendance_overview", data)
        self.assertIn("assignments_overview", data)
        self.assertIn("grades_overview", data)
        self.assertIn("external_integrations", data)

        # Verify calculated values
        metrics = data["institution_metrics"]
        self.assertEqual(metrics["total_students"], 3)
        self.assertEqual(metrics["active_students"], 2)
        self.assertEqual(metrics["inactive_students"], 1)
        self.assertEqual(metrics["total_course_offerings"], 2)
        self.assertEqual(metrics["active_faculty_count"], 2)
        self.assertEqual(metrics["active_enrollments"], 3)

        # Attendance
        att = data["attendance_overview"]
        self.assertEqual(att["total_sessions"], 2)
        self.assertEqual(att["total_records"], 4)
        self.assertEqual(att["present_count"], 2)
        self.assertEqual(att["late_count"], 1)
        self.assertEqual(att["absent_count"], 1)
        self.assertEqual(att["overall_attendance_rate"], 75.0)  # (2 present + 1 late) / 4 = 75.0%

    def test_admin_overview_department_filter(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res = self.client.get("/api/admin/reports/overview/?department_id=DEPT_CS")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        metrics = res.data["institution_metrics"]
        self.assertEqual(metrics["total_students"], 2)  # student1 and student2 are CS
        self.assertEqual(metrics["total_course_offerings"], 1)  # only CS offering

    def test_faculty_and_student_forbidden(self):
        # Faculty forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res_fac = self.client.get("/api/admin/reports/overview/")
        self.assertEqual(res_fac.status_code, status.HTTP_403_FORBIDDEN)

        # Student forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res_stu = self.client.get("/api/admin/reports/overview/")
        self.assertEqual(res_stu.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_rejected(self):
        res = self.client.get("/api/admin/reports/overview/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminStudentsReportTests(ReportsBaseTestCase):
    """
    Tests for GET /api/admin/reports/students/
    """

    def test_admin_retrieves_students_report(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res = self.client.get("/api/admin/reports/students/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["count"], 3)
        results = res.data["results"]
        self.assertEqual(len(results), 3)

        # Student 1 verification
        s1 = next(item for item in results if item["registration_number"] == "REG2026_001")
        self.assertEqual(s1["enrolled_courses_count"], 1)
        self.assertEqual(s1["attendance"]["attendance_percentage"], 100.0)
        self.assertEqual(s1["assignments"]["submitted_count"], 1)
        self.assertEqual(s1["assignments"]["graded_count"], 1)
        self.assertEqual(s1["grades"]["average_score_percentage"], 95.0)

    def test_admin_students_filters(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        # Filter by department
        res_dept = self.client.get("/api/admin/reports/students/?department_id=DEPT_EE")
        self.assertEqual(res_dept.status_code, status.HTTP_200_OK)
        self.assertEqual(res_dept.data["count"], 1)
        self.assertEqual(res_dept.data["results"][0]["registration_number"], "REG2026_003")

        # Filter by search
        res_search = self.client.get("/api/admin/reports/students/?search=REG2026_002")
        self.assertEqual(res_search.data["count"], 1)
        self.assertEqual(res_search.data["results"][0]["auth_user_id"], "stu_2")

    def test_non_admin_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res = self.client.get("/api/admin/reports/students/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class DepartmentReportTests(ReportsBaseTestCase):
    """
    Tests for GET /api/hod/reports/department/
    Covers authoritative HOD verification and fail-closed security.
    """

    def mock_get_department_hod(self, department_id: str):
        if department_id == "DEPT_CS":
            return {
                "_id": "65a8e01b2c3d4e5f6a7b8d02",
                "name": "Dr. CS Head",
                "employeeId": "EMP_CS_01",
                "email": "hod.cs@campusos.edu",
                "designation": "Professor & Head",
            }
        elif department_id == "DEPT_EE":
            return {
                "_id": "65a8e01b2c3d4e5f6a7b8d03",
                "name": "Dr. EE Head",
                "employeeId": "EMP_EE_01",
                "email": "hod.ee@campusos.edu",
                "designation": "Professor & Head",
            }
        return None

    @patch("apps.academics.admin_client.AdminServiceClient.get_department_hod")
    def test_1_designated_hod_retrieves_own_department_report(self, mock_hod):
        """1. Actual designated HOD -> 200 OK."""
        mock_hod.side_effect = self.mock_get_department_hod
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res = self.client.get("/api/hod/reports/department/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["department_id"], "DEPT_CS")
        self.assertEqual(res.data["students_summary"]["total_students"], 2)
        self.assertEqual(res.data["offerings_summary"]["total_offerings"], 1)
        self.assertEqual(len(res.data["courses_breakdown"]), 1)
        self.assertEqual(res.data["courses_breakdown"][0]["course_id"], "CRS_CS101")

    @patch("apps.academics.admin_client.AdminServiceClient.get_department_hod")
    def test_2_ordinary_faculty_in_same_department_forbidden(self, mock_hod):
        """2. Ordinary faculty in the same department -> 403 Forbidden."""
        mock_hod.side_effect = self.mock_get_department_hod
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.ordinary_faculty_token}")
        res = self.client.get("/api/hod/reports/department/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("only authorized Department Heads", str(res.data))

    @patch("apps.academics.admin_client.AdminServiceClient.get_department_hod")
    def test_3_faculty_belonging_to_another_department_forbidden(self, mock_hod):
        """3. Faculty belonging to another department -> 403 Forbidden."""
        mock_hod.side_effect = self.mock_get_department_hod
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        res = self.client.get("/api/hod/reports/department/?department_id=DEPT_CS")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.academics.admin_client.AdminServiceClient.get_department_hod")
    def test_4_department_hod_record_null_forbidden(self, mock_hod):
        """4. Department HOD record is null (unassigned) -> 403 Forbidden (fail-closed)."""
        mock_hod.return_value = None
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res = self.client.get("/api/hod/reports/department/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.academics.admin_client.AdminServiceClient.get_department_hod")
    def test_5_admin_service_unavailable_forbidden(self, mock_hod):
        """5. Admin Service timeout/unavailable -> 403 Forbidden (fail-closed)."""
        mock_hod.side_effect = ConnectionError("Admin service connection timeout")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res = self.client.get("/api/hod/reports/department/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.academics.admin_client.AdminServiceClient.get_department_hod")
    def test_6_missing_or_unverifiable_user_email_forbidden(self, mock_hod):
        """6. Missing or unverifiable user email -> 403 Forbidden (fail-closed)."""
        mock_hod.side_effect = self.mock_get_department_hod
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.no_email_faculty_token}")
        res = self.client.get("/api/hod/reports/department/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_7_student_forbidden(self):
        """7. Student -> 403 Forbidden."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/hod/reports/department/?department_id=DEPT_CS")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_8_admin_and_super_admin_allowed(self):
        """8. Admin and super_admin -> 200 OK."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res_admin = self.client.get("/api/hod/reports/department/?department_id=DEPT_EE")
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertEqual(res_admin.data["department_id"], "DEPT_EE")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.super_admin_token}")
        res_super = self.client.get("/api/hod/reports/department/?department_id=DEPT_CS")
        self.assertEqual(res_super.status_code, status.HTTP_200_OK)
        self.assertEqual(res_super.data["department_id"], "DEPT_CS")

    @patch("apps.academics.admin_client.AdminServiceClient.get_department_hod")
    def test_9_cross_department_query_parameter_manipulation_forbidden(self, mock_hod):
        """9. Cross-department query parameter manipulation -> 403 Forbidden."""
        mock_hod.side_effect = self.mock_get_department_hod
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res = self.client.get("/api/hod/reports/department/?department_id=DEPT_EE")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.academics.admin_client.AdminServiceClient.get_department_hod")
    def test_10_forged_or_unsupported_hod_claims_cannot_bypass(self, mock_hod):
        """10. Forged or unsupported HOD claims cannot bypass authoritative verification."""
        mock_hod.side_effect = self.mock_get_department_hod
        # Ordinary faculty attempts to bypass with forged is_hod and faculty_id claims
        forged_token = ExternalJWTAuthentication.generate_token(
            user_id="fac_102",
            role="faculty",
            email="ordinary.cs@campusos.edu",
            department_id="DEPT_CS",
        )
        import jwt
        from django.conf import settings
        secret_key = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
        payload = jwt.decode(forged_token, key=secret_key, algorithms=["HS256"])
        payload["is_hod"] = True
        payload["faculty_id"] = "65a8e01b2c3d4e5f6a7b8d02"  # Admin HOD ObjectId
        forged_jwt = jwt.encode(payload, key=secret_key, algorithm="HS256")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {forged_jwt}")
        res = self.client.get("/api/hod/reports/department/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class CourseReportTests(ReportsBaseTestCase):
    """
    Tests for GET /api/faculty/reports/course/<course_offering_id>/
    """

    def test_assigned_faculty_retrieves_course_report(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res = self.client.get(f"/api/faculty/reports/course/{self.offering_cs.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data["course_offering"]["course_id"], "CRS_CS101")
        self.assertEqual(data["enrollment_analytics"]["total_enrolled"], 2)
        self.assertEqual(data["attendance_analytics"]["total_sessions_conducted"], 2)
        self.assertEqual(data["attendance_analytics"]["at_risk_students_count"], 1)  # Student 2 is at 50% (< 75%)
        self.assertEqual(data["learning_content_summary"]["modules_count"], 1)
        self.assertEqual(data["assignments_analytics"]["total_assignments"], 1)
        self.assertEqual(data["gradebook_analytics"]["finalized_grades_count"], 1)

    def test_unassigned_faculty_forbidden(self):
        # other_faculty_token is fac_999 (not fac_101)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        res = self.client.get(f"/api/faculty/reports/course/{self.offering_cs.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_any_course_report(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res = self.client.get(f"/api/faculty/reports/course/{self.offering_cs.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["course_offering"]["course_id"], "CRS_CS101")

    def test_student_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get(f"/api/faculty/reports/course/{self.offering_cs.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_offering_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res = self.client.get("/api/faculty/reports/course/99999/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class AttendanceReportTests(ReportsBaseTestCase):
    """
    Tests for GET /api/reports/attendance/
    """

    def test_student_personal_attendance_report(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/reports/attendance/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["student_registration_number"], "REG2026_001")
        self.assertEqual(res.data["overall_attendance_percentage"], 100.0)
        self.assertEqual(len(res.data["subjects"]), 1)
        self.assertEqual(res.data["subjects"][0]["course_id"], "CRS_CS101")

    def test_faculty_attendance_report_with_threshold(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res = self.client.get(f"/api/reports/attendance/?course_offering_id={self.offering_cs.id}&threshold=75.0")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Roster should contain Student 2 who has 50% (< 75.0%)
        roster = res.data["roster"]
        self.assertEqual(len(roster), 1)
        self.assertEqual(roster[0]["registration_number"], "REG2026_002")
        self.assertTrue(roster[0]["below_threshold"])


class ReportExportTests(ReportsBaseTestCase):
    """
    Tests for GET /api/reports/export?type=...&format=csv|json
    """

    def test_admin_exports_students_csv(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res = self.client.get("/api/reports/export/?type=admin_students&format=csv")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", res["Content-Disposition"])

        content = res.content.decode("utf-8")
        self.assertIn("Registration Number", content)
        self.assertIn("REG2026_001", content)
        self.assertIn("REG2026_002", content)

    def test_admin_exports_overview_json(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res = self.client.get("/api/reports/export/?type=admin_overview&format=json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "application/json")
        self.assertIn("attachment; filename=", res["Content-Disposition"])

    def test_faculty_exports_course_csv(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res = self.client.get(f"/api/reports/export/?type=course&course_offering_id={self.offering_cs.id}&format=csv")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/csv")
        self.assertIn("CRS_CS101", res.content.decode("utf-8"))

    def test_student_unauthorized_to_export_admin_report(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/reports/export/?type=admin_students&format=csv")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_report_type_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res = self.client.get("/api/reports/export/?type=unknown_report")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.academics.admin_client.AdminServiceClient.get_department_hod")
    def test_hod_exports_department_csv(self, mock_hod):
        mock_hod.return_value = {
            "_id": "65a8e01b2c3d4e5f6a7b8d02",
            "name": "Dr. CS Head",
            "employeeId": "EMP_CS_01",
            "email": "hod.cs@campusos.edu",
            "designation": "Professor & Head",
        }
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res = self.client.get("/api/reports/export/?type=department&department_id=DEPT_CS&format=csv")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/csv")
        self.assertIn("DEPT_CS", res.content.decode("utf-8"))

    @patch("apps.academics.admin_client.AdminServiceClient.get_department_hod")
    def test_ordinary_faculty_cannot_export_department_csv(self, mock_hod):
        mock_hod.return_value = {
            "_id": "65a8e01b2c3d4e5f6a7b8d02",
            "name": "Dr. CS Head",
            "employeeId": "EMP_CS_01",
            "email": "hod.cs@campusos.edu",
            "designation": "Professor & Head",
        }
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.ordinary_faculty_token}")
        res = self.client.get("/api/reports/export/?type=department&department_id=DEPT_CS&format=csv")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
