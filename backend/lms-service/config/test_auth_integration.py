"""
Comprehensive Integration Tests for Auth Service & LMS Integration.
Verifies real SimpleJWT tokens, role mapping, RBAC permissions, and Admin ID validation.
"""

from datetime import date, datetime, timedelta, timezone
from django.conf import settings
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
import jwt

try:
    from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
    SIMPLE_JWT_AVAILABLE = True
except ImportError:
    SIMPLE_JWT_AVAILABLE = False

from apps.academics.admin_client import AdminServiceClient
from apps.academics.models import AcademicTerm, CourseOffering, OfferingStatus, TermStatus
from apps.students.models import StudentProfile
from config.authentication import ExternalJWTAuthentication


class AuthIntegrationTests(TestCase):
    """
    Integration tests verifying LMS authentication against Shailesh's Auth service.
    """

    def setUp(self):
        self.client = APIClient()
        self.auth_secret = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
        self.algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")

        # Provision baseline active academic term
        self.active_term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )

    def _generate_simplejwt_access_token(self, user_id=1, custom_claims=None) -> str:
        """
        Generates an authentic SimpleJWT AccessToken signed with the configured secret.
        """
        if SIMPLE_JWT_AVAILABLE:
            token = AccessToken()
            token["user_id"] = user_id
            if custom_claims:
                for k, v in custom_claims.items():
                    token[k] = v
            return str(token)

        # Fallback to direct PyJWT matching SimpleJWT structure exactly
        now = datetime.now(timezone.utc)
        payload = {
            "token_type": "access",
            "exp": now + timedelta(minutes=60),
            "iat": now,
            "jti": "d3b07384d113edec49eaa6238ad5ff00",
            "user_id": user_id,
        }
        if custom_claims:
            payload.update(custom_claims)
        return jwt.encode(payload, key=self.auth_secret, algorithm=self.algorithm)

    def test_real_simplejwt_token_accepted_and_defaults_to_student(self):
        """
        A real SimpleJWT access token (which contains user_id and token_type='access'
        without a role claim) is accepted and safely mapped to student role.
        """
        token = self._generate_simplejwt_access_token(user_id=101)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/academics/terms/current/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Fall 2026")

    def test_student_profile_provisioning_with_auth_user_id(self):
        """
        A student user can provision their profile using the user_id extracted from the token.
        """
        token = self._generate_simplejwt_access_token(user_id=202)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        payload = {
            "auth_user_id": "202",
            "registration_number": "CS-2026-0042",
            "department_id": "DEP_CSE",
            "admission_year": 2026,
            "current_semester": 1,
        }
        response = self.client.post("/api/students/profile/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["auth_user_id"], "202")

        # Verify profile can be retrieved via /profile/me/
        me_resp = self.client.get("/api/students/profile/me/")
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data["registration_number"], "CS-2026-0042")

    def test_super_admin_role_mapping(self):
        """
        Shailesh's 'super_admin' role is recognized and granted academic admin permissions.
        """
        token = self._generate_simplejwt_access_token(
            user_id=999,
            custom_claims={"role": "super_admin"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Super admin creates a new academic term
        payload = {
            "name": "Spring 2027",
            "academic_year": "2026-2027",
            "term_number": 2,
            "start_date": "2027-01-10",
            "end_date": "2027-05-15",
            "status": "UPCOMING",
            "is_enrollment_open": False,
        }
        response = self.client.post("/api/academics/terms/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_role_mapping(self):
        """
        Shailesh's 'admin' role is recognized as an academic admin.
        """
        token = self._generate_simplejwt_access_token(
            user_id=888,
            custom_claims={"role": "admin"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Admin can close enrollment window
        url = f"/api/academics/terms/{self.active_term.id}/enrollment-window/"
        response = self.client.post(url, {"is_open": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_enrollment_open"])

    def test_faculty_role_mapping_and_permission_enforcement(self):
        """
        Shailesh's 'faculty' role is recognized; faculty can view roster of their course offering.
        """
        faculty_user_id = "fac_777"
        token = self._generate_simplejwt_access_token(
            user_id=777,
            custom_claims={"role": "faculty", "sub": faculty_user_id},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Create offering assigned to this faculty
        offering = CourseOffering.objects.create(
            course_id="607f1f77bcf86cd799439011",
            faculty_id=faculty_user_id,
            department_id="607f1f77bcf86cd799439022",
            academic_term=self.active_term,
            section="A",
            capacity=40,
            status=OfferingStatus.PUBLISHED,
        )

        # Faculty views students in their offering
        response = self.client.get(f"/api/academics/offerings/{offering.id}/students/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Faculty cannot perform academic admin actions (e.g. create term)
        term_payload = {
            "name": "Summer 2027",
            "academic_year": "2026-2027",
            "term_number": 3,
            "start_date": "2027-06-01",
            "end_date": "2027-07-31",
            "status": "UPCOMING",
        }
        res_fail = self.client.post("/api/academics/terms/", term_payload)
        self.assertEqual(res_fail.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_signature_rejected(self):
        """
        A JWT signed with an untrusted or incorrect secret key is rejected with HTTP 401.
        """
        fake_secret = "wrong-untrusted-secret-key-1234567890"
        now = datetime.now(timezone.utc)
        payload = {
            "token_type": "access",
            "user_id": 505,
            "role": "student",
            "exp": now + timedelta(minutes=60),
            "iat": now,
        }
        forged_token = jwt.encode(payload, key=fake_secret, algorithm="HS256")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {forged_token}")
        response = self.client.get("/api/academics/terms/current/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid authentication token", response.data["detail"])

    def test_expired_token_rejected(self):
        """
        An expired token is rejected with HTTP 401.
        """
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        payload = {
            "token_type": "access",
            "user_id": 505,
            "role": "student",
            "exp": past,
            "iat": past - timedelta(minutes=60),
        }
        expired_token = jwt.encode(payload, key=self.auth_secret, algorithm=self.algorithm)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_token}")
        response = self.client.get("/api/academics/terms/current/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("expired", response.data["detail"])

    def test_refresh_token_rejected_for_api_access(self):
        """
        A refresh token passed in the Authorization header is rejected with HTTP 401.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "token_type": "refresh",
            "user_id": 505,
            "exp": now + timedelta(days=7),
            "iat": now,
        }
        refresh_token = jwt.encode(payload, key=self.auth_secret, algorithm=self.algorithm)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_token}")
        response = self.client.get("/api/academics/terms/current/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid token type", response.data["detail"])

    def test_unsupported_role_rejected(self):
        """
        A token with an unknown or unsupported role is rejected with HTTP 401.
        """
        token = self._generate_simplejwt_access_token(
            user_id=606,
            custom_claims={"role": "intruder"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/academics/terms/current/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid or unsupported role", response.data["detail"])

    def test_idor_protection_between_students(self):
        """
        Student A cannot access Student B's academic profile.
        """
        # Create Student B profile
        profile_b = StudentProfile.objects.create(
            auth_user_id="student_b_id",
            registration_number="CS-2026-9999",
            department_id="DEP_CSE",
            admission_year=2026,
            current_semester=1,
        )

        # Authenticate as Student A
        token_a = self._generate_simplejwt_access_token(
            user_id="student_a_id",
            custom_claims={"role": "student"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_a}")

        # Student A tries to read Student B's profile by ID
        response = self.client.get(f"/api/students/profile/{profile_b.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminClientValidationTests(TestCase):
    """
    Unit tests for AdminServiceClient format validation and integration contracts.
    """

    def test_format_validation(self):
        client = AdminServiceClient()

        # Valid MongoDB ObjectId (24 hex characters)
        self.assertTrue(client.is_valid_format("507f1f77bcf86cd799439011"))

        # Valid alphanumeric external IDs
        self.assertTrue(client.is_valid_format("CS101"))
        self.assertTrue(client.is_valid_format("FAC-001"))
        self.assertTrue(client.is_valid_format("DEP_CSE"))

        # Invalid formats
        self.assertFalse(client.is_valid_format(""))
        self.assertFalse(client.is_valid_format("   "))
        self.assertFalse(client.is_valid_format(None))
        self.assertFalse(client.is_valid_format("a" * 65))  # exceeds 64 chars

    def test_offline_fallback_behavior(self):
        """
        When verify_remote is False or service is offline, validate methods succeed for valid formats.
        """
        client = AdminServiceClient(base_url="http://127.0.0.1:59999")
        self.assertTrue(client.validate_course_id("507f1f77bcf86cd799439011"))
        self.assertTrue(client.validate_faculty_id("507f1f77bcf86cd799439022"))
        self.assertTrue(client.validate_department_id("507f1f77bcf86cd799439033"))
