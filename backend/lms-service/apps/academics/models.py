"""
Academic models for CampusOS LMS: AcademicTerm, CourseOffering, and Enrollment.
"""

import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

ACADEMIC_YEAR_REGEX = r"^\d{4}-\d{4}$"
academic_year_validator = RegexValidator(
    regex=ACADEMIC_YEAR_REGEX,
    message="Academic year must follow the format 'YYYY-YYYY' (e.g., '2026-2027').",
)


class TermStatus(models.TextChoices):
    UPCOMING = "UPCOMING", "Upcoming"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    ARCHIVED = "ARCHIVED", "Archived"


class OfferingStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class EnrollmentStatus(models.TextChoices):
    ENROLLED = "ENROLLED", "Enrolled"
    DROPPED = "DROPPED", "Dropped"
    COMPLETED = "COMPLETED", "Completed"
    AUDIT = "AUDIT", "Audit"


class AcademicTerm(models.Model):
    """
    Represents an institutional academic term/semester.
    Enforces that only ONE academic term may have ACTIVE status institution-wide.
    """

    name = models.CharField(
        max_length=64,
        help_text="Human-readable term name (e.g., 'Fall 2026', 'Odd Semester 2026-2027').",
    )
    academic_year = models.CharField(
        max_length=16,
        db_index=True,
        validators=[academic_year_validator],
        help_text="Academic year string in YYYY-YYYY format (e.g., '2026-2027').",
    )
    term_number = models.PositiveSmallIntegerField(
        help_text="Sequence number of the term within the academic year.",
    )
    start_date = models.DateField(
        help_text="Instructional start date of the term.",
    )
    end_date = models.DateField(
        help_text="Instructional end date of the term.",
    )
    status = models.CharField(
        max_length=16,
        choices=TermStatus.choices,
        default=TermStatus.UPCOMING,
        db_index=True,
        help_text="Current lifecycle state of the academic term.",
    )
    is_enrollment_open = models.BooleanField(
        default=False,
        help_text="Designates whether course registration/enrollment is currently open for this term.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_academic_terms"
        ordering = ["-start_date"]
        verbose_name = "Academic Term"
        verbose_name_plural = "Academic Terms"
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gt=models.F("start_date")),
                name="check_term_end_date_after_start_date",
            ),
            models.UniqueConstraint(
                fields=["academic_year", "term_number"],
                name="unique_academic_term_per_year",
            ),
            # PostgreSQL conditional constraint: Only ONE term can be ACTIVE institution-wide
            models.UniqueConstraint(
                fields=["status"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_academic_term",
            ),
        ]

    def clean(self):
        super().clean()
        # 1. Date chronological order validation
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError(
                {"end_date": "End date must be strictly after the start date."}
            )

        # 2. Academic year format and consecutive year logic
        if self.academic_year:
            if not re.match(ACADEMIC_YEAR_REGEX, self.academic_year):
                raise ValidationError(
                    {"academic_year": "Academic year must follow the format 'YYYY-YYYY' (e.g., '2026-2027')."}
                )
            try:
                start_yr, end_yr = map(int, self.academic_year.split("-"))
                if end_yr != start_yr + 1:
                    raise ValidationError(
                        {"academic_year": f"Academic year range must be consecutive years (e.g., '{start_yr}-{start_yr + 1}')."}
                    )
            except ValueError:
                raise ValidationError(
                    {"academic_year": "Invalid academic year values."}
                )

        # 3. Only one active term institution-wide
        if self.status == TermStatus.ACTIVE:
            qs = AcademicTerm.objects.filter(status=TermStatus.ACTIVE)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"status": "Only one academic term can have ACTIVE status institution-wide."}
                )

        # 4. COMPLETED terms cannot have enrollment open
        if self.status == TermStatus.COMPLETED and self.is_enrollment_open:
            raise ValidationError(
                {"is_enrollment_open": "Enrollment cannot be open for a completed academic term."}
            )

    def __str__(self):
        return f"{self.name} ({self.academic_year})"


class CourseOffering(models.Model):
    """
    Represents an instance of a catalog course delivered during a specific academic term.
    References Course, Faculty, and Department owned by the Admin service.
    """

    course_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="External identifier for Admin-owned Course catalog entry.",
    )
    faculty_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="External identifier for Admin-owned Faculty instructor.",
    )
    department_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="External identifier for Admin-owned Department.",
    )
    academic_term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.PROTECT,
        related_name="course_offerings",
        help_text="The academic term for this offering.",
    )
    section = models.CharField(
        max_length=32,
        help_text="Section identifier (e.g., 'A', 'B', 'Lab-01').",
    )
    capacity = models.PositiveIntegerField(
        help_text="Maximum number of enrolled students allowed.",
    )
    status = models.CharField(
        max_length=16,
        choices=OfferingStatus.choices,
        default=OfferingStatus.DRAFT,
        db_index=True,
        help_text="Current lifecycle state of the course offering.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_course_offerings"
        ordering = ["academic_term", "course_id", "section"]
        verbose_name = "Course Offering"
        verbose_name_plural = "Course Offerings"
        constraints = [
            models.CheckConstraint(
                check=models.Q(capacity__gt=0),
                name="check_course_offering_capacity_positive",
            ),
            models.UniqueConstraint(
                fields=["course_id", "academic_term", "section"],
                name="unique_offering_per_section_term",
            ),
        ]

    def clean(self):
        super().clean()
        if self.capacity is not None and self.capacity <= 0:
            raise ValidationError(
                {"capacity": "Course offering capacity must be a positive integer greater than zero."}
            )

    def __str__(self):
        return f"Course {self.course_id} - Sec {self.section} ({self.academic_term.name})"


class Enrollment(models.Model):
    """
    Represents an enrollment relationship between a student and a course offering.
    Prevents duplicate concurrent active enrollments, while allowing re-enrollment after dropping.
    """

    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="enrollments",
        help_text="The enrolled student.",
    )
    course_offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.PROTECT,
        related_name="enrollments",
        help_text="The course offering being enrolled in.",
    )
    enrolled_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the student enrolled.",
    )
    status = models.CharField(
        max_length=16,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED,
        db_index=True,
        help_text="Current state of the enrollment.",
    )
    dropped_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the course was dropped, if applicable.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_enrollments"
        ordering = ["-enrolled_at"]
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"
        constraints = [
            # Conditional unique constraint: A student cannot have multiple concurrent ENROLLED records
            models.UniqueConstraint(
                fields=["student", "course_offering"],
                condition=models.Q(status="ENROLLED"),
                name="unique_active_enrollment_per_student_offering",
            ),
        ]

    def clean(self):
        super().clean()
        if hasattr(self, "student") and self.student and not self.student.is_active:
            raise ValidationError(
                {"student": "Cannot enroll an inactive student."}
            )
        if (
            hasattr(self, "course_offering")
            and self.course_offering
            and self.status == EnrollmentStatus.ENROLLED
            and self.course_offering.status != OfferingStatus.PUBLISHED
        ):
            raise ValidationError(
                {"course_offering": "Cannot actively enroll in an unpublished course offering."}
            )

    def __str__(self):
        return f"{self.student.registration_number} -> {self.course_offering} [{self.status}]"
