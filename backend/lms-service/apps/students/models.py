"""
Student profile models for CampusOS LMS.
"""

from django.db import models


class StudentProfile(models.Model):
    """
    Represents a student's academic profile within CampusOS LMS.
    References the external Auth service user and Admin department.
    """

    auth_user_id = models.CharField(
        max_length=64,
        unique=True,
        help_text="External identifier from Authentication service.",
    )
    registration_number = models.CharField(
        max_length=32,
        unique=True,
        help_text="Institutional registration/roll number.",
    )
    department_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="External identifier for Admin-owned Department.",
    )
    admission_year = models.PositiveIntegerField(
        help_text="Year of admission into the institution.",
    )
    current_semester = models.PositiveSmallIntegerField(
        default=1,
        help_text="Current enrolled semester.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Designates whether this student is academically active.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_student_profiles"
        ordering = ["registration_number"]
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"

    def __str__(self):
        return f"{self.registration_number} (Auth: {self.auth_user_id})"

