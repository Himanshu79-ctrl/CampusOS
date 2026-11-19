"""
Comprehensive automated test suite for Assignment Management & Submissions (apps.assignments).
Implements SRS Section 3.C:
  - Model validations (max_marks, deadlines, submission constraints).
  - Faculty assignment CRUD & publishing permissions.
  - Student visibility restrictions (draft vs published, enrolled vs non-enrolled).
  - Student submissions (text, file attachments, extension/size checks).
  - Deadline and late submission policy enforcement.
  - Resubmission flow and limit enforcement.
  - Student personal view and IDOR protection.
  - Faculty grading, audit tracking, and marks validation.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
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
from apps.assignments.services import AssignmentService
from apps.learning.models import CourseModule
from apps.students.models import StudentProfile
from config.authentication import ExternalJWTAuthentication


class AssignmentModelTests(TestCase):
    """
    Unit tests for model-level validations and constraints on Assignment and AssignmentSubmission.
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
            registration_number="REG2026_001",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=5,
        )

    def test_assignment_max_marks_must_be_positive(self):
        """Validates that assignment max_marks must be strictly greater than 0."""
        with self.assertRaises(ValidationError):
            Assignment.objects.create(
                course_offering=self.offering,
                title="Zero Marks Assignment",
                max_marks=Decimal("0.00"),
                due_date=timezone.now() + timedelta(days=7),
            )

    def test_late_deadline_must_be_after_due_date(self):
        """Validates that late_submission_deadline cannot precede or equal due_date."""
        now = timezone.now()
        with self.assertRaises(ValidationError):
            Assignment.objects.create(
                course_offering=self.offering,
                title="Invalid Late Deadline",
                max_marks=Decimal("100.00"),
                due_date=now + timedelta(days=7),
                allow_late_submissions=True,
                late_submission_deadline=now + timedelta(days=5),  # Before due_date
            )

    def test_submission_must_have_text_or_file(self):
        """Validates that a submission without text or file raises ValidationError."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Homework 1",
            max_marks=Decimal("50.00"),
            due_date=timezone.now() + timedelta(days=5),
            is_published=True,
        )
        with self.assertRaises(ValidationError):
            AssignmentSubmission.objects.create(
                assignment=assignment,
                student=self.student,
                submission_text="",
                submission_file=None,
            )

    def test_unique_student_assignment_submission_constraint(self):
        """Enforces unique submission constraint on (assignment, student)."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Homework 1",
            max_marks=Decimal("50.00"),
            due_date=timezone.now() + timedelta(days=5),
            is_published=True,
        )
        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            submission_text="Initial submission",
        )
        with self.assertRaises((ValidationError, IntegrityError)):
            AssignmentSubmission.objects.create(
                assignment=assignment,
                student=self.student,
                submission_text="Duplicate submission record",
            )

    def test_marks_obtained_cannot_exceed_max_marks(self):
        """Validates that awarded marks cannot exceed the assignment max_marks."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Homework 1",
            max_marks=Decimal("50.00"),
            due_date=timezone.now() + timedelta(days=5),
            is_published=True,
        )
        sub = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            submission_text="Solution content",
        )
        sub.marks_obtained = Decimal("55.00")  # Exceeds 50.00
        with self.assertRaises(ValidationError):
            sub.full_clean()


class AssignmentAPITests(TestCase):
    """
    Integration tests for Assignment Management & Submission REST API endpoints.
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
        self.module = CourseModule.objects.create(
            course_offering=self.offering,
            title="Module 1: Foundations",
            order=1,
            is_published=True,
        )

        # Student Profiles
        self.student1 = StudentProfile.objects.create(
            auth_user_id="stu_1",
            registration_number="REG2026001",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=5,
        )
        self.student2 = StudentProfile.objects.create(
            auth_user_id="stu_2",
            registration_number="REG2026002",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=5,
        )
        self.non_enrolled_student = StudentProfile.objects.create(
            auth_user_id="stu_99",
            registration_number="REG2026099",
            department_id="607f1f77bcf86cd799439033",
            admission_year=2026,
            current_semester=5,
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
    # 1. Assignment Creation & Management (Faculty / Admin)
    # -------------------------------------------------------------------------

    def test_assigned_faculty_creates_assignment(self):
        """Assigned faculty can successfully create an assignment."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        due = (timezone.now() + timedelta(days=7)).isoformat()
        payload = {
            "title": "Lab 1: Algorithm Analysis",
            "description": "Analyze asymptotic complexity of sort algorithms.",
            "instructions": "Submit PDF report with graph plots.",
            "max_marks": "100.00",
            "due_date": due,
            "module": self.module.id,
            "allow_late_submissions": False,
            "allow_resubmissions": True,
            "max_resubmissions": 2,
            "is_published": False,
        }
        res = self.client.post(f"/api/assignments/offerings/{self.offering.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Lab 1: Algorithm Analysis")
        self.assertEqual(res.data["is_published"], False)

    def test_unassigned_faculty_cannot_create_assignment(self):
        """Faculty not assigned to the offering cannot create assignments (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        due = (timezone.now() + timedelta(days=7)).isoformat()
        payload = {"title": "Unauthorized Assignment", "due_date": due, "max_marks": "100.00"}
        res = self.client.post(f"/api/assignments/offerings/{self.offering.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_create_assignment(self):
        """Student cannot create an assignment (403)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        due = (timezone.now() + timedelta(days=7)).isoformat()
        payload = {"title": "Student Created Assignment", "due_date": due, "max_marks": "100.00"}
        res = self.client.post(f"/api/assignments/offerings/{self.offering.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_assignment(self):
        """Administrator can create an assignment for any course offering."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        due = (timezone.now() + timedelta(days=7)).isoformat()
        payload = {"title": "Admin Created Assignment", "due_date": due, "max_marks": "50.00"}
        res = self.client.post(f"/api/assignments/offerings/{self.offering.id}/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_update_and_publish_assignment(self):
        """Assigned faculty can update details and toggle published status."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Initial Title",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("50.00"),
            is_published=False,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")

        # Update assignment title
        patch_res = self.client.patch(f"/api/assignments/{assignment.id}/", {"title": "Updated Title"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["title"], "Updated Title")

        # Publish assignment
        pub_res = self.client.post(f"/api/assignments/{assignment.id}/publish/", {"is_published": True}, format="json")
        self.assertEqual(pub_res.status_code, status.HTTP_200_OK)
        self.assertEqual(pub_res.data["is_published"], True)

    def test_delete_assignment(self):
        """Assigned faculty can delete an assignment."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="To Delete",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("50.00"),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        del_res = self.client.delete(f"/api/assignments/{assignment.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        self.assertFalse(Assignment.objects.filter(id=assignment.id).exists())

    # -------------------------------------------------------------------------
    # 2. Assignment Visibility & Student Enrollment Enforcement
    # -------------------------------------------------------------------------

    def test_student_sees_only_published_assignments(self):
        """Enrolled students only see published assignments in offering list."""
        Assignment.objects.create(
            course_offering=self.offering,
            title="Published HW",
            due_date=timezone.now() + timedelta(days=5),
            max_marks=Decimal("100.00"),
            is_published=True,
        )
        Assignment.objects.create(
            course_offering=self.offering,
            title="Draft HW",
            due_date=timezone.now() + timedelta(days=10),
            max_marks=Decimal("100.00"),
            is_published=False,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get(f"/api/assignments/offerings/{self.offering.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Published HW")

    def test_faculty_sees_both_draft_and_published_assignments(self):
        """Assigned faculty sees all assignments (draft and published) with stats."""
        Assignment.objects.create(
            course_offering=self.offering,
            title="Published HW",
            due_date=timezone.now() + timedelta(days=5),
            max_marks=Decimal("100.00"),
            is_published=True,
        )
        Assignment.objects.create(
            course_offering=self.offering,
            title="Draft HW",
            due_date=timezone.now() + timedelta(days=10),
            max_marks=Decimal("100.00"),
            is_published=False,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        res = self.client.get(f"/api/assignments/offerings/{self.offering.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_non_enrolled_student_access_denied(self):
        """Non-enrolled student cannot access assignments list or detail (403)."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Published HW",
            due_date=timezone.now() + timedelta(days=5),
            max_marks=Decimal("100.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.non_enrolled_token}")
        res_list = self.client.get(f"/api/assignments/offerings/{self.offering.id}/")
        self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

        res_detail = self.client.get(f"/api/assignments/{assignment.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_view_draft_assignment_detail(self):
        """Enrolled student cannot view detail of an unpublished draft assignment (403)."""
        draft_assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Draft HW",
            due_date=timezone.now() + timedelta(days=5),
            max_marks=Decimal("100.00"),
            is_published=False,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get(f"/api/assignments/{draft_assignment.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 3. Student Submissions & Validation
    # -------------------------------------------------------------------------

    def test_student_submits_text_successfully(self):
        """Enrolled student submits text solution to published assignment."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Essay Assignment",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"submission_text": "https://github.com/student/assignment1"}
        res = self.client.post(f"/api/assignments/{assignment.id}/submit/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["status"], SubmissionStatus.SUBMITTED)
        self.assertEqual(res.data["is_late"], False)
        self.assertEqual(res.data["submission_number"], 1)

    def test_student_submits_file_successfully(self):
        """Enrolled student uploads a permitted file (.pdf) for submission."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Report Submission",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("100.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        fake_pdf = SimpleUploadedFile("report.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
        payload = {"submission_file": fake_pdf, "submission_text": "Final lab report attached."}
        res = self.client.post(f"/api/assignments/{assignment.id}/submit/", payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["submission_file"] is not None)
        self.assertEqual(res.data["status"], SubmissionStatus.SUBMITTED)

    def test_submission_rejects_empty_content(self):
        """Submission with neither text nor file is rejected (400)."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Mandatory Content",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"submission_text": "   "}
        res = self.client.post(f"/api/assignments/{assignment.id}/submit/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disallowed_file_extension_rejected(self):
        """Submission with disallowed file type (e.g. .exe) is rejected with 400."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Secure Upload Assignment",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        bad_file = SimpleUploadedFile("malware.exe", b"binarycontent", content_type="application/octet-stream")
        payload = {"submission_file": bad_file}
        res = self.client.post(f"/api/assignments/{assignment.id}/submit/", payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submission_to_unpublished_assignment_rejected(self):
        """Student cannot submit to an unpublished (draft) assignment (403)."""
        draft_assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Draft HW",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("50.00"),
            is_published=False,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"submission_text": "Early attempt"}
        res = self.client.post(f"/api/assignments/{draft_assignment.id}/submit/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 4. Deadline & Late Submission Policy Enforcement
    # -------------------------------------------------------------------------

    def test_past_due_date_rejected_when_late_submissions_disallowed(self):
        """Past due submission rejected when allow_late_submissions is False (400)."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Strict Deadline HW",
            due_date=timezone.now() - timedelta(hours=2),  # Already passed
            allow_late_submissions=False,
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"submission_text": "Late solution"}
        res = self.client.post(f"/api/assignments/{assignment.id}/submit/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline for this assignment has passed", str(res.data))

    def test_late_submission_accepted_when_allowed_within_late_deadline(self):
        """Late submission accepted and flagged as is_late=True when allowed."""
        now = timezone.now()
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Flexible Late HW",
            due_date=now - timedelta(hours=2),
            allow_late_submissions=True,
            late_submission_deadline=now + timedelta(days=2),
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"submission_text": "Late submission with penalty"}
        res = self.client.post(f"/api/assignments/{assignment.id}/submit/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["is_late"])

    def test_submission_rejected_after_late_deadline_cutoff(self):
        """Submission rejected when past the hard late_submission_deadline (400)."""
        now = timezone.now()
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Hard Cutoff HW",
            due_date=now - timedelta(days=3),
            allow_late_submissions=True,
            late_submission_deadline=now - timedelta(hours=1),  # Cutoff passed
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        payload = {"submission_text": "Super late submission"}
        res = self.client.post(f"/api/assignments/{assignment.id}/submit/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("late submission cutoff deadline has passed", str(res.data))

    # -------------------------------------------------------------------------
    # 5. Resubmission Flow & Limits
    # -------------------------------------------------------------------------

    def test_resubmission_rejected_when_not_allowed(self):
        """Resubmission attempt rejected when allow_resubmissions is False (400)."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Single Attempt HW",
            due_date=timezone.now() + timedelta(days=3),
            allow_resubmissions=False,
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        # Attempt 1
        res1 = self.client.post(f"/api/assignments/{assignment.id}/submit/", {"submission_text": "Attempt 1"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Attempt 2
        res2 = self.client.post(f"/api/assignments/{assignment.id}/submit/", {"submission_text": "Attempt 2"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Resubmissions are not permitted", str(res2.data))

    def test_resubmission_allowed_up_to_max_limit(self):
        """Resubmission permitted up to max_resubmissions limit."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Multi Attempt HW",
            due_date=timezone.now() + timedelta(days=3),
            allow_resubmissions=True,
            max_resubmissions=2,
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")

        # Attempt 1
        res1 = self.client.post(f"/api/assignments/{assignment.id}/submit/", {"submission_text": "First Draft"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res1.data["submission_number"], 1)

        # Attempt 2 (Permitted resubmission)
        res2 = self.client.post(f"/api/assignments/{assignment.id}/submit/", {"submission_text": "Second Draft"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.data["submission_number"], 2)
        self.assertEqual(res2.data["status"], SubmissionStatus.RESUBMITTED)

        # Attempt 3 (Exceeds max limit 2 -> 400)
        res3 = self.client.post(f"/api/assignments/{assignment.id}/submit/", {"submission_text": "Third Draft"}, format="json")
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Maximum allowed submission attempts", str(res3.data))

    def test_resubmission_blocked_after_graded(self):
        """Resubmission blocked once submission has been evaluated/graded."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Gradable HW",
            due_date=timezone.now() + timedelta(days=3),
            allow_resubmissions=True,
            max_resubmissions=3,
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        # Student submits
        sub = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            submission_text="Initial submission",
            status=SubmissionStatus.GRADED,  # Graded by faculty
            marks_obtained=Decimal("45.00"),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.post(f"/api/assignments/{assignment.id}/submit/", {"submission_text": "Resubmit after grade"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been graded", str(res.data))

    # -------------------------------------------------------------------------
    # 6. Student Personal View & IDOR Protection
    # -------------------------------------------------------------------------

    def test_student_views_personal_submission(self):
        """Enrolled student views their own submission record via my-submission endpoint."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Personal HW",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        sub = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            submission_text="Student 1 personal submission",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get(f"/api/assignments/{assignment.id}/my-submission/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], sub.id)
        self.assertEqual(res.data["submission_text"], "Student 1 personal submission")

    def test_idor_protection_student_cannot_access_other_student_submission(self):
        """Student 2 cannot access Student 1's submission via submission detail endpoint (403)."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Confidential HW",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        sub1 = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            submission_text="Student 1 private work",
        )
        # Student 2 tries to access sub1
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student2_token}")
        res = self.client.get(f"/api/assignments/submissions/{sub1.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 7. Faculty Evaluation & Grading
    # -------------------------------------------------------------------------

    def test_instructor_lists_class_submissions(self):
        """Assigned faculty lists all student submissions for an assignment."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Class HW",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("100.00"),
            is_published=True,
        )
        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            submission_text="Student 1 answer",
        )
        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student2,
            submission_text="Student 2 answer",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        res = self.client.get(f"/api/assignments/{assignment.id}/submissions/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_student_cannot_list_class_submissions(self):
        """Student cannot list class submissions (403)."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Class HW",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("100.00"),
            is_published=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        res = self.client.get(f"/api/assignments/{assignment.id}/submissions/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_instructor_grades_submission_successfully(self):
        """Assigned faculty grades a submission with marks and feedback."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Grading Test HW",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("100.00"),
            is_published=True,
        )
        sub = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            submission_text="My full solution",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {
            "marks_obtained": "88.50",
            "feedback": "Excellent work. Clear proofs and optimal complexity.",
        }
        res = self.client.post(f"/api/assignments/submissions/{sub.id}/grade/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], SubmissionStatus.GRADED)
        self.assertEqual(Decimal(str(res.data["marks_obtained"])), Decimal("88.50"))
        self.assertEqual(res.data["feedback"], "Excellent work. Clear proofs and optimal complexity.")
        self.assertEqual(res.data["graded_by_faculty_id"], "fac_101")
        self.assertTrue(res.data["graded_at"] is not None)

        # Student now views their graded submission
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.student1_token}")
        stu_res = self.client.get(f"/api/assignments/{assignment.id}/my-submission/")
        self.assertEqual(stu_res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(stu_res.data["marks_obtained"])), Decimal("88.50"))
        self.assertEqual(stu_res.data["status"], SubmissionStatus.GRADED)

    def test_grading_rejects_marks_exceeding_max_marks(self):
        """Grading rejected if marks_obtained exceeds assignment max_marks (400)."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Exceed Marks Test",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        sub = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            submission_text="Solution",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.instructor_token}")
        payload = {"marks_obtained": "55.00", "feedback": "Too generous"}
        res = self.client.post(f"/api/assignments/submissions/{sub.id}/grade/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot exceed maximum marks", str(res.data))

    def test_unassigned_faculty_cannot_grade_submission(self):
        """Faculty not assigned to the offering cannot grade student submissions (403)."""
        assignment = Assignment.objects.create(
            course_offering=self.offering,
            title="Foreign HW",
            due_date=timezone.now() + timedelta(days=3),
            max_marks=Decimal("50.00"),
            is_published=True,
        )
        sub = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student1,
            submission_text="Solution",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_faculty_token}")
        payload = {"marks_obtained": "40.00"}
        res = self.client.post(f"/api/assignments/submissions/{sub.id}/grade/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
