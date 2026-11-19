"""
Tests for StudentProfile model in apps.students.
"""

from django.db import IntegrityError
from django.test import TestCase

from apps.students.models import StudentProfile


class StudentProfileModelTests(TestCase):
    """
    Test suite for StudentProfile model creation, constraints, and validation.
    """

    def setUp(self):
        self.student_data = {
            "auth_user_id": "usr_auth_001",
            "registration_number": "2026-CSE-001",
            "department_id": "65a8e01b2c3d4e5f6a7b8c9d",
            "admission_year": 2026,
            "current_semester": 1,
            "is_active": True,
        }

    def test_create_student_profile(self):
        """Test creating a valid student profile."""
        student = StudentProfile.objects.create(**self.student_data)
        self.assertEqual(student.registration_number, "2026-CSE-001")
        self.assertEqual(student.auth_user_id, "usr_auth_001")
        self.assertTrue(student.is_active)
        self.assertIn("2026-CSE-001", str(student))

    def test_duplicate_auth_user_id_rejected(self):
        """Test that auth_user_id uniqueness is strictly enforced."""
        StudentProfile.objects.create(**self.student_data)
        duplicate_data = self.student_data.copy()
        duplicate_data["registration_number"] = "2026-CSE-002"

        with self.assertRaises(IntegrityError):
            StudentProfile.objects.create(**duplicate_data)

    def test_duplicate_registration_number_rejected(self):
        """Test that registration_number uniqueness is strictly enforced."""
        StudentProfile.objects.create(**self.student_data)
        duplicate_data = self.student_data.copy()
        duplicate_data["auth_user_id"] = "usr_auth_002"

        with self.assertRaises(IntegrityError):
            StudentProfile.objects.create(**duplicate_data)

