"""
Automated unit tests for CampusOS Auth Service, including the bootstrap_superadmin management command.
"""

import os
from io import StringIO
from unittest.mock import patch
import jwt

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import CustomUser


class BootstrapSuperAdminCommandTests(TestCase):
    """
    Test suite for the `bootstrap_superadmin` management command.
    Ensures secure one-time bootstrap, strict environment variable enforcement,
    role integrity, idempotency, and non-exposure of secrets.
    """

    def setUp(self):
        self.username = "bootstrap_admin"
        self.email = "admin@campusos.internal"
        self.password = "SuperSecurePassword987!#"

    def test_missing_all_environment_variables(self):
        """Should raise CommandError when all required variables are absent."""
        env = {
            "SUPERADMIN_USERNAME": "",
            "SUPERADMIN_EMAIL": "",
            "SUPERADMIN_PASSWORD": "",
        }
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_superadmin")

            err_msg = str(ctx.exception)
            self.assertIn("SUPERADMIN_USERNAME", err_msg)
            self.assertIn("SUPERADMIN_EMAIL", err_msg)
            self.assertIn("SUPERADMIN_PASSWORD", err_msg)

    def test_missing_individual_environment_variables(self):
        """Should raise CommandError when any individual variable is missing."""
        # 1. Missing username
        with patch.dict(
            os.environ,
            {"SUPERADMIN_USERNAME": "", "SUPERADMIN_EMAIL": self.email, "SUPERADMIN_PASSWORD": self.password},
            clear=False,
        ):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_superadmin")
            self.assertIn("SUPERADMIN_USERNAME", str(ctx.exception))

        # 2. Missing email
        with patch.dict(
            os.environ,
            {"SUPERADMIN_USERNAME": self.username, "SUPERADMIN_EMAIL": "", "SUPERADMIN_PASSWORD": self.password},
            clear=False,
        ):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_superadmin")
            self.assertIn("SUPERADMIN_EMAIL", str(ctx.exception))

        # 3. Missing password
        with patch.dict(
            os.environ,
            {"SUPERADMIN_USERNAME": self.username, "SUPERADMIN_EMAIL": self.email, "SUPERADMIN_PASSWORD": ""},
            clear=False,
        ):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_superadmin")
            self.assertIn("SUPERADMIN_PASSWORD", str(ctx.exception))

    def test_successful_superadmin_creation(self):
        """Should successfully create a superadmin user with correct flags and hashed password."""
        env = {
            "SUPERADMIN_USERNAME": self.username,
            "SUPERADMIN_EMAIL": self.email,
            "SUPERADMIN_PASSWORD": self.password,
        }
        out = StringIO()

        with patch.dict(os.environ, env, clear=False):
            call_command("bootstrap_superadmin", stdout=out)

        # Verify output does NOT contain the raw password
        stdout_content = out.getvalue()
        self.assertNotIn(self.password, stdout_content)
        self.assertIn(self.username, stdout_content)
        self.assertIn("successfully created", stdout_content)

        # Verify user record in database
        user = CustomUser.objects.filter(username=self.username).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, self.email)
        self.assertEqual(user.role, "super_admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password(self.password))

    def test_existing_superadmin_idempotency(self):
        """
        When the superadmin already exists with role='super_admin',
        the command should report it safely and NOT modify its password.
        """
        # Create initial superadmin with a known password
        initial_user = CustomUser.objects.create_superuser(
            username=self.username,
            email=self.email,
            password=self.password,
            role="super_admin",
        )
        self.assertTrue(initial_user.check_password(self.password))

        # Attempt to run bootstrap again with a DIFFERENT password
        new_password = "AttemptedPasswordChange999!"
        env = {
            "SUPERADMIN_USERNAME": self.username,
            "SUPERADMIN_EMAIL": self.email,
            "SUPERADMIN_PASSWORD": new_password,
        }
        out = StringIO()

        with patch.dict(os.environ, env, clear=False):
            call_command("bootstrap_superadmin", stdout=out)

        stdout_content = out.getvalue()
        self.assertIn("already exists", stdout_content)
        self.assertNotIn(new_password, stdout_content)
        self.assertNotIn(self.password, stdout_content)

        # Verify original password was NOT changed
        initial_user.refresh_from_db()
        self.assertTrue(initial_user.check_password(self.password))
        self.assertFalse(initial_user.check_password(new_password))

    def test_existing_user_with_different_role_rejected(self):
        """
        If a user with the specified username already exists with another role (e.g. 'student'),
        the command must reject promotion and raise CommandError.
        """
        student_user = CustomUser.objects.create_user(
            username=self.username,
            email=self.email,
            password="ExistingStudentPassword123",
            role="student",
        )
        self.assertEqual(student_user.role, "student")

        env = {
            "SUPERADMIN_USERNAME": self.username,
            "SUPERADMIN_EMAIL": self.email,
            "SUPERADMIN_PASSWORD": self.password,
        }

        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(CommandError) as ctx:
                call_command("bootstrap_superadmin")

            err_msg = str(ctx.exception)
            self.assertIn("already exists with role 'student'", err_msg)
            self.assertIn("Cannot promote", err_msg)

        # Verify role was NOT changed
        student_user.refresh_from_db()
        self.assertEqual(student_user.role, "student")
        self.assertFalse(student_user.is_superuser)
        self.assertFalse(student_user.is_staff)


class JWTRoleClaimTests(TestCase):
    """
    Test suite verifying that SimpleJWT tokens issued by Auth service
    embed the user's role claim in both access and refresh tokens,
    without unnecessary extra claims, across all user roles.
    """

    def setUp(self):
        self.client = APIClient()
        self.password = "ValidCampusPass123!"
        self.jwt_secret = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
        self.jwt_algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")

    def _decode_token(self, token_str: str) -> dict:
        return jwt.decode(
            token_str,
            self.jwt_secret,
            algorithms=[self.jwt_algorithm],
            options={"verify_exp": False},
        )

    def test_superadmin_login_token_contains_role(self):
        """Super Admin login must return access and refresh tokens with role='super_admin'."""
        CustomUser.objects.create_user(
            username="test_superadmin",
            email="superadmin@campusos.edu",
            password=self.password,
            role="super_admin",
        )
        response = self.client.post(
            "/api/token/",
            {"username": "test_superadmin", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)

        access_payload = self._decode_token(data["access"])
        refresh_payload = self._decode_token(data["refresh"])

        self.assertEqual(access_payload.get("role"), "super_admin")
        self.assertEqual(refresh_payload.get("role"), "super_admin")

        # Verify no unnecessary claims added
        self.assertNotIn("email", access_payload)
        self.assertNotIn("username", access_payload)
        self.assertNotIn("full_name", access_payload)

    def test_admin_login_token_contains_role(self):
        """Admin login must return tokens with role='admin'."""
        CustomUser.objects.create_user(
            username="test_admin",
            email="admin@campusos.edu",
            password=self.password,
            role="admin",
        )
        response = self.client.post(
            "/api/token/",
            {"username": "test_admin", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        access_payload = self._decode_token(data["access"])
        refresh_payload = self._decode_token(data["refresh"])

        self.assertEqual(access_payload.get("role"), "admin")
        self.assertEqual(refresh_payload.get("role"), "admin")

    def test_student_login_token_contains_role(self):
        """Student login must return tokens with role='student'."""
        CustomUser.objects.create_user(
            username="test_student",
            email="student@campusos.edu",
            password=self.password,
            role="student",
        )
        response = self.client.post(
            "/api/token/",
            {"username": "test_student", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        access_payload = self._decode_token(data["access"])
        refresh_payload = self._decode_token(data["refresh"])

        self.assertEqual(access_payload.get("role"), "student")
        self.assertEqual(refresh_payload.get("role"), "student")

    def test_faculty_login_token_contains_role(self):
        """Faculty login must return tokens with role='faculty'."""
        CustomUser.objects.create_user(
            username="test_faculty",
            email="faculty@campusos.edu",
            password=self.password,
            role="faculty",
        )
        response = self.client.post(
            "/api/token/",
            {"username": "test_faculty", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        access_payload = self._decode_token(data["access"])
        refresh_payload = self._decode_token(data["refresh"])

        self.assertEqual(access_payload.get("role"), "faculty")
        self.assertEqual(refresh_payload.get("role"), "faculty")

    def test_token_refresh_endpoint_preserves_role(self):
        """Refreshing an access token through /api/token/refresh/ must preserve the role claim."""
        CustomUser.objects.create_user(
            username="test_refresh_user",
            email="refresh@campusos.edu",
            password=self.password,
            role="super_admin",
        )
        login_resp = self.client.post(
            "/api/token/",
            {"username": "test_refresh_user", "password": self.password},
            format="json",
        )
        refresh_token = login_resp.json()["refresh"]

        refresh_resp = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        self.assertEqual(refresh_resp.status_code, status.HTTP_200_OK)
        new_access = refresh_resp.json()["access"]

        new_access_payload = self._decode_token(new_access)
        self.assertEqual(new_access_payload.get("role"), "super_admin")

    def test_invalid_credentials_rejected(self):
        """Invalid credentials must return 401 Unauthorized."""
        CustomUser.objects.create_user(
            username="test_auth_fail",
            password=self.password,
            role="student",
        )
        response = self.client.post(
            "/api/token/",
            {"username": "test_auth_fail", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
