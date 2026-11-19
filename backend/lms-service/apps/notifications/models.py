"""
Models for Notifications & Announcements in CampusOS LMS (SRS Section 3.G).
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AudienceType(models.TextChoices):
    ALL = "ALL", "All Users"
    STUDENTS = "STUDENTS", "Students Only"
    FACULTY = "FACULTY", "Faculty Only"


class AnnouncementScope(models.TextChoices):
    INSTITUTION = "INSTITUTION", "Institution-Wide"
    DEPARTMENT = "DEPARTMENT", "Department-Level"
    COURSE = "COURSE", "Course-Specific"


class Announcement(models.Model):
    """
    Announcements for institution-wide, department-level, or course-specific communications.
    """

    title = models.CharField(max_length=255, help_text="Headline or title of the announcement.")
    content = models.TextField(help_text="Detailed announcement body (supports markdown/plain text).")
    author_user_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Auth user ID of the creator/author.",
    )
    author_role = models.CharField(
        max_length=50,
        default="admin",
        help_text="Role of the creator at publication time.",
    )
    scope = models.CharField(
        max_length=20,
        choices=AnnouncementScope.choices,
        default=AnnouncementScope.INSTITUTION,
        db_index=True,
        help_text="Target scope: INSTITUTION, DEPARTMENT, or COURSE.",
    )
    audience_type = models.CharField(
        max_length=20,
        choices=AudienceType.choices,
        default=AudienceType.ALL,
        db_index=True,
        help_text="Target audience category: ALL, STUDENTS, or FACULTY.",
    )
    course_offering = models.ForeignKey(
        "academics.CourseOffering",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="announcements",
        help_text="Course offering if this is a course-specific announcement.",
    )
    department_id = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        db_index=True,
        help_text="Department identifier if this is a department-level announcement.",
    )
    is_published = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this announcement is actively visible.",
    )
    published_at = models.DateTimeField(
        default=timezone.now,
        null=True,
        blank=True,
        help_text="Timestamp when announcement was published.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_announcements"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["scope", "is_published"]),
            models.Index(fields=["course_offering", "is_published"]),
            models.Index(fields=["department_id", "is_published"]),
        ]

    def clean(self):
        super().clean()
        if self.scope == AnnouncementScope.COURSE and not self.course_offering_id:
            raise ValidationError({"course_offering": "Course offering is required for course-level announcements."})
        if self.scope == AnnouncementScope.DEPARTMENT and not self.department_id:
            raise ValidationError({"department_id": "Department ID is required for department-level announcements."})
        if self.scope == AnnouncementScope.INSTITUTION:
            if self.course_offering_id:
                raise ValidationError({"course_offering": "Course offering must be null for institution-wide announcements."})
            if self.department_id:
                raise ValidationError({"department_id": "Department ID must be null for institution-wide announcements."})

    def save(self, *args, **kwargs):
        # Auto-infer scope if not explicitly matched
        if self.course_offering_id:
            self.scope = AnnouncementScope.COURSE
        elif self.department_id:
            self.scope = AnnouncementScope.DEPARTMENT
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.scope}] {self.title}"


class NotificationType(models.TextChoices):
    ANNOUNCEMENT = "ANNOUNCEMENT", "Announcement"
    ASSIGNMENT = "ASSIGNMENT", "Assignment"
    GRADE = "GRADE", "Grade / Assessment Result"
    ATTENDANCE = "ATTENDANCE", "Attendance Alert"
    TIMETABLE = "TIMETABLE", "Timetable Update"
    GENERAL = "GENERAL", "General Notification"


class Notification(models.Model):
    """
    Persistent in-app notification delivered to a specific user.
    """

    recipient_user_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Auth user ID of the notification recipient.",
    )
    title = models.CharField(max_length=255, help_text="Short notification subject or summary.")
    message = models.TextField(help_text="Detailed notification content.")
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
        db_index=True,
    )
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indicates whether recipient has read the notification.",
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when notification was marked as read.",
    )
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional context payload (links, source entity IDs, metadata).",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "lms_notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient_user_id", "is_read"]),
            models.Index(fields=["recipient_user_id", "-created_at"]),
        ]

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def __str__(self):
        return f"To: {self.recipient_user_id} | {self.title} ({'Read' if self.is_read else 'Unread'})"

