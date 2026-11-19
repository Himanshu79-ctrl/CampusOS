"""
Models for Assignment Management & Student Submissions in CampusOS LMS.
Implements Assignments, Deadlines, Evaluation settings, and Submissions (SRS Section 3.C).
"""

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class SubmissionStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    GRADED = "GRADED", "Graded"
    RESUBMITTED = "RESUBMITTED", "Resubmitted"


class Assignment(models.Model):
    """
    Represents an academic coursework, homework, or project assigned to a CourseOffering.
    """

    course_offering = models.ForeignKey(
        "academics.CourseOffering",
        on_delete=models.CASCADE,
        related_name="assignments",
        help_text="CourseOffering to which this assignment belongs.",
    )
    module = models.ForeignKey(
        "learning.CourseModule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
        help_text="Optional learning module organizing this assignment.",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title of the assignment.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Overview or summary of the assignment task.",
    )
    instructions = models.TextField(
        blank=True,
        default="",
        help_text="Detailed formatting guidelines, problem statement, or evaluation rubric.",
    )
    max_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("100.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Maximum marks achievable for this assignment.",
    )
    due_date = models.DateTimeField(
        help_text="Official submission deadline.",
    )
    allow_late_submissions = models.BooleanField(
        default=False,
        help_text="Configurable flag permitting submissions after the due date.",
    )
    late_submission_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Hard cutoff deadline when late submissions are allowed.",
    )
    allow_resubmissions = models.BooleanField(
        default=False,
        help_text="Configurable flag permitting students to update/resubmit before grading.",
    )
    max_resubmissions = models.PositiveSmallIntegerField(
        default=1,
        help_text="Maximum total submission attempts allowed per student.",
    )
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Draft (False) vs Published (True) visibility for students.",
    )
    attachment = models.FileField(
        upload_to="assignment_briefs/%Y/%m/",
        blank=True,
        null=True,
        help_text="Optional brief document, starter template, or problem sheet.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_assignments"
        ordering = ["due_date", "created_at"]
        verbose_name = "Assignment"
        verbose_name_plural = "Assignments"

    def clean(self):
        super().clean()
        if self.max_marks is not None and self.max_marks <= Decimal("0.00"):
            raise ValidationError({"max_marks": "Maximum marks must be greater than zero."})

        if self.allow_late_submissions and self.late_submission_deadline and self.due_date:
            if self.late_submission_deadline <= self.due_date:
                raise ValidationError(
                    {"late_submission_deadline": "Late submission deadline must be strictly after the due date."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.title} (Offering #{self.course_offering_id})"


class AssignmentSubmission(models.Model):
    """
    Represents a student's submission (text and/or file) for an assignment,
    along with faculty evaluation marks and feedback.
    """

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
        help_text="Target assignment.",
    )
    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
        help_text="Enrolled student submitting the assignment.",
    )
    submission_text = models.TextField(
        blank=True,
        default="",
        help_text="Text-based answer, notes, or repository URL.",
    )
    submission_file = models.FileField(
        upload_to="assignment_submissions/%Y/%m/",
        blank=True,
        null=True,
        help_text="Uploaded submission document, source code, or archive.",
    )
    file_size_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Size of the uploaded file in bytes.",
    )
    file_mime_type = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Detected MIME type of the uploaded file.",
    )
    submission_number = models.PositiveSmallIntegerField(
        default=1,
        help_text="Submission attempt counter (e.g. 1 for initial, 2 for resubmission).",
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the submission was recorded.",
    )
    is_late = models.BooleanField(
        default=False,
        help_text="Designates whether this submission was received past the due date.",
    )
    status = models.CharField(
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.SUBMITTED,
        help_text="Current evaluation status: SUBMITTED, RESUBMITTED, or GRADED.",
    )
    marks_obtained = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Marks awarded by faculty evaluator.",
    )
    feedback = models.TextField(
        blank=True,
        default="",
        help_text="Qualitative feedback or comments provided by the faculty evaluator.",
    )
    graded_by_faculty_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="External identifier of the faculty member who graded the submission.",
    )
    graded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when grading was completed.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_assignment_submissions"
        ordering = ["-submitted_at"]
        verbose_name = "Assignment Submission"
        verbose_name_plural = "Assignment Submissions"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student"],
                name="unique_student_assignment_submission",
            )
        ]

    def clean(self):
        super().clean()
        if not self.submission_text.strip() and not self.submission_file:
            raise ValidationError("A submission must include either text content or an uploaded file.")

        if self.marks_obtained is not None and hasattr(self, "assignment") and self.assignment:
            if self.marks_obtained < Decimal("0.00"):
                raise ValidationError({"marks_obtained": "Marks cannot be negative."})
            if self.marks_obtained > self.assignment.max_marks:
                raise ValidationError(
                    {"marks_obtained": f"Marks cannot exceed maximum marks ({self.assignment.max_marks})."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Submission by {self.student.registration_number} for {self.assignment.title}"

