"""
Permission classes for Timetable & Calendar Management in CampusOS LMS.
Enforces instructor course ownership, student enrollment boundaries, and IDOR protection (SRS Section 3.E).
"""

from rest_framework import permissions
from apps.academics.models import Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile


class IsTimetableInstructorOrAdmin(permissions.BasePermission):
    """
    Grants write/management permissions for timetable slots to the assigned
    course faculty instructor or an academic administrator.
    """

    message = "Permission denied: only the assigned instructor or an administrator can manage timetable schedules."

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
        # TimetableEntry
        if hasattr(obj, "course_offering") and hasattr(obj.course_offering, "faculty_id"):
            return str(obj.faculty_id or obj.course_offering.faculty_id)
        # CalendarEvent
        if hasattr(obj, "course_offering") and obj.course_offering:
            return str(obj.course_offering.faculty_id)
        return ""


class CanViewTimetableEntry(permissions.BasePermission):
    """
    Allows instructors and admins full read access to class schedule slots.
    Allows students read access only to timetable entries for their enrolled courses.
    """

    message = "Permission denied: you must be enrolled in this course to view its schedule."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        faculty_id = IsTimetableInstructorOrAdmin._extract_faculty_id(obj)
        if getattr(request.user, "is_faculty", False) and faculty_id == str(request.user.user_id):
            return True

        if request.method not in permissions.SAFE_METHODS:
            return False

        if getattr(request.user, "is_student", False):
            offering = getattr(obj, "course_offering", None)
            if not offering:
                return False
            profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
            if not profile:
                return False
            return Enrollment.objects.filter(
                student=profile, course_offering=offering, status=EnrollmentStatus.ENROLLED
            ).exists()

        return False

