"""
Role-based permission classes for CampusOS LMS service.
Enforces boundaries between Students, Faculty, and Academic Administrators.
"""

from rest_framework import permissions


class IsAuthenticated(permissions.BasePermission):
    """
    Allows access only to authenticated users verified by ExternalJWTAuthentication.
    """

    message = "Authentication credentials were not provided or are invalid."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsStudent(permissions.BasePermission):
    """
    Allows access only to users with the 'student' role.
    """

    message = "Access restricted: this action requires student privileges."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_student", False)
        )


class IsFaculty(permissions.BasePermission):
    """
    Allows access only to users with the 'faculty' role.
    """

    message = "Access restricted: this action requires faculty privileges."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_faculty", False)
        )


class IsAcademicAdmin(permissions.BasePermission):
    """
    Allows access only to users with the 'admin' or 'academic_admin' role.
    """

    message = "Access restricted: this action requires academic administrator privileges."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_admin", False)
        )


class IsSelfStudentOrAdmin(permissions.BasePermission):
    """
    Object-level permission allowing students to access only their own StudentProfile.
    Academic administrators can access any student profile.
    Prevents Insecure Direct Object References (IDOR).
    """

    message = "Permission denied: you cannot access another student's academic profile."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        if getattr(request.user, "is_student", False):
            # obj can be a StudentProfile instance
            auth_user_id = getattr(obj, "auth_user_id", None)
            return auth_user_id == request.user.user_id

        return False


class IsFacultyOfferingOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission allowing access to course offerings and roster
    only to the assigned faculty instructor or an academic administrator.
    """

    message = "Permission denied: you are not the assigned faculty instructor for this course offering."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        if getattr(request.user, "is_faculty", False):
            # obj can be a CourseOffering instance
            from apps.academics.faculty_matcher import is_faculty_assigned
            faculty_id = getattr(obj, "faculty_id", None)
            return is_faculty_assigned(request.user, faculty_id)

        return False


class IsEnrollmentOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission allowing students to view/drop only their own enrollments,
    or the assigned faculty of the course offering, or an academic administrator.
    """

    message = "Permission denied: you do not have permission to access this enrollment record."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        if getattr(request.user, "is_student", False):
            return obj.student.auth_user_id == request.user.user_id

        if getattr(request.user, "is_faculty", False):
            from apps.academics.faculty_matcher import is_faculty_assigned
            return is_faculty_assigned(request.user, obj.course_offering.faculty_id)

        return False

