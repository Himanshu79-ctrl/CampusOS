"""
Permission classes for Grades & Academic Results in CampusOS LMS.
Enforces instructor course ownership, student enrollment boundaries, and IDOR protection (SRS Section 3.F).
"""

from rest_framework import permissions
from apps.academics.models import Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile


class IsGradeInstructorOrAdmin(permissions.BasePermission):
    """
    Grants management permissions (creating grade items, entering marks,
    updating feedback, publishing grades) to the assigned course instructor or an academic admin.
    """

    message = "Permission denied: only the assigned course instructor or an administrator can manage grades and gradebooks."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        if getattr(request.user, "is_faculty", False):
            faculty_id = self._extract_faculty_id(obj)
            return faculty_id == str(request.user.user_id)

        return False

    @staticmethod
    def _extract_faculty_id(obj) -> str:
        # CourseOffering
        if hasattr(obj, "faculty_id"):
            return str(obj.faculty_id)
        # GradeItem
        if hasattr(obj, "course_offering") and hasattr(obj.course_offering, "faculty_id"):
            return str(obj.course_offering.faculty_id)
        # GradeRecord
        if hasattr(obj, "grade_item") and hasattr(obj.grade_item, "course_offering"):
            return str(obj.grade_item.course_offering.faculty_id)
        # FinalCourseGrade
        if hasattr(obj, "course_offering") and hasattr(obj.course_offering, "faculty_id"):
            return str(obj.course_offering.faculty_id)
        return ""


class CanViewGradeRecord(permissions.BasePermission):
    """
    Ensures students can only view their own published grade records.
    Assigned course instructors and academic admins have full access.
    Protects against IDOR data leakage.
    """

    message = "Permission denied: you cannot view another student's grade record."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        faculty_id = IsGradeInstructorOrAdmin._extract_faculty_id(obj)
        if getattr(request.user, "is_faculty", False) and faculty_id == str(request.user.user_id):
            return True

        if request.method not in permissions.SAFE_METHODS:
            return False

        if getattr(request.user, "is_student", False):
            # Must be published either at record or grade_item level
            is_pub = getattr(obj, "is_published", False) or (
                hasattr(obj, "grade_item") and getattr(obj.grade_item, "is_published", False)
            )
            if not is_pub:
                return False

            if hasattr(obj, "student") and hasattr(obj.student, "auth_user_id"):
                return str(obj.student.auth_user_id) == str(request.user.user_id)

        return False


class CanViewFinalGrade(permissions.BasePermission):
    """
    Ensures students can only view their own published final course grade.
    Assigned course instructors and academic admins have full access.
    """

    message = "Permission denied: you cannot access another student's final course result."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        faculty_id = IsGradeInstructorOrAdmin._extract_faculty_id(obj)
        if getattr(request.user, "is_faculty", False) and faculty_id == str(request.user.user_id):
            return True

        if request.method not in permissions.SAFE_METHODS:
            return False

        if getattr(request.user, "is_student", False):
            if not getattr(obj, "is_published", False):
                return False
            if hasattr(obj, "student") and hasattr(obj.student, "auth_user_id"):
                return str(obj.student.auth_user_id) == str(request.user.user_id)

        return False

