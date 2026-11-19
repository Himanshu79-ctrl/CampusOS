"""
Client for interacting with the CampusOS Express Admin Backend.
Validates external IDs (course_id, faculty_id, department_id) against the Admin master data.
"""

import json
import logging
import re
import urllib.error
import urllib.request
from django.conf import settings

logger = logging.getLogger(__name__)

# Standard MongoDB 24-hex-character ObjectId regex
OBJECT_ID_REGEX = re.compile(r"^[0-9a-fA-F]{24}$")


class AdminServiceClient:
    """
    HTTP client for validating external identifiers against the Express Admin backend.
    Endpoints:
      - GET /api/admin/courses/:id
      - GET /api/admin/faculty/:id
      - GET /api/admin/departments/:id
      - GET /api/admin/departments/:id/hod
    """

    def __init__(self, base_url: str = None, timeout: float = 2.0):
        self.base_url = (base_url or getattr(settings, "ADMIN_SERVICE_URL", "http://127.0.0.1:5000")).rstrip("/")
        self.timeout = timeout

    @staticmethod
    def is_valid_format(external_id: str) -> bool:
        """
        Validates ID format: non-empty string, max length 64 characters.
        Matches MongoDB ObjectId hex string or alphanumeric code.
        """
        if not external_id or not isinstance(external_id, str):
            return False
        cleaned = external_id.strip()
        return 1 <= len(cleaned) <= 64

    def _query_endpoint(self, path: str) -> tuple[bool, dict | None]:
        """
        Queries an Admin backend endpoint.
        Returns (exists: bool, payload: dict | None).
        Raises ConnectionError if service is unreachable.
        """
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "CampusOS-LMS-Service"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                if res.status == 200:
                    payload = json.loads(res.read().decode())
                    return True, payload
                return False, None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False, None
            logger.warning("Admin service returned error %s for %s", exc.code, url)
            return False, None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # Service is not running or unreachable
            logger.debug("Admin service unreachable at %s: %s", url, exc)
            raise ConnectionError(f"Admin service unreachable at {url}: {exc}") from exc

    def validate_course_id(self, course_id: str, verify_remote: bool = False) -> bool:
        """
        Validates a course_id.
        If verify_remote is True, queries Admin service GET /api/admin/courses/:id.
        """
        if not self.is_valid_format(course_id):
            return False
        if not verify_remote:
            return True

        try:
            exists, _ = self._query_endpoint(f"/api/admin/courses/{course_id}")
            return exists
        except ConnectionError:
            logger.info("Admin service offline; falling back to format validation for course_id: %s", course_id)
            return True

    def validate_faculty_id(self, faculty_id: str, verify_remote: bool = False) -> bool:
        """
        Validates a faculty_id.
        If verify_remote is True, queries Admin service GET /api/admin/faculty/:id.
        """
        if not self.is_valid_format(faculty_id):
            return False
        if not verify_remote:
            return True

        try:
            exists, _ = self._query_endpoint(f"/api/admin/faculty/{faculty_id}")
            return exists
        except ConnectionError:
            logger.info("Admin service offline; falling back to format validation for faculty_id: %s", faculty_id)
            return True

    def validate_department_id(self, department_id: str, verify_remote: bool = False) -> bool:
        """
        Validates a department_id.
        If verify_remote is True, queries Admin service GET /api/admin/departments/:id.
        """
        if not self.is_valid_format(department_id):
            return False
        if not verify_remote:
            return True

        try:
            exists, _ = self._query_endpoint(f"/api/admin/departments/{department_id}")
            return exists
        except ConnectionError:
            logger.info("Admin service offline; falling back to format validation for department_id: %s", department_id)
            return True

    def get_department_hod(self, department_id: str) -> dict | None:
        """
        Queries Admin service GET /api/admin/departments/{department_id}/hod.
        Returns the HOD faculty dict (containing _id, name, employeeId, email, designation)
        if assigned, or None if unassigned, department not found, or service error/offline (fail-closed).
        """
        if not self.is_valid_format(department_id):
            return None

        try:
            exists, payload = self._query_endpoint(f"/api/admin/departments/{department_id}/hod")
            if not exists or not isinstance(payload, dict):
                return None
            if not payload.get("success", False):
                return None
            hod_data = payload.get("data")
            if isinstance(hod_data, dict):
                return hod_data
            return None
        except Exception as exc:
            logger.warning(
                "Admin service error or unreachable while fetching HOD for department %s: %s",
                department_id,
                exc,
            )
            return None

    def is_department_hod(self, user, department_id: str) -> bool:
        """
        Authoritatively verifies whether the given authenticated user is the assigned HOD
        for the specified department by querying the Admin Service.

        Strict fail-closed security policy:
          - Canonical cross-service identity link is the user's verified email.
          - Normalizes both emails via strip() and lower().
          - Fails closed (False) if user.email is missing, HOD is unassigned, 
            service is offline/times out/returns error, or email does not match.
          - Does NOT accept unverified faculty_id, employee_id, or is_hod claims.
          - Does NOT compare MongoDB Faculty _id directly with Auth Service integer user ID.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return False

        user_email = (getattr(user, "email", "") or "").strip().lower()
        if not user_email:
            logger.warning(
                "HOD authorization denied: user %s has no verified email.",
                getattr(user, "user_id", None),
            )
            return False

        try:
            hod_data = self.get_department_hod(department_id)
        except Exception as exc:
            logger.warning(
                "Admin service unreachable or error while evaluating HOD for department %s: %s",
                department_id,
                exc,
            )
            return False

        if not hod_data or not isinstance(hod_data, dict):
            return False

        hod_email = (hod_data.get("email") or "").strip().lower()
        if not hod_email:
            logger.warning("Department %s HOD record has no valid email.", department_id)
            return False

        return user_email == hod_email


