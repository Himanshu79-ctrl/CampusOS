"""
Permission classes for Assignment Management & Student Submissions in CampusOS LMS.
Enforces instructor course ownership, student enrollment boundaries, and IDOR protection.
"""

from rest_framework import permissions
from apps.academics.faculty_matcher import is_faculty_assigned
from apps.academics.models import Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile


class IsAssignmentInstructorOrAdmin(permissions.BasePermission):
    """
    Grants write/evaluation permissions only to the assigned faculty instructor
    of the course offering or an academic administrator.
    """

    message = "Permission denied: only the assigned course instructor or an administrator can manage assignments and evaluations."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        if getattr(request.user, "is_faculty", False):
            faculty_id = self._extract_faculty_id(obj)
            return is_faculty_assigned(request.user, faculty_id)

        return False

    @staticmethod
    def _extract_faculty_id(obj) -> str:
        # CourseOffering
        if hasattr(obj, "faculty_id"):
            return str(obj.faculty_id)
        # Assignment
        if hasattr(obj, "course_offering"):
            return str(obj.course_offering.faculty_id)
        # AssignmentSubmission
        if hasattr(obj, "assignment") and hasattr(obj.assignment, "course_offering"):
            return str(obj.assignment.course_offering.faculty_id)
        return ""


class CanViewOrAccessAssignment(permissions.BasePermission):
    """
    Allows instructors and admins full access to assignments.
    Allows enrolled students access only to published assignments.
    """

    message = "Access restricted: you must be enrolled in this course to view published assignments."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        faculty_id = IsAssignmentInstructorOrAdmin._extract_faculty_id(obj)
        if getattr(request.user, "is_faculty", False):
            if is_faculty_assigned(request.user, faculty_id):
                return True

        if request.method not in permissions.SAFE_METHODS:
            return False

        if getattr(request.user, "is_student", False):
            # Must be published
            is_published = getattr(obj, "is_published", False)
            if not is_published:
                return False

            course_offering = getattr(obj, "course_offering", None)
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


class IsSubmissionOwnerOrInstructor(permissions.BasePermission):
    """
    Ensures students can view and submit only their OWN submission records.
    Assigned course instructors and academic admins can view and grade any student submission.
    Prevents IDOR data leakage.
    """

    message = "Permission denied: you cannot access another student's assignment submission or private feedback."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        # Check instructor
        faculty_id = IsAssignmentInstructorOrAdmin._extract_faculty_id(obj)
        if getattr(request.user, "is_faculty", False):
            if is_faculty_assigned(request.user, faculty_id):
                return True

        # Check student ownership
        if getattr(request.user, "is_student", False):
            if hasattr(obj, "student"):
                return str(obj.student.auth_user_id) == str(request.user.user_id)

        return False

