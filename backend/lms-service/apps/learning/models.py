"""
Models for Course Content & Learning Management in CampusOS LMS.
Implements Course Modules, Topics/Lessons, Learning Resources, and Student Progress.
"""

from django.core.exceptions import ValidationError
from django.db import models


class ResourceType(models.TextChoices):
    FILE = "FILE", "Uploaded File"
    LINK = "LINK", "External Link"


class CourseModule(models.Model):
    """
    Represents a thematic unit, weekly section, or chapter within a CourseOffering.
    """

    course_offering = models.ForeignKey(
        "academics.CourseOffering",
        on_delete=models.CASCADE,
        related_name="modules",
        help_text="CourseOffering to which this module belongs.",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title or name of the module/chapter.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Summary or objectives of the module.",
    )
    order = models.PositiveIntegerField(
        default=1,
        help_text="Display ordering sequence within the course offering.",
    )
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Draft (False) vs Published (True) visibility for students.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_course_modules"
        ordering = ["order", "created_at"]
        verbose_name = "Course Module"
        verbose_name_plural = "Course Modules"
        constraints = [
            models.UniqueConstraint(
                fields=["course_offering", "order"],
                name="unique_module_order_per_offering",
            )
        ]

    def __str__(self) -> str:
        return f"Module: {self.title} (Offering #{self.course_offering_id})"


class Lesson(models.Model):
    """
    Represents an individual topic, lecture, or instructional unit within a module.
    """

    module = models.ForeignKey(
        CourseModule,
        on_delete=models.CASCADE,
        related_name="lessons",
        help_text="Parent CourseModule containing this lesson.",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title of the topic or lesson.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Short overview of the lesson.",
    )
    content = models.TextField(
        blank=True,
        default="",
        help_text="Rich text or markdown learning content for the lesson.",
    )
    order = models.PositiveIntegerField(
        default=1,
        help_text="Display sequence within the module.",
    )
    is_published = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Draft (False) vs Published (True) visibility for students.",
    )
    estimated_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Estimated time in minutes to complete this lesson.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_lessons"
        ordering = ["order", "created_at"]
        verbose_name = "Lesson"
        verbose_name_plural = "Lessons"
        constraints = [
            models.UniqueConstraint(
                fields=["module", "order"],
                name="unique_lesson_order_per_module",
            )
        ]

    def __str__(self) -> str:
        return f"Lesson: {self.title} (Module: {self.module.title})"


class LearningResource(models.Model):
    """
    Represents an attachment, document (PDF, presentation), or external link
    associated with a lesson or an entire module.
    """

    title = models.CharField(
        max_length=255,
        help_text="Resource display title.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Resource notes or description.",
    )
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceType.choices,
        default=ResourceType.FILE,
        help_text="Type of resource: uploaded file or external web link.",
    )
    module = models.ForeignKey(
        CourseModule,
        on_delete=models.CASCADE,
        related_name="resources",
        null=True,
        blank=True,
        help_text="Associated module if attached at module-level.",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="resources",
        null=True,
        blank=True,
        help_text="Associated lesson if attached at lesson-level.",
    )
    file = models.FileField(
        upload_to="course_resources/%Y/%m/",
        blank=True,
        null=True,
        help_text="Uploaded document or media file.",
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
        help_text="MIME type of the file.",
    )
    external_url = models.URLField(
        max_length=2048,
        blank=True,
        default="",
        help_text="External URL if resource_type is LINK.",
    )
    order = models.PositiveIntegerField(
        default=1,
        help_text="Display ordering sequence.",
    )
    is_published = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Visibility flag for students.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_learning_resources"
        ordering = ["order", "created_at"]
        verbose_name = "Learning Resource"
        verbose_name_plural = "Learning Resources"

    def clean(self):
        super().clean()
        if not self.module_id and not self.lesson_id:
            raise ValidationError("A resource must be linked to either a Module or a Lesson.")

        if self.resource_type == ResourceType.FILE and not self.file:
            raise ValidationError({"file": "File is required when resource_type is FILE."})

        if self.resource_type == ResourceType.LINK and not self.external_url:
            raise ValidationError({"external_url": "External URL is required when resource_type is LINK."})

    def save(self, *args, **kwargs):
        # Automatically populate parent module if linked via lesson
        if self.lesson_id and not self.module_id:
            self.module_id = self.lesson.module_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Resource: {self.title} ({self.resource_type})"


class LessonProgress(models.Model):
    """
    Tracks a student's completion status for a lesson.
    """

    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="lesson_progress",
        help_text="Enrolled student profile.",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress_records",
        help_text="Target lesson.",
    )
    is_completed = models.BooleanField(
        default=False,
        help_text="Designates whether the student has completed this lesson.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the lesson was completed.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lms_lesson_progress"
        verbose_name = "Lesson Progress"
        verbose_name_plural = "Lesson Progress Records"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "lesson"],
                name="unique_student_lesson_progress",
            )
        ]

    def __str__(self) -> str:
        status_str = "Completed" if self.is_completed else "Incomplete"
        return f"{self.student.registration_number} - {self.lesson.title}: {status_str}"

