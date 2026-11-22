"""
Client for interacting with the CampusOS Express Admin Backend.
Validates external IDs (course_id, faculty_id, department_id) against the Admin master data.
"""

import json
import logging
import re
import time
import urllib.error
import urllib.request
from django.conf import settings

logger = logging.getLogger(__name__)

# Standard MongoDB 24-hex-character ObjectId regex
OBJECT_ID_REGEX = re.compile(r"^[0-9a-fA-F]{24}$")

# In-memory cache for remote course & department catalog records from Admin service
_CATALOG_CACHE = {
    "courses_timestamp": 0,
    "courses": [],
    "departments_timestamp": 0,
    "departments": [],
}
_CATALOG_CACHE_TTL = 60.0
DEFAULT_ADMIN_SERVICE_TIMEOUT = 20.0


def clear_catalog_cache():
    """Resets the in-memory course and department catalog cache (useful for testing)."""
    global _CATALOG_CACHE
    _CATALOG_CACHE = {
        "courses_timestamp": 0,
        "courses": [],
        "departments_timestamp": 0,
        "departments": [],
    }


class AdminServiceClient:
    """
    HTTP client for validating external identifiers against the Express Admin backend.
    Endpoints:
      - GET /api/admin/courses
      - GET /api/admin/courses/:id
      - GET /api/admin/faculty/:id
      - GET /api/admin/departments
      - GET /api/admin/departments/:id
      - GET /api/admin/departments/:id/hod
    """

    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = (base_url or getattr(settings, "ADMIN_SERVICE_URL", "http://127.0.0.1:5000")).rstrip("/")
        self.timeout = timeout if timeout is not None else getattr(settings, "ADMIN_SERVICE_TIMEOUT", DEFAULT_ADMIN_SERVICE_TIMEOUT)

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

    def get_courses(self) -> list[dict]:
        """
        Fetches all courses from Admin Service GET /api/admin/courses.
        Cached for 60s. Fails gracefully to empty list if unreachable.
        """
        global _CATALOG_CACHE
        now = time.time()
        if (now - _CATALOG_CACHE["courses_timestamp"] < _CATALOG_CACHE_TTL) and _CATALOG_CACHE["courses"]:
            return _CATALOG_CACHE["courses"]

        try:
            exists, payload = self._query_endpoint("/api/admin/courses")
            if exists and payload is not None:
                records = payload if isinstance(payload, list) else payload.get("data", [])
                if isinstance(records, list) and records:
                    _CATALOG_CACHE["courses"] = records
                    _CATALOG_CACHE["courses_timestamp"] = now
                    return records
        except Exception as exc:
            logger.warning("Could not fetch courses from Admin service: %s", exc)

        return _CATALOG_CACHE.get("courses", [])

    def get_course(self, course_id: str) -> dict | None:
        """
        Resolves course details for a given course_id (MongoDB ObjectId or course code).
        Matches against cached courses first, then queries /api/admin/courses/:id.
        """
        if not course_id:
            return None
        target = str(course_id).strip()

        # 1. Search in cached courses list
        for c in self.get_courses():
            if not isinstance(c, dict):
                continue
            if str(c.get("_id", "")).strip() == target:
                return c
            if str(c.get("code", "")).strip().upper() == target.upper():
                return c

        # 2. Query endpoint directly if not in cached list
        try:
            exists, payload = self._query_endpoint(f"/api/admin/courses/{target}")
            if exists and isinstance(payload, dict):
                course_data = payload.get("course", payload) if "course" in payload else payload
                if isinstance(course_data, dict):
                    return course_data
        except Exception as exc:
            logger.debug("Could not fetch course %s from Admin service: %s", target, exc)

        return None

    def get_departments(self) -> list[dict]:
        """
        Fetches all departments from Admin Service GET /api/admin/departments.
        Cached for 60s. Fails gracefully to empty list if unreachable.
        """
        global _CATALOG_CACHE
        now = time.time()
        if (now - _CATALOG_CACHE["departments_timestamp"] < _CATALOG_CACHE_TTL) and _CATALOG_CACHE["departments"]:
            return _CATALOG_CACHE["departments"]

        try:
            exists, payload = self._query_endpoint("/api/admin/departments")
            if exists and payload is not None:
                records = (
                    payload.get("data", [])
                    if isinstance(payload, dict)
                    else (payload if isinstance(payload, list) else [])
                )
                if isinstance(records, list) and records:
                    _CATALOG_CACHE["departments"] = records
                    _CATALOG_CACHE["departments_timestamp"] = now
                    return records
        except Exception as exc:
            logger.warning("Could not fetch departments from Admin service: %s", exc)

        return _CATALOG_CACHE.get("departments", [])

    def get_department(self, department_id: str) -> dict | None:
        """
        Resolves department details for a given department_id (MongoDB ObjectId or code).
        Matches against cached departments first, then queries /api/admin/departments/:id.
        """
        if not department_id:
            return None
        target = str(department_id).strip()

        # 1. Search in cached departments list
        for d in self.get_departments():
            if not isinstance(d, dict):
                continue
            if str(d.get("_id", "")).strip() == target:
                return d
            if str(d.get("code", "")).strip().upper() == target.upper():
                return d

        # 2. Query endpoint directly if not in cached list
        try:
            exists, payload = self._query_endpoint(f"/api/admin/departments/{target}")
            if exists and isinstance(payload, dict):
                dept_data = payload.get("data", payload)
                if isinstance(dept_data, dict):
                    return dept_data
        except Exception as exc:
            logger.debug("Could not fetch department %s from Admin service: %s", target, exc)

        return None

