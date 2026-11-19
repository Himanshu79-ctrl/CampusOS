"""
Models for Attendance Management in CampusOS LMS.
Implements AttendanceSession and AttendanceRecord (SRS Section 3.D).
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.academics.models import Enrollment, EnrollmentStatus


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    ABSENT = "ABSENT", "Absent"
    LATE = "LATE", "Late"


class AttendanceSession(models.Model):
    """
    Represents an instructional lecture, lab, or tutorial attendance session
    associated with a CourseOffering.
    """

    course_offering = models.ForeignKey(
        "academics.CourseOffering",
        on_delete=models.CASCADE,
        related_name="attendance_sessions",
        help_text="Course offering for which this attendance session is conducted.",
    )
    session_date = models.DateField(
        default=timezone.now,
        db_index=True,
        help_text="Date on which the lecture/session took place.",
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Scheduled start time of the session.",
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Scheduled end time of the session.",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Lecture topic or session title.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Detailed coverage notes or syllabus agenda.",
    )
    created_by_faculty_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Identifier of the faculty member who created the session.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_attendance_sessions"
        ordering = ["-session_date", "-created_at"]
        verbose_name = "Attendance Session"
        verbose_name_plural = "Attendance Sessions"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError({"end_time": "Session end time must be after the start time."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        name = self.title or "Session"
        return f"{name} ({self.session_date}) - Offering #{self.course_offering_id}"


class AttendanceRecord(models.Model):
    """
    Represents an individual student's attendance entry for a given AttendanceSession.
    Captures Present, Absent, or Late status, along with audit tracking for corrections.
    """

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="records",
        help_text="Target attendance session.",
    )
    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="attendance_records",
        help_text="Enrolled student whose attendance is recorded.",
    )
    status = models.CharField(
        max_length=16,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        db_index=True,
        help_text="Attendance status: PRESENT, ABSENT, or LATE.",
    )
    remarks = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional remarks (e.g. excused absence note).",
    )
    audit_reason = models.TextField(
        blank=True,
        default="",
        help_text="Audit explanation when attendance is corrected or amended.",
    )
    recorded_by_user_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Identifier of the faculty member or admin who logged/corrected this record.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_attendance_records"
        ordering = ["student__registration_number"]
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "student"],
                name="unique_student_session_attendance",
            )
        ]

    def clean(self):
        super().clean()
        # Verify student is actively enrolled in the course offering
        if hasattr(self, "session") and self.session and hasattr(self, "student") and self.student:
            is_enrolled = Enrollment.objects.filter(
                student=self.student,
                course_offering=self.session.course_offering,
                status=EnrollmentStatus.ENROLLED,
            ).exists()
            if not is_enrolled:
                raise ValidationError("Student is not actively enrolled in this course offering.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.student.registration_number} - {self.session.session_date}: {self.status}"

