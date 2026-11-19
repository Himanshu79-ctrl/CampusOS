"""
Permission classes for Attendance Management in CampusOS LMS.
Enforces instructor course ownership, student enrollment boundaries, and IDOR protection (SRS Section 3.D).
"""

from rest_framework import permissions
from apps.academics.models import Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile


class IsAttendanceInstructorOrAdmin(permissions.BasePermission):
    """
    Grants attendance management permissions (session creation, marking, correction)
    only to the assigned faculty instructor of the course offering or an academic administrator.
    """

    message = "Permission denied: only the assigned course instructor or an administrator can manage attendance."

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
        # AttendanceSession
        if hasattr(obj, "course_offering") and hasattr(obj.course_offering, "faculty_id"):
            return str(obj.course_offering.faculty_id)
        # AttendanceRecord
        if hasattr(obj, "session") and hasattr(obj.session, "course_offering"):
            return str(obj.session.course_offering.faculty_id)
        return ""


class CanViewOrAccessAttendanceRecord(permissions.BasePermission):
    """
    Ensures students can only view their own attendance records.
    Assigned course instructors and academic admins can view and manage all student records.
    Protects against IDOR data leakage.
    """

    message = "Permission denied: you cannot access another student's attendance record."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        # Check instructor
        from apps.academics.faculty_matcher import is_faculty_assigned
        faculty_id = IsAttendanceInstructorOrAdmin._extract_faculty_id(obj)
        if getattr(request.user, "is_faculty", False) and is_faculty_assigned(request.user, faculty_id):
            return True

        # Check student ownership (safe read methods only)
        if getattr(request.user, "is_student", False) and request.method in permissions.SAFE_METHODS:
            if hasattr(obj, "student") and hasattr(obj.student, "auth_user_id"):
                return str(obj.student.auth_user_id) == str(request.user.user_id)

        return False

