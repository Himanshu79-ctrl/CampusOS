"""
Service layer for Assignment Management & Student Submissions in CampusOS LMS.
Encapsulates business rules for deadline enforcement, late submission policies,
resubmission limits, file validation, and grading.
"""

import os
from decimal import Decimal
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.academics.faculty_matcher import is_faculty_assigned
from apps.academics.models import CourseOffering, Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile
from .models import Assignment, AssignmentSubmission, SubmissionStatus

ALLOWED_SUBMISSION_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".txt",
    ".zip",
    ".tar.gz",
    ".png",
    ".jpg",
    ".jpeg",
    ".py",
    ".java",
    ".c",
    ".cpp",
    ".js",
    ".ts",
    ".html",
    ".css",
}
MAX_SUBMISSION_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


class AssignmentService:
    """
    Business service layer managing assignment publication, submission lifecycle,
    and grading evaluations.
    """

    @classmethod
    def check_user_assignment_access(cls, user, course_offering: CourseOffering) -> str:
        """
        Determines user access mode:
          - "MANAGE": Academic admin or assigned course offering faculty instructor.
          - "VIEW": Actively enrolled student.
        Raises PermissionDenied if unauthorized.
        """
        if getattr(user, "is_admin", False):
            return "MANAGE"

        if getattr(user, "is_faculty", False):
            if is_faculty_assigned(user, course_offering.faculty_id):
                return "MANAGE"
            raise PermissionDenied("You are not the assigned instructor for this course offering.")

        if getattr(user, "is_student", False):
            profile = StudentProfile.objects.filter(auth_user_id=str(user.user_id)).first()
            if not profile:
                raise PermissionDenied("No student academic profile found.")

            is_enrolled = Enrollment.objects.filter(
                student=profile,
                course_offering=course_offering,
                status=EnrollmentStatus.ENROLLED,
            ).exists()
            if is_enrolled:
                return "VIEW"
            raise PermissionDenied("You are not actively enrolled in this course offering.")

        raise PermissionDenied("Authentication required to access assignments.")

    @classmethod
    def get_assignments_queryset(cls, user, course_offering: CourseOffering):
        """
        Returns assignments queryset filtered by role privileges.
        Students see published assignments only.
        Instructors and Admins see both draft and published assignments.
        """
        access_mode = cls.check_user_assignment_access(user, course_offering)
        qs = Assignment.objects.filter(course_offering=course_offering)

        if access_mode == "VIEW":
            qs = qs.filter(is_published=True)

        return qs.order_by("due_date", "created_at")

    @classmethod
    def publish_assignment(cls, assignment: Assignment, is_published: bool) -> Assignment:
        """
        Toggles publish status of an assignment and triggers student notifications upon publication.
        """
        was_published = assignment.is_published
        assignment.is_published = is_published
        assignment.save(update_fields=["is_published", "updated_at"])
        if is_published and not was_published:
            try:
                from apps.notifications.services import trigger_assignment_published
                trigger_assignment_published(assignment)
            except Exception:
                pass
        return assignment

    @classmethod
    def validate_submission_file(cls, uploaded_file) -> tuple[int, str]:
        """
        Validates uploaded file size and extension.
        Returns (size_bytes, content_type).
        """
        if not uploaded_file:
            return 0, ""

        file_name = uploaded_file.name
        ext = os.path.splitext(file_name)[1].lower()
        if ext not in ALLOWED_SUBMISSION_EXTENSIONS:
            raise ValidationError(
                f"File type '{ext}' is not permitted for submissions. Allowed: {', '.join(sorted(ALLOWED_SUBMISSION_EXTENSIONS))}"
            )

        file_size = uploaded_file.size
        if file_size > MAX_SUBMISSION_FILE_SIZE:
            max_mb = MAX_SUBMISSION_FILE_SIZE // (1024 * 1024)
            raise ValidationError(f"File size exceeds maximum {max_mb}MB limit.")

        content_type = getattr(uploaded_file, "content_type", "application/octet-stream")
        return file_size, content_type

    @classmethod
    def submit_assignment(
        cls,
        user,
        assignment: Assignment,
        submission_text: str = "",
        submission_file=None,
    ) -> AssignmentSubmission:
        """
        Records or updates a student's submission.
        Enforces:
          - Active student enrollment.
          - Published assignment requirement.
          - Due date & late submission policies.
          - Resubmission limits and graded status locks.
          - Payload non-empty check (text or file).
        """
        if not getattr(user, "is_student", False):
            raise PermissionDenied("Only students can submit assignments.")

        profile = StudentProfile.objects.filter(auth_user_id=str(user.user_id)).first()
        if not profile:
            raise PermissionDenied("Student academic profile required.")

        # 1. Enforce active enrollment
        is_enrolled = Enrollment.objects.filter(
            student=profile,
            course_offering=assignment.course_offering,
            status=EnrollmentStatus.ENROLLED,
        ).exists()
        if not is_enrolled:
            raise PermissionDenied("You must be actively enrolled in this course offering to submit.")

        # 2. Enforce published assignment
        if not assignment.is_published:
            raise PermissionDenied("Cannot submit to an unpublished assignment.")

        # 3. Enforce payload content
        text_clean = (submission_text or "").strip()
        if not text_clean and not submission_file:
            raise ValidationError("A submission must include either text content or an uploaded file.")

        # 4. Enforce deadlines
        now = timezone.now()
        is_late = (now > assignment.due_date)

        if is_late:
            if not assignment.allow_late_submissions:
                raise ValidationError("The submission deadline for this assignment has passed and late submissions are not allowed.")
            if assignment.late_submission_deadline and now > assignment.late_submission_deadline:
                raise ValidationError("The final late submission cutoff deadline has passed.")

        # Validate file if present
        file_size, file_mime = 0, ""
        if submission_file:
            file_size, file_mime = cls.validate_submission_file(submission_file)

        # 5. Handle existing submission (Resubmission flow)
        with transaction.atomic():
            existing = AssignmentSubmission.objects.filter(assignment=assignment, student=profile).first()

            if existing:
                if not assignment.allow_resubmissions:
                    raise ValidationError("Resubmissions are not permitted for this assignment.")

                if existing.status == SubmissionStatus.GRADED:
                    raise ValidationError("Cannot resubmit after your submission has already been graded.")

                if existing.submission_number >= assignment.max_resubmissions:
                    raise ValidationError(
                        f"Maximum allowed submission attempts ({assignment.max_resubmissions}) reached."
                    )

                existing.submission_text = text_clean
                if submission_file:
                    existing.submission_file = submission_file
                    existing.file_size_bytes = file_size
                    existing.file_mime_type = file_mime
                existing.submission_number += 1
                existing.status = SubmissionStatus.RESUBMITTED
                existing.is_late = is_late
                existing.submitted_at = now
                existing.save()
                return existing

            # Initial submission
            submission = AssignmentSubmission(
                assignment=assignment,
                student=profile,
                submission_text=text_clean,
                submission_file=submission_file,
                file_size_bytes=file_size if submission_file else None,
                file_mime_type=file_mime if submission_file else "",
                submission_number=1,
                is_late=is_late,
                status=SubmissionStatus.SUBMITTED,
            )
            submission.save()
            return submission

    @classmethod
    def grade_submission(
        cls,
        evaluator_user,
        submission: AssignmentSubmission,
        marks_obtained: Decimal,
        feedback: str = "",
    ) -> AssignmentSubmission:
        """
        Evaluates and grades a student submission.
        Enforces maximum marks boundary and records evaluator audit information.
        """
        if marks_obtained is None:
            raise ValidationError({"marks_obtained": "Marks obtained is required."})

        marks_dec = Decimal(str(marks_obtained))
        if marks_dec < Decimal("0.00"):
            raise ValidationError({"marks_obtained": "Marks obtained cannot be negative."})

        if marks_dec > submission.assignment.max_marks:
            raise ValidationError(
                {"marks_obtained": f"Marks cannot exceed maximum marks ({submission.assignment.max_marks})."}
            )

        submission.marks_obtained = marks_dec
        submission.feedback = (feedback or "").strip()
        submission.status = SubmissionStatus.GRADED
        submission.graded_by_faculty_id = str(evaluator_user.user_id)
        submission.graded_at = timezone.now()
        submission.save(update_fields=["marks_obtained", "feedback", "status", "graded_by_faculty_id", "graded_at", "updated_at"])
        return submission

