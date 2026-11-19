"""
Automated tests for Student APIs in apps.students.
Covers profile provisioning, retrieval, updates, IDOR protection, and permissions.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import StudentProfile
from config.authentication import ExternalJWTAuthentication


class StudentAPITests(APITestCase):
    """
    Test suite for Student Profile REST APIs.
    """

    def setUp(self):
        self.student_user_id = "auth_std_001"
        self.student_token = ExternalJWTAuthentication.generate_token(
            user_id=self.student_user_id,
            role="student",
            email="student1@campus.edu",
        )
        self.other_student_user_id = "auth_std_002"
        self.other_student_token = ExternalJWTAuthentication.generate_token(
            user_id=self.other_student_user_id,
            role="student",
            email="student2@campus.edu",
        )
        self.admin_token = ExternalJWTAuthentication.generate_token(
            user_id="auth_admin_001",
            role="admin",
            email="admin@campus.edu",
        )

        # Existing student profile for other student
        self.other_profile = StudentProfile.objects.create(
            auth_user_id=self.other_student_user_id,
            registration_number="2026-CSE-002",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            admission_year=2026,
            current_semester=2,
            is_active=True,
        )

        self.create_url = reverse("students:profile-create")
        self.me_url = reverse("students:profile-me")

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests must be rejected with 401 Unauthorized."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_self_provision_profile(self):
        """Student successfully provisions their own academic profile."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        data = {
            "registration_number": "2026-CSE-001",
            "department_id": "65a8e01b2c3d4e5f6a7b8d01",
            "admission_year": 2026,
            "current_semester": 1,
        }
        response = self.client.post(self.create_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["registration_number"], "2026-CSE-001")
        self.assertEqual(response.data["auth_user_id"], self.student_user_id)

    def test_duplicate_registration_number_rejected(self):
        """Profile provisioning rejects duplicate registration numbers."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        data = {
            "registration_number": "2026-CSE-002",  # Already used by other_profile
            "department_id": "65a8e01b2c3d4e5f6a7b8d01",
            "admission_year": 2026,
            "current_semester": 1,
        }
        response = self.client.post(self.create_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_get_own_profile(self):
        """Student retrieves their own profile via /profile/me/."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_student_token}")
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["registration_number"], "2026-CSE-002")

    def test_student_update_permitted_fields(self):
        """Student updates their current semester, while sensitive fields are immutable."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_student_token}")
        update_data = {
            "current_semester": 3,
            "registration_number": "HACKED_REG_NUM",  # should be ignored
            "is_active": False,  # should be ignored
        }
        response = self.client.patch(self.me_url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_semester"], 3)
        self.assertEqual(response.data["registration_number"], "2026-CSE-002")
        self.assertTrue(response.data["is_active"])

    def test_idor_prevention_on_student_detail(self):
        """
        Verify that student A cannot access student B's profile by ID.
        Must return 403 Forbidden.
        """
        # Create profile for student A
        profile_a = StudentProfile.objects.create(
            auth_user_id=self.student_user_id,
            registration_number="2026-CSE-001",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            admission_year=2026,
            current_semester=1,
            is_active=True,
        )

        detail_url_b = reverse("students:profile-detail", kwargs={"pk": self.other_profile.pk})

        # Student A requests Student B's profile
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student_token}")
        response = self.client.get(detail_url_b)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin requests Student B's profile -> 200 OK
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response_admin = self.client.get(detail_url_b)
        self.assertEqual(response_admin.status_code, status.HTTP_200_OK)
        self.assertEqual(response_admin.data["registration_number"], "2026-CSE-002")

    def test_student_get_enrolled_courses(self):
        """Student retrieves their enrolled courses via /profile/me/enrollments/."""
        from datetime import date
        from apps.academics.models import AcademicTerm, CourseOffering, Enrollment, OfferingStatus, TermStatus

        term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )
        offering = CourseOffering.objects.create(
            course_id="65a8e01b2c3d4e5f6a7b8c01",
            faculty_id="fac_123",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            academic_term=term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )
        Enrollment.objects.create(student=self.other_profile, course_offering=offering)

        enrollments_url = reverse("students:profile-me-enrollments")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_student_token}")
        response = self.client.get(enrollments_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["course_id"], "65a8e01b2c3d4e5f6a7b8c01")
        self.assertEqual(response.data[0]["status"], "ENROLLED")
