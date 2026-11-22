"""
Unit and integration tests for faculty identity resolution and course offering filtering in apps.academics.
Covers:
  - Successful Auth ID to MongoDB faculty ID mapping (e.g. authUserId="2" -> MongoDB _id "6b001d4b79943f38bdcb47f2")
  - Admin service timeout handling (20s timeout, warning log with URL and exception)
  - Admin service returning an empty list (warning log, ensures no permanent empty caching)
  - Retry after a failed request (cache is not poisoned by failures)
  - Course offering filtering for authenticated faculty users
"""

import json
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .faculty_matcher import (
    _get_admin_faculty_records,
    clear_faculty_cache,
    filter_offerings_for_faculty,
    get_faculty_identifiers_for_user,
    is_faculty_assigned,
)
from .models import AcademicTerm, CourseOffering, OfferingStatus, TermStatus
from config.authentication import AuthenticatedUser, ExternalJWTAuthentication


class MockHttpResponse:
    """Mock for urllib.request.urlopen response."""

    def __init__(self, data: dict, status_code: int = 200):
        self.status = status_code
        self._body = json.dumps(data).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class FacultyMatcherUnitTests(TestCase):
    """
    Unit tests for faculty_matcher helper functions and cache behavior.
    """

    def setUp(self):
        clear_faculty_cache()
        self.mock_admin_data = {
            "data": [
                {
                    "_id": "6b001d4b79943f38bdcb47f2",
                    "name": "Dr. Anurag Sewak",
                    "employeeId": "FAC-CSE-201",
                    "email": "anurag@campusos.edu",
                    "username": "dr_anurag",
                    "authUserId": "2",
                    "department": {
                        "_id": "6afff8aa0979ad733ef114d1",
                        "name": "Computer Science & Engineering",
                        "code": "CSE",
                    },
                }
            ]
        }

    def tearDown(self):
        clear_faculty_cache()

    @patch("urllib.request.urlopen")
    def test_successful_auth_id_to_mongodb_id_mapping(self, mock_urlopen):
        """
        1. Verify that user_id='2' correctly resolves to MongoDB ObjectId '6b001d4b79943f38bdcb47f2'
           and employee ID / name identifiers when Admin service returns HTTP 200.
        """
        mock_urlopen.return_value = MockHttpResponse(self.mock_admin_data)

        user = AuthenticatedUser(user_id="2", role="faculty")
        identifiers = get_faculty_identifiers_for_user(user)

        self.assertIn("2", identifiers)
        self.assertIn("6b001d4b79943f38bdcb47f2", identifiers)
        self.assertIn("FAC-CSE-201", identifiers)
        self.assertIn("Dr. Anurag Sewak", identifiers)
        self.assertIn("anurag@campusos.edu", identifiers)

        # Verify timeout argument is 20.0 seconds
        args, kwargs = mock_urlopen.call_args
        self.assertEqual(kwargs.get("timeout"), 20.0)

    @patch("urllib.request.urlopen")
    def test_admin_service_timeout(self, mock_urlopen):
        """
        2. Verify that when Admin service times out, a WARNING is logged with the URL and exception,
           and the matcher falls back to the user's integer auth ID without crashing.
        """
        timeout_exc = TimeoutError("The read operation timed out")
        mock_urlopen.side_effect = timeout_exc

        user = AuthenticatedUser(user_id="2", role="faculty")

        with self.assertLogs("apps.academics.faculty_matcher", level="WARNING") as cm:
            identifiers = get_faculty_identifiers_for_user(user)

        # Warning logged with URL and exception
        self.assertTrue(any("Could not fetch faculty records from Admin service" in msg for msg in cm.output))
        self.assertTrue(any("timed out" in msg for msg in cm.output))

        # Identifier contains fallback user_id
        self.assertEqual(identifiers, {"2"})

    @patch("urllib.request.urlopen")
    def test_admin_service_returning_empty_list(self, mock_urlopen):
        """
        3. Verify that when Admin service returns HTTP 200 with an empty list,
           a warning is logged and the empty result is NOT permanently cached.
        """
        mock_urlopen.return_value = MockHttpResponse({"data": []})

        user = AuthenticatedUser(user_id="2", role="faculty")

        with self.assertLogs("apps.academics.faculty_matcher", level="WARNING") as cm:
            identifiers = get_faculty_identifiers_for_user(user)

        self.assertTrue(any("returned an empty faculty list" in msg for msg in cm.output))
        self.assertEqual(identifiers, {"2"})

        # Subsequent call should retry fetching because empty list is not cached
        mock_urlopen.return_value = MockHttpResponse(self.mock_admin_data)
        retry_identifiers = get_faculty_identifiers_for_user(user)
        self.assertIn("6b001d4b79943f38bdcb47f2", retry_identifiers)

    @patch("urllib.request.urlopen")
    def test_retry_after_failed_request(self, mock_urlopen):
        """
        4. Verify that after a failed request (e.g. connection refused during spin-up),
           the failure is not cached, and a subsequent attempt immediately retries and succeeds.
        """
        # First call fails
        mock_urlopen.side_effect = URLError("Connection refused")
        user = AuthenticatedUser(user_id="2", role="faculty")

        with self.assertLogs("apps.academics.faculty_matcher", level="WARNING"):
            records_first = _get_admin_faculty_records()
        self.assertEqual(records_first, [])

        # Second call succeeds
        mock_urlopen.side_effect = None
        mock_urlopen.return_value = MockHttpResponse(self.mock_admin_data)

        records_second = _get_admin_faculty_records()
        self.assertEqual(len(records_second), 1)
        self.assertEqual(records_second[0]["_id"], "6b001d4b79943f38bdcb47f2")

        # Identity resolution succeeds on retry
        identifiers = get_faculty_identifiers_for_user(user)
        self.assertIn("6b001d4b79943f38bdcb47f2", identifiers)


class FacultyCourseOfferingFilteringAPITests(APITestCase):
    """
    5. Integration tests verifying course offering filtering for faculty users via API.
    """

    def setUp(self):
        clear_faculty_cache()

        self.mock_admin_data = {
            "data": [
                {
                    "_id": "6b001d4b79943f38bdcb47f2",
                    "name": "Dr. Anurag Sewak",
                    "employeeId": "FAC-CSE-201",
                    "email": "anurag@campusos.edu",
                    "username": "dr_anurag",
                    "authUserId": "2",
                },
                {
                    "_id": "6afc347ed9e74d0557163928",
                    "name": "Dr. Kalpana Singh",
                    "employeeId": "FAC-CSE-001",
                    "email": "kalapna@example.com",
                    "username": "faculty_live",
                    "authUserId": "17",
                },
            ]
        }

        # Create active academic term
        self.term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )

        # Course Offering 1: Assigned to Anurag Sewak (MongoDB ObjectId: 6b001d4b79943f38bdcb47f2)
        self.anurag_offering = CourseOffering.objects.create(
            course_id="6b002d29e5fc4d2ec633113d",  # Control System
            faculty_id="6b001d4b79943f38bdcb47f2",
            department_id="6afff8960979ad733ef114d0",  # EL
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )

        # Course Offering 2: Assigned to Kalpana Singh (MongoDB ObjectId: 6afc347ed9e74d0557163928)
        self.kalpana_offering = CourseOffering.objects.create(
            course_id="6afbf3e6481d101426bc03ae",  # Data Structures
            faculty_id="6afc347ed9e74d0557163928",
            department_id="6afff8aa0979ad733ef114d1",  # CSE
            academic_term=self.term,
            section="B",
            capacity=40,
            status=OfferingStatus.PUBLISHED,
        )

        # Generate JWT for Anurag Sewak (Auth user_id=2, role=faculty)
        self.anurag_token = ExternalJWTAuthentication.generate_token(
            user_id="2", role="faculty"
        )

    def tearDown(self):
        clear_faculty_cache()

    @patch("urllib.request.urlopen")
    def test_faculty_sees_assigned_course_offering_via_api(self, mock_urlopen):
        """
        Verify that Dr. Anurag Sewak (user_id='2') fetches only his assigned offering
        ('Control System' with faculty_id='6b001d4b79943f38bdcb47f2') from GET /api/academics/offerings/.
        """
        mock_urlopen.return_value = MockHttpResponse(self.mock_admin_data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.anurag_token}")
        url = reverse("academics:offering-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)

        # Should only contain Anurag Sewak's offering
        offering_ids = [r["id"] for r in results]
        self.assertIn(self.anurag_offering.id, offering_ids)
        self.assertNotIn(self.kalpana_offering.id, offering_ids)
        self.assertEqual(len(results), 1)

    @patch("urllib.request.urlopen")
    def test_faculty_courses_page_query_param_compatibility(self, mock_urlopen):
        """
        Verify that GET /api/academics/offerings/?faculty=2 (as called by FacultyCoursesPage.jsx)
        returns Dr. Anurag Sewak's offering correctly.
        """
        mock_urlopen.return_value = MockHttpResponse(self.mock_admin_data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.anurag_token}")
        url = reverse("academics:offering-list-create")
        response = self.client.get(f"{url}?faculty=2")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)

        offering_ids = [r["id"] for r in results]
        self.assertIn(self.anurag_offering.id, offering_ids)
        self.assertEqual(len(results), 1)
