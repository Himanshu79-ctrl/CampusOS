"""
Unit and regression tests for dynamic Course and Department decoding in apps.academics.
Verifies:
  - AdminServiceClient retrieves and caches courses and departments from Admin service.
  - CourseOfferingSerializer dynamically resolves course_name, course_code, department_name, department_code.
  - Graceful fallback when Admin service is offline, unreachable, or returns 404.
  - No hardcoded department names, course names, or ObjectIds.
"""

import json
from datetime import date
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.test import TestCase
from rest_framework.test import APITestCase

from .admin_client import AdminServiceClient, clear_catalog_cache
from .models import AcademicTerm, CourseOffering, OfferingStatus, TermStatus
from .serializers import CourseOfferingListSerializer, CourseOfferingSerializer
from config.authentication import ExternalJWTAuthentication


class MockHttpResponse:
    def __init__(self, data, status_code: int = 200):
        self.status = status_code
        self._body = json.dumps(data).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class AdminCatalogClientTests(TestCase):
    def setUp(self):
        clear_catalog_cache()
        self.client = AdminServiceClient(base_url="http://127.0.0.1:5000", timeout=5.0)
        self.mock_courses = [
            {
                "_id": "6b002d29e5fc4d2ec633113d",
                "name": "Control System",
                "code": "EL0126",
                "department": {
                    "_id": "6afff8960979ad733ef114d0",
                    "name": "Electronics Engineering",
                    "code": "EL",
                },
                "credits": 4,
            },
            {
                "_id": "6afbf3e6481d101426bc03ae",
                "name": "Data Structures",
                "code": "CS201",
                "department": {
                    "_id": "6afff8aa0979ad733ef114d1",
                    "name": "Computer Science & Engineering",
                    "code": "CSE",
                },
                "credits": 3,
            },
        ]
        self.mock_departments = {
            "success": True,
            "data": [
                {
                    "_id": "6afff8960979ad733ef114d0",
                    "name": "Electronics Engineering",
                    "code": "EL",
                },
                {
                    "_id": "6afff8aa0979ad733ef114d1",
                    "name": "Computer Science & Engineering",
                    "code": "CSE",
                },
            ],
        }

    def tearDown(self):
        clear_catalog_cache()

    @patch("urllib.request.urlopen")
    def test_get_courses_and_find_by_id_or_code(self, mock_urlopen):
        mock_urlopen.return_value = MockHttpResponse(self.mock_courses)

        courses = self.client.get_courses()
        self.assertEqual(len(courses), 2)

        # Match by MongoDB ObjectId
        by_id = self.client.get_course("6b002d29e5fc4d2ec633113d")
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id["name"], "Control System")
        self.assertEqual(by_id["code"], "EL0126")

        # Match by code (case-insensitive)
        by_code = self.client.get_course("el0126")
        self.assertIsNotNone(by_code)
        self.assertEqual(by_code["name"], "Control System")

        # Second call uses cache (mock_urlopen call count does not increment for courses)
        courses_cached = self.client.get_courses()
        self.assertEqual(len(courses_cached), 2)
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("urllib.request.urlopen")
    def test_get_departments_and_find_by_id_or_code(self, mock_urlopen):
        mock_urlopen.return_value = MockHttpResponse(self.mock_departments)

        depts = self.client.get_departments()
        self.assertEqual(len(depts), 2)

        # Match by MongoDB ObjectId
        dept_by_id = self.client.get_department("6afff8960979ad733ef114d0")
        self.assertIsNotNone(dept_by_id)
        self.assertEqual(dept_by_id["name"], "Electronics Engineering")
        self.assertEqual(dept_by_id["code"], "EL")

        # Match by code
        dept_by_code = self.client.get_department("CSE")
        self.assertIsNotNone(dept_by_code)
        self.assertEqual(dept_by_code["name"], "Computer Science & Engineering")

    @patch("urllib.request.urlopen")
    def test_graceful_fallback_when_admin_service_is_offline(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Connection refused")

        courses = self.client.get_courses()
        self.assertEqual(courses, [])

        course = self.client.get_course("6b002d29e5fc4d2ec633113d")
        self.assertIsNone(course)

        depts = self.client.get_departments()
        self.assertEqual(depts, [])

        dept = self.client.get_department("6afff8960979ad733ef114d0")
        self.assertIsNone(dept)


class CourseOfferingSerializerCatalogResolutionTests(TestCase):
    def setUp(self):
        clear_catalog_cache()
        self.term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )
        self.offering = CourseOffering.objects.create(
            course_id="6b002d29e5fc4d2ec633113d",
            faculty_id="6b001d4b79943f38bdcb47f2",
            department_id="6afff8960979ad733ef114d0",
            academic_term=self.term,
            section="A",
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )
        self.mock_courses = [
            {
                "_id": "6b002d29e5fc4d2ec633113d",
                "name": "Control System",
                "code": "EL0126",
                "department": {
                    "_id": "6afff8960979ad733ef114d0",
                    "name": "Electronics Engineering",
                    "code": "EL",
                },
            }
        ]
        self.mock_departments = {
            "success": True,
            "data": [
                {
                    "_id": "6afff8960979ad733ef114d0",
                    "name": "Electronics Engineering",
                    "code": "EL",
                }
            ],
        }

    def tearDown(self):
        clear_catalog_cache()

    @patch("urllib.request.urlopen")
    def test_serializer_decodes_course_and_department_names(self, mock_urlopen):
        def side_effect(req, *args, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if "/api/admin/courses" in url:
                return MockHttpResponse(self.mock_courses)
            if "/api/admin/departments" in url:
                return MockHttpResponse(self.mock_departments)
            return MockHttpResponse({}, 404)

        mock_urlopen.side_effect = side_effect

        serializer = CourseOfferingSerializer(self.offering)
        data = serializer.data

        self.assertEqual(data["course_id"], "6b002d29e5fc4d2ec633113d")
        self.assertEqual(data["course_code"], "EL0126")
        self.assertEqual(data["course_name"], "Control System")
        self.assertEqual(data["department_id"], "6afff8960979ad733ef114d0")
        self.assertEqual(data["department_code"], "EL")
        self.assertEqual(data["department_name"], "Electronics Engineering")

    @patch("urllib.request.urlopen")
    def test_list_serializer_decodes_course_and_department(self, mock_urlopen):
        def side_effect(req, *args, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if "/api/admin/courses" in url:
                return MockHttpResponse(self.mock_courses)
            if "/api/admin/departments" in url:
                return MockHttpResponse(self.mock_departments)
            return MockHttpResponse({}, 404)

        mock_urlopen.side_effect = side_effect

        serializer = CourseOfferingListSerializer(self.offering)
        data = serializer.data

        self.assertEqual(data["course_code"], "EL0126")
        self.assertEqual(data["course_name"], "Control System")
        self.assertEqual(data["department_name"], "Electronics Engineering")

    @patch("urllib.request.urlopen")
    def test_serializer_graceful_fallback_when_admin_offline(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Connection refused")

        serializer = CourseOfferingSerializer(self.offering)
        data = serializer.data

        # Fallback values without crashing or hardcoded overrides
        self.assertEqual(data["course_code"], "6b002d29e5fc4d2ec633113d")
        self.assertEqual(data["course_name"], "")
        self.assertEqual(data["department_code"], "6afff8960979ad733ef114d0")
        self.assertEqual(data["department_name"], "")
