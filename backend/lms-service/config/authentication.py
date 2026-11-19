"""
Authentication layer for CampusOS LMS service.
Verifies external JWT tokens issued by Shailesh's Authentication service.
Supports SimpleJWT access tokens, external role claims, and RBAC mapping.
"""

import json
import logging
import os
import urllib.request
from datetime import datetime, timedelta, timezone
import jwt
from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

logger = logging.getLogger(__name__)


class AuthenticatedUser:
    """
    Stateless user representation constructed from verified external JWT claims.
    LMS does not maintain a local password or User table.
    """

    def __init__(
        self,
        user_id: str,
        role: str,
        email: str = "",
        department_id: str = "",
        claims: dict = None,
        username: str = "",
        full_name: str = "",
    ):
        self.user_id = str(user_id)
        self.role = str(role).lower()
        self.email = email
        self.username = username
        self.full_name = full_name
        self.department_id = str(department_id) if department_id else ""
        self.claims = claims or {}
        self.is_authenticated = True
        self.is_anonymous = False

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @property
    def is_faculty(self) -> bool:
        return self.role == "faculty"

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "academic_admin", "superadmin", "super_admin")

    @property
    def is_staff(self) -> bool:
        return self.is_admin

    def __str__(self) -> str:
        return f"User({self.user_id}, role={self.role})"

    def __repr__(self) -> str:
        return self.__str__()


class ExternalJWTAuthentication(BaseAuthentication):
    """
    DRF Authentication backend that validates Bearer JWT tokens issued by Auth service.
    Configurable via environment variables (JWT_SECRET_KEY, JWT_ALGORITHM).
    Supports SimpleJWT tokens with user_id, sub, role, and fallback mechanisms.
    """

    keyword = "Bearer"

    VALID_ROLES = {
        "student",
        "faculty",
        "admin",
        "academic_admin",
        "superadmin",
        "super_admin",
    }

    def authenticate_header(self, request):
        """
        Returns a string for the WWW-Authenticate header when an unauthenticated
        request is rejected, ensuring DRF responds with HTTP 401 Unauthorized instead of 403.
        """
        return f'{self.keyword} realm="api"'

    def authenticate(self, request):
        auth_header = get_authorization_header(request).split()

        if not auth_header:
            return None

        if auth_header[0].decode().lower() != self.keyword.lower():
            return None

        if len(auth_header) == 1:
            raise exceptions.AuthenticationFailed("Invalid Bearer header: token missing.")
        elif len(auth_header) > 2:
            raise exceptions.AuthenticationFailed(
                "Invalid Bearer header: token contains spaces."
            )

        token = auth_header[1].decode()
        return self.authenticate_token(token)

    def _fetch_profile_from_auth_service(self, auth_service_url: str, token: str) -> dict:
        """
        Queries the Auth service /api/user/me/ endpoint to resolve user profile details
        (such as role and verified email) when missing from JWT access token claims.
        """
        try:
            url = f"{auth_service_url.rstrip('/')}/api/user/me/"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=2.0) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode())
                    if isinstance(data, dict):
                        return data
        except Exception as exc:
            logger.debug("Could not resolve profile from Auth service endpoint: %s", exc)
        return {}

    def _fetch_role_from_auth_service(self, auth_service_url: str, token: str) -> str:
        """
        Queries the Auth service /api/user/me/ endpoint to resolve user role
        when the JWT access token does not include the custom 'role' claim.
        """
        profile = self._fetch_profile_from_auth_service(auth_service_url, token)
        return profile.get("role", "")

    def authenticate_token(self, token: str):
        secret_key = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
        algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")

        try:
            payload = jwt.decode(
                token,
                key=secret_key,
                algorithms=[algorithm],
                options={"verify_exp": True},
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Authentication token has expired.")
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid authentication token: {str(exc)}")

        # Enforce token type: prevent refresh tokens from authenticating API calls
        token_type = payload.get("token_type")
        if token_type and token_type != "access":
            raise exceptions.AuthenticationFailed(
                f"Invalid token type: '{token_type}' tokens cannot be used for API authentication."
            )

        # Extract user claims (SimpleJWT standard user_id or OIDC sub)
        user_id = payload.get("sub") or payload.get("user_id")
        if user_id is None:
            raise exceptions.AuthenticationFailed(
                "Token missing mandatory user identity claim ('sub' or 'user_id')."
            )

        # Extract or resolve user role & verified email
        role = payload.get("role")
        email = payload.get("email", "")

        auth_service_url = getattr(settings, "AUTH_SERVICE_URL", "")
        auth_service_profile = None

        username = payload.get("username", "")
        full_name = payload.get("full_name") or payload.get("name", "")

        # Query Auth service /api/user/me/ endpoint to resolve role, verified email, username and full_name
        if auth_service_url and (not role or not email or not full_name):
            auth_service_profile = self._fetch_profile_from_auth_service(auth_service_url, token)
            if auth_service_profile:
                if not role:
                    role = auth_service_profile.get("role", "")
                if not email:
                    email = auth_service_profile.get("email", "")
                if not username:
                    username = auth_service_profile.get("username", "")
                if not full_name:
                    full_name = auth_service_profile.get("full_name", "")

        if not role:
            role = getattr(settings, "JWT_DEFAULT_ROLE", "student")

        role = str(role).lower()
        if role not in self.VALID_ROLES:
            raise exceptions.AuthenticationFailed(
                f"Invalid or unsupported role: '{role}'."
            )
        department_id = payload.get("department_id", "")

        payload["username"] = username
        payload["full_name"] = full_name
        payload["email"] = email
        payload["role"] = role

        user = AuthenticatedUser(
            user_id=str(user_id),
            role=role,
            email=email,
            department_id=department_id,
            claims=payload,
            username=username,
            full_name=full_name,
        )
        return (user, token)

    @staticmethod
    def generate_token(
        user_id: str,
        role: str = "student",
        email: str = "",
        department_id: str = "",
        expires_in_minutes: int = 60,
        token_type: str = "access",
    ) -> str:
        """
        Utility for generating valid JWT tokens for tests and verified mock requests.
        Matches SimpleJWT payload structure.
        """
        secret_key = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
        algorithm = getattr(settings, "JWT_ALGORITHM", "HS256")

        now = datetime.now(timezone.utc)
        payload = {
            "token_type": token_type,
            "sub": str(user_id),
            "user_id": int(user_id) if str(user_id).isdigit() else str(user_id),
            "role": str(role).lower(),
            "email": email,
            "department_id": str(department_id),
            "iat": now,
            "exp": now + timedelta(minutes=expires_in_minutes),
        }
        return jwt.encode(payload, key=secret_key, algorithm=algorithm)
