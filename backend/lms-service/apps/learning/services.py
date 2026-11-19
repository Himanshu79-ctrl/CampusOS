"""
Service layer for Learning & Course Content in CampusOS LMS.
Encapsulates business logic for content reordering, publishing, progress tracking,
and file validation.
"""

import os
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.academics.models import CourseOffering, Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile
from .models import CourseModule, Lesson, LearningResource, LessonProgress, ResourceType

ALLOWED_FILE_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".txt",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit


class LearningContentService:
    """
    Business service layer managing learning modules, lessons, resources, and progress.
    """

    @classmethod
    def check_user_content_access(cls, user, course_offering: CourseOffering) -> str:
        """
        Determines user's access mode to a course offering's content:
        Returns:
          - "MANAGE": Academic admin or assigned faculty instructor.
          - "VIEW": Enrolled active student.
        Raises:
          - PermissionDenied: If user is not authorized.
        """
        if getattr(user, "is_admin", False):
            return "MANAGE"

        if getattr(user, "is_faculty", False):
            from apps.academics.faculty_matcher import is_faculty_assigned
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

        raise PermissionDenied("Authentication required to access course content.")

    @classmethod
    def get_modules_queryset(cls, user, course_offering: CourseOffering):
        """
        Returns modules queryset appropriately filtered based on user privileges.
        Students see only published modules. Instructors/Admins see all.
        """
        access_mode = cls.check_user_content_access(user, course_offering)
        qs = CourseModule.objects.filter(course_offering=course_offering)

        if access_mode == "VIEW":
            qs = qs.filter(is_published=True)

        return qs.order_by("order", "created_at")

    @classmethod
    def publish_module(cls, module: CourseModule, is_published: bool, cascade_lessons: bool = False) -> CourseModule:
        """
        Toggles publish status of a module.
        Optionally cascades publish state to all contained lessons.
        """
        with transaction.atomic():
            module.is_published = is_published
            module.save(update_fields=["is_published", "updated_at"])

            if cascade_lessons:
                module.lessons.update(is_published=is_published, updated_at=timezone.now())

        return module

    @classmethod
    def publish_lesson(cls, lesson: Lesson, is_published: bool) -> Lesson:
        """
        Toggles publish status of an individual lesson.
        """
        lesson.is_published = is_published
        lesson.save(update_fields=["is_published", "updated_at"])
        return lesson

    @classmethod
    def record_lesson_progress(cls, user, lesson: Lesson, is_completed: bool) -> LessonProgress:
        """
        Records or updates a student's completion progress for a published lesson.
        """
        if not getattr(user, "is_student", False):
            raise PermissionDenied("Only students can record lesson progress.")

        profile = StudentProfile.objects.filter(auth_user_id=str(user.user_id)).first()
        if not profile:
            raise PermissionDenied("Student academic profile required.")

        # Verify enrollment
        course_offering = lesson.module.course_offering
        is_enrolled = Enrollment.objects.filter(
            student=profile,
            course_offering=course_offering,
            status=EnrollmentStatus.ENROLLED,
        ).exists()
        if not is_enrolled:
            raise PermissionDenied("You must be enrolled in the course offering to record progress.")

        # Ensure lesson is published
        if not lesson.is_published or not lesson.module.is_published:
            raise PermissionDenied("Cannot record progress on unpublished lessons.")

        progress, created = LessonProgress.objects.get_or_create(
            student=profile,
            lesson=lesson,
            defaults={
                "is_completed": is_completed,
                "completed_at": timezone.now() if is_completed else None,
            },
        )
        if not created:
            progress.is_completed = is_completed
            progress.completed_at = timezone.now() if is_completed else None
            progress.save(update_fields=["is_completed", "completed_at", "updated_at"])

        return progress

    @classmethod
    def validate_uploaded_resource_file(cls, uploaded_file) -> tuple[int, str]:
        """
        Validates file type extension and size.
        Returns (file_size_bytes, mime_type).
        """
        if not uploaded_file:
            raise ValidationError("File is required.")

        file_name = uploaded_file.name
        ext = os.path.splitext(file_name)[1].lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            raise ValidationError(
                f"File type '{ext}' is not permitted. Allowed types: {', '.join(sorted(ALLOWED_FILE_EXTENSIONS))}"
            )

        file_size = uploaded_file.size
        if file_size > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise ValidationError(f"File size exceeds the {max_mb}MB limit.")

        content_type = getattr(uploaded_file, "content_type", "application/octet-stream")
        return file_size, content_type

