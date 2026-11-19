"""
Comprehensive automated test suite for Grades & Academic Results (apps.grades).
Implements SRS Section 3.F:
  - Model validations and constraints on GradeItem, GradeRecord, and FinalCourseGrade.
  - GradeItem CRUD, permissions, and publishing.
  - Faculty marks entry, letter grades, and feedback.
  - Assignment submission marks synchronization.
  - Exam Engine integration boundary and mock ingestion.
  - Course-wise gradebook matrix for faculty and admin.
  - Final course results publication.
  - Student personal grades retrieval and strict IDOR protection.
"""

from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import (
    AcademicTerm,
    CourseOffering,
    Enrollment,
    EnrollmentStatus,
    OfferingStatus,
    TermStatus,
)
from apps.assignments.models import Assignment, AssignmentSubmission, SubmissionStatus
from apps.grades.models import FinalCourseGrade, GradeItem, GradeItemType, GradeRecord
from apps.students.models import StudentProfile
from config.authentication import ExternalJWTAuthentication


class GradeModelTests(TestCase):
    """
    Unit tests for model-level validation on GradeItem, GradeRecord, and FinalCourseGrade.
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
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )
        self.student = StudentProfile.objects.create(
            auth_user_id="stu_101",
            registration_number="REG2026_101",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=3,
        )
        self.non_enrolled_student = StudentProfile.objects.create(
            auth_user_id="stu_999",
            registration_number="REG2026_999",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=3,
        )
        Enrollment.objects.create(
            student=self.student,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )

    def test_grade_item_max_marks_must_be_positive(self):
        """Validates that GradeItem max_marks must be strictly greater than zero."""
        with self.assertRaises(ValidationError):
            GradeItem.objects.create(
                course_offering=self.offering,
                name="Zero Marks Item",
                max_marks=Decimal("0.00"),
            )

    def test_grade_record_unique_constraint(self):
        """Enforces that a student cannot have duplicate grade records for the same GradeItem."""
        item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Midterm Exam",
            max_marks=Decimal("100.00"),
        )
        GradeRecord.objects.create(
            grade_item=item,
            student=self.student,
            marks_obtained=Decimal("85.00"),
        )
        with self.assertRaises((ValidationError, IntegrityError)):
            GradeRecord.objects.create(
                grade_item=item,
                student=self.student,
                marks_obtained=Decimal("90.00"),
            )

    def test_grade_record_marks_cannot_exceed_max_marks(self):
        """Validates that awarded marks cannot exceed grade item max_marks."""
        item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Quiz 1",
            max_marks=Decimal("20.00"),
        )
        record = GradeRecord(
            grade_item=item,
            student=self.student,
            marks_obtained=Decimal("25.00"),  # Exceeds 20.00
        )
        with self.assertRaises(ValidationError):
            record.full_clean()

    def test_non_enrolled_student_cannot_have_grade_record(self):
        """Validates that a non-enrolled student raises ValidationError for GradeRecord."""
        item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Midterm Exam",
            max_marks=Decimal("100.00"),
        )
        record = GradeRecord(
            grade_item=item,
            student=self.non_enrolled_student,
            marks_obtained=Decimal("75.00"),
        )
        with self.assertRaises(ValidationError):
            record.full_clean()


class GradeAPITests(TestCase):
    """
    Integration tests for Grades & Academic Results REST API endpoints (SRS Section 3.F).
    """

    def setUp(self):
        self.client = APIClient()

        # Auth Tokens
        self.admin_token = ExternalJWTAuthentication.generate_token(user_id="adm_1", role="admin")
        self.instructor_token = ExternalJWTAuthentication.generate_token(user_id="fac_101", role="faculty")
        self.other_faculty_token = ExternalJWTAuthentication.generate_token(user_id="fac_999", role="faculty")
        self.student1_token = ExternalJWTAuthentication.generate_token(user_id="stu_1", role="student")
        self.student2_token = ExternalJWTAuthentication.generate_token(user_id="stu_2", role="student")
        self.non_enrolled_token = ExternalJWTAuthentication.generate_token(user_id="stu_99", role="student")

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
            capacity=30,
            status=OfferingStatus.PUBLISHED,
        )

        # Student Profiles
        self.student1 = StudentProfile.objects.create(
            auth_user_id="stu_1",
            registration_number="REG2026001",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=3,
        )
        self.student2 = StudentProfile.objects.create(
            auth_user_id="stu_2",
            registration_number="REG2026002",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=3,
        )
        self.non_enrolled_student = StudentProfile.objects.create(
            auth_user_id="stu_99",
            registration_number="REG2026099",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=3,
        )

        # Enrollments
        Enrollment.objects.create(
            student=self.student1,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )
        Enrollment.objects.create(
            student=self.student2,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )

    # -------------------------------------------------------------------------
    # 1. GradeItem Creation, Update, and Permissions
    # -------------------------------------------------------------------------

    def test_assigned_faculty_creates_grade_item(self):
        """Assigned faculty can create an assessment component (GradeItem)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "name": "Midterm Examination",
            "item_type": "MIDTERM",
            "max_marks": "100.00",
            "weightage_percentage": "30.00",
            "is_published": False,
        }
        res = self.client.post(f"/api/grades/offerings/{self.offering.id}/items/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "Midterm Examination")
        self.assertEqual(res.data["item_type"], "MIDTERM")
        self.assertEqual(res.data["is_published"], False)

    def test_unassigned_faculty_cannot_create_grade_item(self):
        """Faculty not assigned to the offering cannot create grade items (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        payload = {"name": "Unauthorized Component", "max_marks": "50.00"}
        res = self.client.post(f"/api/grades/offerings/{self.offering.id}/items/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_create_grade_item(self):
        """Student cannot create grade items (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"name": "Student Created Component", "max_marks": "50.00"}
        res = self.client.post(f"/api/grades/offerings/{self.offering.id}/items/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_grade_item(self):
        """Academic admin can create grade items for any course offering."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        payload = {"name": "Admin Final Exam", "max_marks": "100.00", "item_type": "FINAL"}
        res = self.client.post(f"/api/grades/offerings/{self.offering.id}/items/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_update_and_publish_grade_item(self):
        """Assigned faculty can update and publish a grade item."""
        item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Initial Name",
            max_marks=Decimal("50.00"),
            is_published=False,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")

        # Update name
        patch_res = self.client.patch(f"/api/grades/items/{item.id}/", {"name": "Updated Name"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["name"], "Updated Name")

        # Publish
        pub_res = self.client.post(f"/api/grades/items/{item.id}/publish/", {"is_published": True}, format="json")
        self.assertEqual(pub_res.status_code, status.HTTP_200_OK)
        self.assertEqual(pub_res.data["is_published"], True)

    # -------------------------------------------------------------------------
    # 2. Marks Entry & Grade Record Evaluation
    # -------------------------------------------------------------------------

    def test_assigned_faculty_bulk_enters_grades(self):
        """Assigned faculty can bulk enter student marks, letter grades, and feedback."""
        item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Project 1",
            max_marks=Decimal("100.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "records": [
                {
                    "student_id": self.student1.id,
                    "marks_obtained": "92.50",
                    "letter_grade": "A+",
                    "feedback": "Outstanding implementation and test coverage.",
                },
                {
                    "student_id": self.student2.id,
                    "marks_obtained": "81.00",
                    "letter_grade": "A-",
                    "feedback": "Good work, minor documentation issues.",
                },
            ]
        }
        res = self.client.post(f"/api/grades/items/{item.id}/marks/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

        # Verify Student 1 record
        rec1 = GradeRecord.objects.get(grade_item=item, student=self.student1)
        self.assertEqual(rec1.marks_obtained, Decimal("92.50"))
        self.assertEqual(rec1.letter_grade, "A+")
        self.assertEqual(rec1.graded_by_faculty_id, "fac_101")

    def test_marks_exceeding_max_marks_rejected(self):
        """Marks exceeding max_marks are rejected with 400 Bad Request."""
        item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Quiz 1",
            max_marks=Decimal("20.00"),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "records": [
                {"student_id": self.student1.id, "marks_obtained": "25.00"},  # Exceeds 20.00
            ]
        }
        res = self.client.post(f"/api/grades/items/{item.id}/marks/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_enrolled_student_marks_entry_rejected(self):
        """Attempting to enter marks for non-enrolled student is rejected with 400."""
        item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Quiz 1",
            max_marks=Decimal("20.00"),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "records": [
                {"student_id": self.non_enrolled_student.id, "marks_obtained": "15.00"},
            ]
        }
        res = self.client.post(f"/api/grades/items/{item.id}/marks/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not actively enrolled", str(res.data))

    # -------------------------------------------------------------------------
    # 3. Assignment Marks Synchronization
    # -------------------------------------------------------------------------

    def test_sync_assignment_marks_into_gradebook(self):
        """LMS Assignment graded submissions can be synchronized into GradeRecords."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Lab 1 Assignment",
            max_marks=Decimal("100.00"),
            due_date=timezone.now() + timedelta(days=5),
            is_published=True,
        )
        # Student 1 graded submission
        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            submission_text="Solution content",
            status=SubmissionStatus.GRADED,
            marks_obtained=Decimal("88.00"),
            feedback="Great work.",
            graded_by_faculty_id="fac_101",
        )
        # Student 2 graded submission
        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student2,
            submission_text="Solution 2",
            status=SubmissionStatus.GRADED,
            marks_obtained=Decimal("94.50"),
            feedback="Perfect.",
            graded_by_faculty_id="fac_101",
        )

        # GradeItem linked to assignment
        item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Lab 1 Grade",
            max_marks=Decimal("100.00"),
            assignment=assignment,
            is_published=True,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        res = self.client.post(f"/api/grades/items/{item.id}/sync-assignment/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["synced_count"], 2)

        # Check records
        rec1 = GradeRecord.objects.get(grade_item=item, student=self.student1)
        self.assertEqual(rec1.marks_obtained, Decimal("88.00"))
        self.assertEqual(rec1.feedback, "Great work.")

    # -------------------------------------------------------------------------
    # 4. Exam Engine Integration Boundary
    # -------------------------------------------------------------------------

    def test_exam_engine_sync_unconfigured_status(self):
        """When Exam Engine service is not configured, sync-exam reports pending integration status cleanly."""
        item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Midterm Online Exam",
            max_marks=Decimal("100.00"),
            external_exam_id="exam_abc_123",
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        res = self.client.post(f"/api/grades/items/{item.id}/sync-exam/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "PENDING_INTEGRATION")
        self.assertIn("EXAM_ENGINE_SERVICE_URL", res.data["message"])

    @patch("apps.grades.exam_client.ExamEngineClient.fetch_exam_results")
    def test_exam_engine_sync_ingests_scores(self, mock_fetch):
        """When Exam Engine returns results, scores are ingested for enrolled students."""
        mock_fetch.return_value = {
            "status": "SUCCESS",
            "results": [
                {"student_auth_id": "stu_1", "marks_obtained": "89.00"},
                {"student_auth_id": "stu_2", "marks_obtained": "76.50"},
            ],
        }
        item = GradeItem.objects.create(
            course_offering=self.offering,
            name="Online Quiz Exam",
            max_marks=Decimal("100.00"),
            external_exam_id="exam_quiz_1",
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        res = self.client.post(f"/api/grades/items/{item.id}/sync-exam/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "SUCCESS")
        self.assertEqual(res.data["synced_records_count"], 2)

        rec1 = GradeRecord.objects.get(grade_item=item, student=self.student1)
        self.assertEqual(rec1.marks_obtained, Decimal("89.00"))

    # -------------------------------------------------------------------------
    # 5. Course Gradebook View Matrix
    # -------------------------------------------------------------------------

    def test_faculty_views_course_gradebook_matrix(self):
        """Assigned faculty views the complete course gradebook matrix."""
        item1 = GradeItem.objects.create(course_offering=self.offering, name="HW 1", max_marks=Decimal("50.00"), is_published=True)
        item2 = GradeItem.objects.create(course_offering=self.offering, name="Exam 1", max_marks=Decimal("100.00"), is_published=True)

        GradeRecord.objects.create(grade_item=item1, student=self.student1, marks_obtained=Decimal("45.00"))
        GradeRecord.objects.create(grade_item=item2, student=self.student1, marks_obtained=Decimal("90.00"))

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        res = self.client.get(f"/api/grades/offerings/{self.offering.id}/gradebook/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["grade_items"]), 2)
        self.assertEqual(len(res.data["students"]), 2)

        stu1_data = next(s for s in res.data["students"] if s["student_id"] == self.student1.id)
        self.assertEqual(Decimal(stu1_data["total_marks_obtained"]), Decimal("135.00"))
        self.assertEqual(Decimal(stu1_data["total_max_marks"]), Decimal("150.00"))

    def test_student_cannot_view_course_gradebook(self):
        """Student cannot access the class-wide gradebook matrix (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get(f"/api/grades/offerings/{self.offering.id}/gradebook/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 6. Final Course Results Publication
    # -------------------------------------------------------------------------

    def test_faculty_publishes_final_course_grades(self):
        """Assigned faculty can publish overall course results."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "grades": [
                {
                    "student_id": self.student1.id,
                    "final_letter_grade": "A+",
                    "total_marks_obtained": "180.00",
                    "total_max_marks": "200.00",
                    "percentage": "90.00",
                    "feedback": "First class honours.",
                }
            ]
        }
        res = self.client.post(f"/api/grades/offerings/{self.offering.id}/final-results/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["final_letter_grade"], "A+")
        self.assertEqual(res.data[0]["is_published"], True)

    def test_student_cannot_publish_final_results(self):
        """Student cannot publish final course results (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"grades": [{"student_id": self.student1.id, "final_letter_grade": "A+"}]}
        res = self.client.post(f"/api/grades/offerings/{self.offering.id}/final-results/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 7. Student Personal Grades & IDOR Protection
    # -------------------------------------------------------------------------

    def test_student_views_own_published_grades(self):
        """Student can view their published grade records and published final grades."""
        item_pub = GradeItem.objects.create(course_offering=self.offering, name="Published Quiz", max_marks=Decimal("20.00"), is_published=True)
        item_draft = GradeItem.objects.create(course_offering=self.offering, name="Draft Quiz", max_marks=Decimal("20.00"), is_published=False)

        rec_pub = GradeRecord.objects.create(grade_item=item_pub, student=self.student1, marks_obtained=Decimal("18.00"), is_published=True)
        rec_draft = GradeRecord.objects.create(grade_item=item_draft, student=self.student1, marks_obtained=Decimal("19.00"), is_published=False)

        FinalCourseGrade.objects.create(
            course_offering=self.offering,
            student=self.student1,
            final_letter_grade="A",
            is_published=True,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get("/api/grades/my-grades/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Published record present, draft record excluded
        records = res.data["grade_records"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], rec_pub.id)
        self.assertEqual(records[0]["marks_obtained"], "18.00")

        # Final grade present
        final_grades = res.data["final_course_grades"]
        self.assertEqual(len(final_grades), 1)
        self.assertEqual(final_grades[0]["final_letter_grade"], "A")

    def test_student_cannot_view_other_student_grade_record_idor(self):
        """Student 2 cannot view Student 1's grade record (403 IDOR Protection)."""
        item = GradeItem.objects.create(course_offering=self.offering, name="HW", max_marks=Decimal("50.00"), is_published=True)
        rec1 = GradeRecord.objects.create(grade_item=item, student=self.student1, marks_obtained=Decimal("48.00"), is_published=True)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student2_token}")
        res = self.client.get(f"/api/grades/records/{rec1.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_view_own_grade_record(self):
        """Student 1 can view their own published grade record (200 OK)."""
        item = GradeItem.objects.create(course_offering=self.offering, name="HW", max_marks=Decimal("50.00"), is_published=True)
        rec1 = GradeRecord.objects.create(grade_item=item, student=self.student1, marks_obtained=Decimal("48.00"), is_published=True)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get(f"/api/grades/records/{rec1.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["marks_obtained"], "48.00")
