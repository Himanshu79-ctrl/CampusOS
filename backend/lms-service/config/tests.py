"""
Tests for core configuration, health check endpoint, and JWT authentication layer.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import jwt
from django.conf import settings
from django.test import Client, SimpleTestCase
from django.urls import reverse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from config.authentication import AuthenticatedUser, ExternalJWTAuthentication


class HealthCheckTests(SimpleTestCase):
    """
    Test cases for /api/health/ endpoint.
    """

    def setUp(self):
        self.client = Client()
        self.health_url = reverse("health-check")

    def test_health_url_resolves(self):
        """Test health check URL resolves to /api/health/."""
        self.assertEqual(self.health_url, "/api/health/")

    @patch("config.views.check_database_connection")
    def test_health_check_database_connected(self, mock_check_db):
        """Test health check returns 200 OK when database is accessible."""
        mock_check_db.return_value = None
        response = self.client.get(self.health_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "service": "CampusOS LMS",
                "database": "connected",
            },
        )

    @patch("config.views.check_database_connection")
    def test_health_check_database_disconnected(self, mock_check_db):
        """Test health check returns 503 Service Unavailable when database is inaccessible."""
        mock_check_db.side_effect = Exception("Connection refused")
        response = self.client.get(self.health_url)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "error",
                "service": "CampusOS LMS",
                "database": "disconnected",
            },
        )


class JWTAuthenticationUnitTests(SimpleTestCase):
    """
    Unit tests for ExternalJWTAuthentication verification rules.
    """

    def setUp(self):
        self.auth = ExternalJWTAuthentication()
        self.factory = APIRequestFactory()
        self.secret_key = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
        self.algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")

    def test_valid_token_authenticates_user(self):
        """Valid token unpacks AuthenticatedUser with correct roles and claims."""
        token = ExternalJWTAuthentication.generate_token(
            user_id="usr_valid_001",
            role="student",
            email="valid@campus.edu",
            department_id="dept_123",
        )
        request = self.factory.get("/api/health/", HTTP_AUTHORIZATION=f"Bearer {token}")
        user_auth_tuple = self.auth.authenticate(request)

        self.assertIsNotNone(user_auth_tuple)
        user, returned_token = user_auth_tuple
        self.assertEqual(user.user_id, "usr_valid_001")
        self.assertEqual(user.role, "student")
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_faculty)
        self.assertFalse(user.is_admin)
        self.assertEqual(user.email, "valid@campus.edu")
        self.assertEqual(user.department_id, "dept_123")
        self.assertEqual(returned_token, token)

    def test_expired_token_raises_authentication_failed(self):
        """Expired JWT raises AuthenticationFailed."""
        expired_payload = {
            "sub": "usr_expired_001",
            "role": "student",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        }
        token = jwt.encode(expired_payload, key=self.secret_key, algorithm=self.algorithm)
        request = self.factory.get("/api/health/", HTTP_AUTHORIZATION=f"Bearer {token}")

        with self.assertRaises(AuthenticationFailed) as ctx:
            self.auth.authenticate(request)
        self.assertIn("expired", str(ctx.exception))

    def test_missing_mandatory_claims_raises_authentication_failed(self):
        """Token missing user identity claim ('sub' or 'user_id') raises AuthenticationFailed."""
        invalid_payload = {
            "role": "student",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
        }
        token = jwt.encode(invalid_payload, key=self.secret_key, algorithm=self.algorithm)
        request = self.factory.get("/api/health/", HTTP_AUTHORIZATION=f"Bearer {token}")

        with self.assertRaises(AuthenticationFailed) as ctx:
            self.auth.authenticate(request)
        self.assertIn("mandatory user identity claim", str(ctx.exception))

    def test_malformed_token_raises_authentication_failed(self):
        """Malformed token string raises AuthenticationFailed."""
        request = self.factory.get("/api/health/", HTTP_AUTHORIZATION="Bearer not.a.valid.jwt.token")

        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_non_bearer_header_ignored(self):
        """Requests with non-Bearer Authorization headers are ignored (returns None)."""
        request = self.factory.get("/api/health/", HTTP_AUTHORIZATION="Basic dXNlcjpwYXNz")
        self.assertIsNone(self.auth.authenticate(request))
