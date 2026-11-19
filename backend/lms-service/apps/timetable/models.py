"""
Models for Timetable and Calendar Management in CampusOS LMS.
Implements TimetableEntry and CalendarEvent (SRS Section 3.E).
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class DayOfWeek(models.TextChoices):
    MONDAY = "MONDAY", "Monday"
    TUESDAY = "TUESDAY", "Tuesday"
    WEDNESDAY = "WEDNESDAY", "Wednesday"
    THURSDAY = "THURSDAY", "Thursday"
    FRIDAY = "FRIDAY", "Friday"
    SATURDAY = "SATURDAY", "Saturday"
    SUNDAY = "SUNDAY", "Sunday"


class ClassType(models.TextChoices):
    LECTURE = "LECTURE", "Lecture"
    LAB = "LAB", "Lab"
    TUTORIAL = "TUTORIAL", "Tutorial"
    SEMINAR = "SEMINAR", "Seminar"


class TimetableEntry(models.Model):
    """
    Represents a recurring scheduled class session for a CourseOffering.
    Stores room, day of week, times, faculty assignment, and supports conflict validation.
    """

    course_offering = models.ForeignKey(
        "academics.CourseOffering",
        on_delete=models.CASCADE,
        related_name="timetable_entries",
        help_text="CourseOffering to which this timetable entry belongs.",
    )
    faculty_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Instructor assigned for this class slot.",
    )
    day_of_week = models.CharField(
        max_length=16,
        choices=DayOfWeek.choices,
        db_index=True,
        help_text="Day of the week for the recurring class slot.",
    )
    start_time = models.TimeField(
        help_text="Scheduled slot start time.",
    )
    end_time = models.TimeField(
        help_text="Scheduled slot end time.",
    )
    room = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Classroom, lecture hall, or lab room.",
    )
    building = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Campus building, wing, or block.",
    )
    entry_type = models.CharField(
        max_length=32,
        choices=ClassType.choices,
        default=ClassType.LECTURE,
        help_text="Classification of the scheduled session.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Active status of this class schedule entry.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_timetable_entries"
        ordering = ["day_of_week", "start_time"]
        verbose_name = "Timetable Entry"
        verbose_name_plural = "Timetable Entries"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError({"end_time": "Class end time must be strictly after the start time."})

        # Automatically default faculty_id from course_offering if not explicitly set
        if not self.faculty_id and hasattr(self, "course_offering") and self.course_offering:
            self.faculty_id = str(self.course_offering.faculty_id)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.course_offering_id} | {self.day_of_week} {self.start_time}-{self.end_time} in {self.room}"


class CalendarEventType(models.TextChoices):
    ACADEMIC = "ACADEMIC", "Academic Milestone"
    HOLIDAY = "HOLIDAY", "Holiday"
    EXAM = "EXAM", "Examination"
    EVENT = "EVENT", "Institutional Event"
    DEADLINE = "DEADLINE", "Academic Deadline"


class CalendarEvent(models.Model):
    """
    Represents an institutional or course-specific calendar event / announcement.
    """

    title = models.CharField(
        max_length=255,
        help_text="Title or summary of the calendar event.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Detailed description of the event or announcement.",
    )
    event_type = models.CharField(
        max_length=32,
        choices=CalendarEventType.choices,
        default=CalendarEventType.EVENT,
        db_index=True,
        help_text="Category of the calendar event.",
    )
    start_date = models.DateField(
        db_index=True,
        help_text="Event start date.",
    )
    end_date = models.DateField(
        db_index=True,
        help_text="Event end date.",
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Optional event start time.",
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Optional event end time.",
    )
    academic_term = models.ForeignKey(
        "academics.AcademicTerm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_events",
        help_text="Optional academic term this event pertains to.",
    )
    course_offering = models.ForeignKey(
        "academics.CourseOffering",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_events",
        help_text="Optional course offering for course-specific events.",
    )
    created_by_user_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="User ID of the creator (faculty or admin).",
    )
    is_published = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Visibility status for students and faculty.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_calendar_events"
        ordering = ["start_date", "start_time"]
        verbose_name = "Calendar Event"
        verbose_name_plural = "Calendar Events"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({"end_date": "Event end date cannot precede start date."})

        if self.start_date == self.end_date and self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError({"end_time": "Event end time must be after the start time on the same date."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.title} ({self.start_date})"

