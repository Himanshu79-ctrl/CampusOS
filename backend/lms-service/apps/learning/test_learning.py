"""
Comprehensive automated test suite for Learning Management & Course Content (apps.learning).
Verifies:
  - CourseModule CRUD and unique ordering per offering.
  - Lesson CRUD and text-based learning content.
  - Draft vs Published visibility enforcement (students only see published).
  - Enrolled student access vs non-enrolled student restriction.
  - Faculty instructor ownership enforcement (only assigned instructor can modify).
  - Academic administrator management permissions.
  - LearningResource file uploads and external link validation.
  - Permitted file extension and size checks.
  - Student lesson completion progress tracking.
"""

from datetime import date
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import AcademicTerm, CourseOffering, Enrollment, EnrollmentStatus, OfferingStatus, TermStatus
from apps.students.models import StudentProfile
from apps.learning.models import CourseModule, Lesson, LearningResource, LessonProgress, ResourceType
from config.authentication import ExternalJWTAuthentication


class LearningModuleModelTests(TestCase):
    """
    Unit tests for model-level constraints and validation in apps.learning.
    """

    def setUp(self):
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
            course_id="607f1f77bcf86cd799439011",
            faculty_id="fac_101",
            department_id="607f1f77bcf86cd799439033",
            academic_term=self.term,
            section="A",
            capacity=40,
            status=OfferingStatus.PUBLISHED,
        )

    def test_unique_module_order_per_offering(self):
        """Enforces unique module order within the same CourseOffering."""
        CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1)
        with self.assertRaises(IntegrityError):
            CourseModule.objects.create(course_offering=self.offering, title="Duplicate Order", order=1)

    def test_unique_lesson_order_per_module(self):
        """Enforces unique lesson order within the same CourseModule."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1)
        Lesson.objects.create(module=module, title="Lesson 1", order=1)
        with self.assertRaises(IntegrityError):
            Lesson.objects.create(module=module, title="Duplicate Lesson Order", order=1)

    def test_learning_resource_validation(self):
        """Validates that a resource must have either a file (for FILE) or URL (for LINK)."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1)

        # File type without file raises error
        with self.assertRaises(Exception):
            res = LearningResource(module=module, title="No File", resource_type=ResourceType.FILE)
            res.save()

        # Link type without URL raises error
        with self.assertRaises(Exception):
            res = LearningResource(module=module, title="No Link", resource_type=ResourceType.LINK)
            res.save()


class LearningAPITests(TestCase):
    """
    Integration tests for Learning Content REST API endpoints and RBAC.
    """

    def setUp(self):
        self.client = APIClient()

        # Tokens
        self.admin_token = ExternalJWTAuthentication.generate_token(user_id="adm_1", role="admin")
        self.instructor_token = ExternalJWTAuthentication.generate_token(user_id="fac_101", role="faculty")
        self.other_faculty_token = ExternalJWTAuthentication.generate_token(user_id="fac_999", role="faculty")
        self.enrolled_student_token = ExternalJWTAuthentication.generate_token(user_id="stu_1", role="student")
        self.non_enrolled_student_token = ExternalJWTAuthentication.generate_token(user_id="stu_2", role="student")

        # Academic Setup
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
            course_id="607f1f77bcf86cd799439011",
            faculty_id="fac_101",
            department_id="607f1f77bcf86cd799439033",
            academic_term=self.term,
            section="A",
            capacity=40,
            status=OfferingStatus.PUBLISHED,
        )

        # Students Setup
        self.enrolled_student = StudentProfile.objects.create(
            auth_user_id="stu_1",
            registration_number="REG-STU-001",
            department_id="DEP_CSE",
            admission_year=2026,
            current_semester=1,
        )
        self.non_enrolled_student = StudentProfile.objects.create(
            auth_user_id="stu_2",
            registration_number="REG-STU-002",
            department_id="DEP_CSE",
            admission_year=2026,
            current_semester=1,
        )

        # Active Enrollment for Student 1
        self.enrollment = Enrollment.objects.create(
            student=self.enrolled_student,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )

    # -------------------------------------------------------------------------
    # Course Module Tests
    # -------------------------------------------------------------------------

    def test_instructor_create_module(self):
        """Assigned instructor can create a course module."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        url = f"/api/learning/offerings/{self.offering.id}/modules/"
        payload = {
            "title": "Module 1: Introduction to Algorithms",
            "description": "Foundational algorithmic complexity and Big-O notation.",
            "order": 1,
            "is_published": False,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], payload["title"])
        self.assertFalse(response.data["is_published"])

    def test_admin_create_module(self):
        """Academic admin can create a module in any offering."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        url = f"/api/learning/offerings/{self.offering.id}/modules/"
        payload = {"title": "Admin Created Module", "order": 1}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_other_faculty_cannot_create_module(self):
        """Faculty not assigned to the offering cannot create modules."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        url = f"/api/learning/offerings/{self.offering.id}/modules/"
        response = self.client.post(url, {"title": "Unauthorized Module"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_create_module(self):
        """Students cannot create course modules."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.enrolled_student_token}")
        url = f"/api/learning/offerings/{self.offering.id}/modules/"
        response = self.client.post(url, {"title": "Student Module"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_module_update_and_delete(self):
        """Instructor can update and delete their course module."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Initial Title", order=1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")

        # Update
        update_url = f"/api/learning/modules/{module.id}/"
        patch_resp = self.client.patch(update_url, {"title": "Updated Title"}, format="json")
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.data["title"], "Updated Title")

        # Delete
        del_resp = self.client.delete(update_url)
        self.assertEqual(del_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(CourseModule.objects.filter(id=module.id).exists())

    def test_module_publish_toggle_and_cascade(self):
        """Instructor can publish/unpublish a module, optionally cascading to lessons."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1, is_published=False)
        lesson1 = Lesson.objects.create(module=module, title="Lesson 1", order=1, is_published=False)
        lesson2 = Lesson.objects.create(module=module, title="Lesson 2", order=2, is_published=False)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        publish_url = f"/api/learning/modules/{module.id}/publish/"

        # Publish module with cascade
        resp = self.client.post(publish_url, {"is_published": True, "cascade_lessons": True}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_published"])

        lesson1.refresh_from_db()
        lesson2.refresh_from_db()
        self.assertTrue(lesson1.is_published)
        self.assertTrue(lesson2.is_published)

    # -------------------------------------------------------------------------
    # Lesson Tests
    # -------------------------------------------------------------------------

    def test_instructor_create_lesson(self):
        """Instructor creates a lesson with text learning content."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")

        url = f"/api/learning/modules/{module.id}/lessons/"
        payload = {
            "title": "Topic 1: Asymptotic Analysis",
            "description": "Understanding worst-case and average-case complexity.",
            "content": "# Asymptotic Analysis\n\nBig-O notation formally describes an upper bound.",
            "order": 1,
            "estimated_duration_minutes": 45,
            "is_published": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], payload["title"])
        self.assertEqual(response.data["content"], payload["content"])

    def test_lesson_publish_toggle(self):
        """Instructor toggles lesson draft vs published status."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1)
        lesson = Lesson.objects.create(module=module, title="Lesson 1", order=1, is_published=False)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        url = f"/api/learning/lessons/{lesson.id}/publish/"
        resp = self.client.post(url, {"is_published": True}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_published"])

    # -------------------------------------------------------------------------
    # Student Visibility & Access Control Tests
    # -------------------------------------------------------------------------

    def test_enrolled_student_sees_only_published_content(self):
        """
        Enrolled students can only see published modules and published lessons.
        Draft content is filtered out.
        """
        pub_module = CourseModule.objects.create(course_offering=self.offering, title="Published Module", order=1, is_published=True)
        draft_module = CourseModule.objects.create(course_offering=self.offering, title="Draft Module", order=2, is_published=False)

        pub_lesson = Lesson.objects.create(module=pub_module, title="Published Lesson", order=1, is_published=True)
        draft_lesson = Lesson.objects.create(module=pub_module, title="Draft Lesson", order=2, is_published=False)

        # 1. Enrolled Student Views Offering Modules
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.enrolled_student_token}")
        url = f"/api/learning/offerings/{self.offering.id}/modules/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see 1 module (published)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], pub_module.id)
        # Inside published module, should only see 1 lesson (published)
        self.assertEqual(len(response.data[0]["lessons"]), 1)
        self.assertEqual(response.data[0]["lessons"][0]["id"], pub_lesson.id)

        # 2. Student attempts to access draft lesson detail directly -> 403 Forbidden
        draft_lesson_url = f"/api/learning/lessons/{draft_lesson.id}//"
        draft_resp = self.client.get(f"/api/learning/lessons/{draft_lesson.id}/")
        self.assertEqual(draft_resp.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Instructor sees BOTH published and draft modules/lessons
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        inst_resp = self.client.get(url)
        self.assertEqual(len(inst_resp.data), 2)
        # Inside pub_module, instructor sees both lessons
        pub_mod_data = next(m for m in inst_resp.data if m["id"] == pub_module.id)
        self.assertEqual(len(pub_mod_data["lessons"]), 2)

    def test_non_enrolled_student_blocked_from_course_content(self):
        """A student not enrolled in the course offering is denied access."""
        CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1, is_published=True)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.non_enrolled_student_token}")

        url = f"/api/learning/offerings/{self.offering.id}/modules/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # Learning Resources (Files & External Links)
    # -------------------------------------------------------------------------

    def test_upload_permitted_file_resource(self):
        """Instructor uploads a valid PDF resource attached to a lesson."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1)
        lesson = Lesson.objects.create(module=module, title="Lesson 1", order=1)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        url = f"/api/learning/lessons/{lesson.id}/resources/"

        fake_pdf = SimpleUploadedFile("lecture_slides.pdf", b"%PDF-1.4 Fake PDF Content", content_type="application/pdf")
        payload = {
            "title": "Lecture 1 Slides (PDF)",
            "description": "Slides covering asymptotic analysis.",
            "resource_type": "FILE",
            "file": fake_pdf,
            "order": 1,
        }
        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["resource_type"], "FILE")
        self.assertIn("lecture_slides", response.data["file"])
        self.assertGreater(response.data["file_size_bytes"], 0)

    def test_upload_forbidden_file_extension_rejected(self):
        """Uploading a disallowed executable file extension (e.g., .exe) is rejected."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1)
        lesson = Lesson.objects.create(module=module, title="Lesson 1", order=1)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        url = f"/api/learning/lessons/{lesson.id}/resources/"

        fake_exe = SimpleUploadedFile("malicious.exe", b"MZ...", content_type="application/octet-stream")
        payload = {"title": "Malicious File", "resource_type": "FILE", "file": fake_exe}
        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not permitted", str(response.data))

    def test_create_external_link_resource(self):
        """Instructor attaches an external web resource link."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1)
        lesson = Lesson.objects.create(module=module, title="Lesson 1", order=1)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        url = f"/api/learning/lessons/{lesson.id}/resources/"

        payload = {
            "title": "MIT OpenCourseWare Algorithms Video",
            "description": "Supplementary video lecture.",
            "resource_type": "LINK",
            "external_url": "https://ocw.mit.edu/courses/electrical-engineering-and-computer-science/algorithms",
            "order": 1,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["resource_type"], "LINK")
        self.assertEqual(response.data["external_url"], payload["external_url"])

    # -------------------------------------------------------------------------
    # Student Lesson Progress Tracking
    # -------------------------------------------------------------------------

    def test_student_marks_lesson_completed(self):
        """Enrolled student marks a published lesson as completed."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1, is_published=True)
        lesson = Lesson.objects.create(module=module, title="Lesson 1", order=1, is_published=True)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.enrolled_student_token}")
        progress_url = f"/api/learning/lessons/{lesson.id}/progress/"

        # 1. Mark completed
        response = self.client.post(progress_url, {"is_completed": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_completed"])
        self.assertIsNotNone(response.data["completed_at"])

        # 2. Check lesson detail reflects completion status for this student
        detail_resp = self.client.get(f"/api/learning/lessons/{lesson.id}/")
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(detail_resp.data["is_completed"])

        # 3. Mark incomplete
        toggle_resp = self.client.post(progress_url, {"is_completed": False}, format="json")
        self.assertEqual(toggle_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(toggle_resp.data["is_completed"])

    def test_student_cannot_mark_progress_on_unpublished_lesson(self):
        """Students cannot record progress on draft lessons."""
        module = CourseModule.objects.create(course_offering=self.offering, title="Module 1", order=1, is_published=False)
        lesson = Lesson.objects.create(module=module, title="Lesson 1", order=1, is_published=False)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.enrolled_student_token}")
        progress_url = f"/api/learning/lessons/{lesson.id}/progress/"
        response = self.client.post(progress_url, {"is_completed": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

