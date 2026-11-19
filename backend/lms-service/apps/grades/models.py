"""
Models for Grades & Academic Results in CampusOS LMS.
Implements GradeItem, GradeRecord, and FinalCourseGrade (SRS Section 3.F).
"""

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from apps.academics.models import Enrollment, EnrollmentStatus


class GradeItemType(models.TextChoices):
    ASSIGNMENT = "ASSIGNMENT", "Assignment"
    EXAM = "EXAM", "Exam"
    QUIZ = "QUIZ", "Quiz"
    PROJECT = "PROJECT", "Project"
    MIDTERM = "MIDTERM", "Midterm Examination"
    FINAL = "FINAL", "Final Examination"
    ATTENDANCE = "ATTENDANCE", "Attendance Score"
    OTHER = "OTHER", "Other Academic Assessment"


class GradeItem(models.Model):
    """
    Represents an assessment component within a CourseOffering that contributes to the gradebook.
    Can be linked to an LMS Assignment or an external Exam from the Exam Engine.
    """

    course_offering = models.ForeignKey(
        "academics.CourseOffering",
        on_delete=models.CASCADE,
        related_name="grade_items",
        help_text="CourseOffering to which this assessment component belongs.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Name of the assessment component (e.g. 'Assignment 1', 'Midterm Exam').",
    )
    item_type = models.CharField(
        max_length=32,
        choices=GradeItemType.choices,
        default=GradeItemType.ASSIGNMENT,
        db_index=True,
        help_text="Category of assessment.",
    )
    max_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("100.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Maximum marks achievable for this assessment component.",
    )
    weightage_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Optional component weightage percentage, if institutionally specified.",
    )
    assignment = models.ForeignKey(
        "assignments.Assignment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_grade_items",
        help_text="Optional link to an internal LMS Assignment.",
    )
    external_exam_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="External identifier of an exam from the Exam Engine microservice.",
    )
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Publication toggle: students can only view published grade items.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_grade_items"
        ordering = ["created_at"]
        verbose_name = "Grade Item"
        verbose_name_plural = "Grade Items"

    def clean(self):
        super().clean()
        if self.max_marks is not None and self.max_marks <= Decimal("0.00"):
            raise ValidationError({"max_marks": "Maximum marks must be strictly greater than zero."})

        if self.weightage_percentage is not None:
            if self.weightage_percentage < Decimal("0.00") or self.weightage_percentage > Decimal("100.00"):
                raise ValidationError({"weightage_percentage": "Weightage percentage must be between 0 and 100."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} (Max: {self.max_marks}) - Offering #{self.course_offering_id}"


class GradeRecord(models.Model):
    """
    Represents an individual student's awarded marks, optional letter grade,
    and faculty feedback for a specific GradeItem.
    """

    grade_item = models.ForeignKey(
        GradeItem,
        on_delete=models.CASCADE,
        related_name="grade_records",
        help_text="Assessment component being graded.",
    )
    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="grade_records",
        help_text="Enrolled student receiving the grade.",
    )
    marks_obtained = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Marks awarded by faculty.",
    )
    letter_grade = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="Optional institutional letter grade entered by faculty (e.g. A+, B).",
    )
    feedback = models.TextField(
        blank=True,
        default="",
        help_text="Qualitative feedback or remarks from faculty.",
    )
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Publication status: students can only view published grade records.",
    )
    graded_by_faculty_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Identifier of the faculty evaluator or administrator.",
    )
    graded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when marks were recorded or last updated.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_grade_records"
        ordering = ["student__registration_number"]
        verbose_name = "Grade Record"
        verbose_name_plural = "Grade Records"
        constraints = [
            models.UniqueConstraint(
                fields=["grade_item", "student"],
                name="unique_student_grade_item",
            )
        ]

    def clean(self):
        super().clean()
        if hasattr(self, "grade_item") and self.grade_item and hasattr(self, "student") and self.student:
            # Enforce active enrollment
            is_enrolled = Enrollment.objects.filter(
                student=self.student,
                course_offering=self.grade_item.course_offering,
                status=EnrollmentStatus.ENROLLED,
            ).exists()
            if not is_enrolled:
                raise ValidationError("Student is not actively enrolled in this course offering.")

            # Validate marks bounds
            if self.marks_obtained is not None:
                if self.marks_obtained < Decimal("0.00"):
                    raise ValidationError({"marks_obtained": "Marks cannot be negative."})
                if self.marks_obtained > self.grade_item.max_marks:
                    raise ValidationError(
                        {"marks_obtained": f"Marks cannot exceed maximum marks ({self.grade_item.max_marks})."}
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.student.registration_number} - {self.grade_item.name}: {self.marks_obtained}"


class FinalCourseGrade(models.Model):
    """
    Represents the published overall final course result for an enrolled student
    in a CourseOffering (SRS Section 3.F).
    """

    course_offering = models.ForeignKey(
        "academics.CourseOffering",
        on_delete=models.CASCADE,
        related_name="final_grades",
        help_text="Course offering for which the final grade is issued.",
    )
    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="final_course_grades",
        help_text="Enrolled student.",
    )
    total_marks_obtained = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Aggregate marks achieved across published assessment components.",
    )
    total_max_marks = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total maximum achievable marks.",
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated percentage (if applicable).",
    )
    final_letter_grade = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="Official letter grade entered/confirmed by faculty.",
    )
    feedback = models.TextField(
        blank=True,
        default="",
        help_text="Overall course performance feedback or remarks.",
    )
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Publication toggle: students can only view published final results.",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when final result was officially published.",
    )
    graded_by_faculty_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Identifier of the faculty instructor who finalized the grade.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_final_course_grades"
        ordering = ["student__registration_number"]
        verbose_name = "Final Course Grade"
        verbose_name_plural = "Final Course Grades"
        constraints = [
            models.UniqueConstraint(
                fields=["course_offering", "student"],
                name="unique_student_course_final_grade",
            )
        ]

    def clean(self):
        super().clean()
        if hasattr(self, "course_offering") and self.course_offering and hasattr(self, "student") and self.student:
            is_enrolled = Enrollment.objects.filter(
                student=self.student,
                course_offering=self.course_offering,
                status=EnrollmentStatus.ENROLLED,
            ).exists()
            if not is_enrolled:
                raise ValidationError("Student is not actively enrolled in this course offering.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Final Grade: {self.student.registration_number} - Offering #{self.course_offering_id}: {self.final_letter_grade or self.percentage or 'Pending'}"

