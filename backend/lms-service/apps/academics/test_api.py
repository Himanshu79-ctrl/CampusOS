"""
Automated tests for Academic Terms, Course Offerings, and Enrollment APIs in apps.academics.
Covers permission enforcement, filtering, lifecycle transitions, roster access, and enrollment actions.
"""

from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    AcademicTerm,
    CourseOffering,
    Enrollment,
    EnrollmentStatus,
    OfferingStatus,
    TermStatus,
)
from apps.students.models import StudentProfile
from config.authentication import ExternalJWTAuthentication


class AcademicAndEnrollmentAPITests(APITestCase):
    """
    Test suite for Academic terms, offerings, and enrollment endpoints.
    """

    def setUp(self):
        # Roles and tokens
        self.student_user_id = "std_auth_100"
        self.student_token = ExternalJWTAuthentication.generate_token(
            user_id=self.student_user_id, role="student"
        )
        self.faculty_user_id = "fac_auth_200"
        self.faculty_token = ExternalJWTAuthentication.generate_token(
            user_id=self.faculty_user_id, role="faculty"
        )
        self.other_faculty_token = ExternalJWTAuthentication.generate_token(
            user_id="fac_auth_999", role="faculty"
        )
        self.admin_token = ExternalJWTAuthentication.generate_token(
            user_id="admin_auth_001", role="admin"
        )

        # Student profile
        self.student_profile = StudentProfile.objects.create(
            auth_user_id=self.student_user_id,
            registration_number="2026-CSE-100",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            admission_year=2026,
            current_semester=1,
            is_active=True,
        )

        # Academic term
        self.term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )

        # Course offering (taught by self.faculty_user_id)
        self.offering = CourseOffering.objects.create(
            course_id="65a8e01b2c3d4e5f6a7b8c01",
            faculty_id=self.faculty_user_id,
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            academic_term=self.term,
            section="A",
            capacity=2,
            status=OfferingStatus.PUBLISHED,
        )

        # Draft course offering
        self.draft_offering = CourseOffering.objects.create(
            course_id="65a8e01b2c3d4e5f6a7b8c02",
            faculty_id=self.faculty_user_id,
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            academic_term=self.term,
            section="B",
            capacity=30,
            status=OfferingStatus.DRAFT,
        )

    # --------------------------------------------------------------------------
    # Academic Term Endpoint Tests
    # --------------------------------------------------------------------------

    def test_list_academic_terms(self):
        """Authenticated users can list terms."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        url = reverse("academics:term-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 1)

    def test_get_current_active_term(self):
        """Current active term returns 200 OK with active term details."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        url = reverse("academics:term-current")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Fall 2026")
        self.assertEqual(response.data["status"], "ACTIVE")

    def test_only_admin_can_create_term(self):
        """Student cannot create term (403), Admin can (201)."""
        url = reverse("academics:term-list-create")
        data = {
            "name": "Spring 2027",
            "academic_year": "2026-2027",
            "term_number": 2,
            "start_date": "2027-01-10",
            "end_date": "2027-05-20",
            "status": "UPCOMING",
            "is_enrollment_open": False,
        }

        # Student attempt -> 403
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        res_std = self.client.post(url, data, format="json")
        self.assertEqual(res_std.status_code, status.HTTP_403_FORBIDDEN)

        # Admin attempt -> 201
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res_adm = self.client.post(url, data, format="json")
        self.assertEqual(res_adm.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_adm.data["name"], "Spring 2027")

    def test_admin_term_lifecycle_transitions(self):
        """Admin can activate, complete, and configure enrollment window via dedicated endpoints."""
        term2 = AcademicTerm.objects.create(
            name="Spring 2027",
            academic_year="2026-2027",
            term_number=2,
            start_date=date(2027, 1, 10),
            end_date=date(2027, 5, 20),
            status=TermStatus.UPCOMING,
            is_enrollment_open=False,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")

        # Activate term2 -> term1 becomes COMPLETED
        act_url = reverse("academics:term-activate", kwargs={"pk": term2.pk})
        res_act = self.client.post(act_url)
        self.assertEqual(res_act.status_code, status.HTTP_200_OK)
        self.assertEqual(res_act.data["status"], "ACTIVE")

        self.term.refresh_from_db()
        self.assertEqual(self.term.status, "COMPLETED")

        # Open enrollment window
        win_url = reverse("academics:term-enrollment-window", kwargs={"pk": term2.pk})
        res_win = self.client.post(win_url, {"is_open": True}, format="json")
        self.assertEqual(res_win.status_code, status.HTTP_200_OK)
        self.assertTrue(res_win.data["is_enrollment_open"])

    # --------------------------------------------------------------------------
    # Course Offering Endpoint Tests
    # --------------------------------------------------------------------------

    def test_students_only_see_published_offerings(self):
        """Students see only PUBLISHED offerings, drafts are filtered out."""
        url = reverse("academics:offering-list-create")

        # Student query
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        res_std = self.client.get(url)
        self.assertEqual(res_std.status_code, status.HTTP_200_OK)
        statuses = [item["status"] for item in res_std.data["results"]]
        self.assertIn("PUBLISHED", statuses)
        self.assertNotIn("DRAFT", statuses)

        # Admin query
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res_adm = self.client.get(url)
        self.assertEqual(res_adm.status_code, status.HTTP_200_OK)
        admin_statuses = [item["status"] for item in res_adm.data["results"]]
        self.assertIn("DRAFT", admin_statuses)

    def test_course_offering_details_include_seat_counts(self):
        """Offering detail includes capacity, enrolled_count, and available_seats."""
        url = reverse("academics:offering-detail", kwargs={"pk": self.offering.pk})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["capacity"], 2)
        self.assertEqual(response.data["enrolled_count"], 0)
        self.assertEqual(response.data["available_seats"], 2)

    def test_course_offering_roster_access_control(self):
        """
        Only assigned faculty or academic admin can view class roster.
        Different faculty and students are rejected with 403 Forbidden.
        """
        roster_url = reverse("academics:offering-roster", kwargs={"pk": self.offering.pk})

        # 1. Assigned faculty member -> 200 OK
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res_fac = self.client.get(roster_url)
        self.assertEqual(res_fac.status_code, status.HTTP_200_OK)
        self.assertEqual(res_fac.data["offering_id"], self.offering.id)

        # 2. Unassigned faculty member -> 403 Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        res_other_fac = self.client.get(roster_url)
        self.assertEqual(res_other_fac.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Student -> 403 Forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        res_std = self.client.get(roster_url)
        self.assertEqual(res_std.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Academic admin -> 200 OK
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        res_adm = self.client.get(roster_url)
        self.assertEqual(res_adm.status_code, status.HTTP_200_OK)

    # --------------------------------------------------------------------------
    # Enrollment Action Tests
    # --------------------------------------------------------------------------

    def test_student_enroll_and_drop_flow(self):
        """Student enrolls in course offering, then drops the enrollment."""
        enroll_url = reverse("academics:offering-enroll", kwargs={"pk": self.offering.pk})
        drop_url = reverse("academics:offering-drop", kwargs={"pk": self.offering.pk})

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")

        # 1. Enroll
        res_enroll = self.client.post(enroll_url)
        self.assertEqual(res_enroll.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_enroll.data["status"], "ENROLLED")
        self.assertEqual(res_enroll.data["course_offering_id"], self.offering.id)

        # 2. Verify duplicate enrollment rejected
        res_dup = self.client.post(enroll_url)
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Drop enrollment
        res_drop = self.client.post(drop_url)
        self.assertEqual(res_drop.status_code, status.HTTP_200_OK)
        self.assertEqual(res_drop.data["status"], "DROPPED")

        # 4. Re-enroll after drop
        res_reenroll = self.client.post(enroll_url)
        self.assertEqual(res_reenroll.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_reenroll.data["status"], "ENROLLED")

    def test_cannot_enroll_in_draft_offering(self):
        """Enrolling in a draft offering returns 400 Bad Request."""
        enroll_url = reverse("academics:offering-enroll", kwargs={"pk": self.draft_offering.pk})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        response = self.client.post(enroll_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_enroll_when_capacity_reached(self):
        """Enrolling when capacity is full returns 400 Bad Request."""
        # Enroll 2 students into offering (capacity = 2)
        Enrollment.objects.create(
            student=self.student_profile,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )
        student2 = StudentProfile.objects.create(
            auth_user_id="std_auth_101",
            registration_number="2026-CSE-101",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            admission_year=2026,
            current_semester=1,
            is_active=True,
        )
        Enrollment.objects.create(
            student=student2,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )

        # Third student attempts to enroll via API
        student3_token = ExternalJWTAuthentication.generate_token(
            user_id="std_auth_102", role="student"
        )
        StudentProfile.objects.create(
            auth_user_id="std_auth_102",
            registration_number="2026-CSE-102",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            admission_year=2026,
            current_semester=1,
            is_active=True,
        )

        enroll_url = reverse("academics:offering-enroll", kwargs={"pk": self.offering.pk})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {student3_token}")
        response = self.client.post(enroll_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("maximum capacity", str(response.data))

    def test_enrollment_list_role_scoping(self):
        """Students see only their enrollments, faculty see their courses, admin sees all."""
        Enrollment.objects.create(
            student=self.student_profile,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )

        url = reverse("academics:enrollment-list")

        # Student query
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        res_std = self.client.get(url)
        self.assertEqual(res_std.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_std.data["results"]), 1)

        # Faculty query
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.faculty_token}")
        res_fac = self.client.get(url)
        self.assertEqual(res_fac.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_fac.data["results"]), 1)

        # Unassigned faculty query
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        res_other = self.client.get(url)
        self.assertEqual(res_other.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_other.data["results"]), 0)

