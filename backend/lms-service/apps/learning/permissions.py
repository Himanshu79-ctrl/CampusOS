"""
Permission classes for Course Content & Learning Management in CampusOS LMS.
Enforces role separation between Faculty instructors, Enrolled Students, and Academic Admins.
"""

from rest_framework import permissions
from apps.academics.models import Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile


class IsOfferingInstructorOrAdmin(permissions.BasePermission):
    """
    Grants write/manage permissions only to the assigned faculty instructor
    of the course offering or an academic administrator.
    """

    message = "Permission denied: only the assigned course instructor or an administrator can manage learning content."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        if getattr(request.user, "is_faculty", False):
            from apps.academics.faculty_matcher import is_faculty_assigned
            faculty_id = self._extract_faculty_id(obj)
            return is_faculty_assigned(request.user, faculty_id)

        return False

    @staticmethod
    def _extract_faculty_id(obj) -> str:
        # CourseOffering
        if hasattr(obj, "faculty_id"):
            return str(obj.faculty_id)
        # CourseModule
        if hasattr(obj, "course_offering"):
            return str(obj.course_offering.faculty_id)
        # Lesson
        if hasattr(obj, "module"):
            return str(obj.module.course_offering.faculty_id)
        # LearningResource
        if hasattr(obj, "lesson") and obj.lesson:
            return str(obj.lesson.module.course_offering.faculty_id)
        if hasattr(obj, "module") and obj.module:
            return str(obj.module.course_offering.faculty_id)
        return ""


class CanViewOrManageLearningContent(permissions.BasePermission):
    """
    Allows instructors and admins full access (including draft content).
    Allows enrolled students read-only access to published content.
    """

    message = "Access restricted: you must be enrolled in this course to view its published learning content."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # 1. Admin always allowed
        if getattr(request.user, "is_admin", False):
            return True

        # 2. Assigned faculty instructor always allowed
        from apps.academics.faculty_matcher import is_faculty_assigned
        faculty_id = IsOfferingInstructorOrAdmin._extract_faculty_id(obj)
        if getattr(request.user, "is_faculty", False) and is_faculty_assigned(request.user, faculty_id):
            return True

        # 3. For write operations, non-instructors/non-admins are blocked
        if request.method not in permissions.SAFE_METHODS:
            return False

        # 4. Students can only view if actively enrolled AND content is published
        if getattr(request.user, "is_student", False):
            # Check draft visibility
            is_published = getattr(obj, "is_published", True)
            if not is_published:
                return False

            # If it's a lesson, parent module must also be published
            if hasattr(obj, "module") and hasattr(obj.module, "is_published"):
                if not obj.module.is_published:
                    return False

            # If it's a resource linked to a lesson, the lesson must also be published
            if hasattr(obj, "lesson") and obj.lesson and hasattr(obj.lesson, "is_published"):
                if not obj.lesson.is_published:
                    return False

            # Check enrollment
            course_offering = self._extract_course_offering(obj)
            if not course_offering:
                return False

            profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
            if not profile:
                return False

            return Enrollment.objects.filter(
                student=profile,
                course_offering=course_offering,
                status=EnrollmentStatus.ENROLLED,
            ).exists()

        return False

    @staticmethod
    def _extract_course_offering(obj):
        if hasattr(obj, "course_offering"):
            return obj.course_offering
        if hasattr(obj, "module") and hasattr(obj.module, "course_offering"):
            return obj.module.course_offering
        if hasattr(obj, "lesson") and obj.lesson and hasattr(obj.lesson, "module"):
            return obj.lesson.module.course_offering
        return None

