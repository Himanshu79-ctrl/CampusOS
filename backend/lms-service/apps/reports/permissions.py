"""
Role-based permissions for Reports & Analytics in CampusOS LMS.
Enforces boundaries between Administrators, Department Heads (HODs), Faculty Instructors, and Students.
"""

from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Allows access strictly to academic administrators (admin, super_admin, academic_admin).
    """

    message = "Access restricted: this report requires academic administrator privileges."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, "is_admin", False))


class IsHODOrAdmin(permissions.BasePermission):
    """
    Allows access to Department Reports:
      - Academic Administrators (admin, super_admin, academic_admin) can access any department report.
      - Faculty members authoritatively verified as HOD for their assigned department by the Admin Service
        can access only their own department report.
      - Ordinary faculty, students, and unauthorized users are rejected (fail-closed).
    """

    message = "Access restricted: only authorized Department Heads (HODs) or Administrators may access this report."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        if getattr(request.user, "is_admin", False):
            return True

        if getattr(request.user, "is_faculty", False):
            user_dept = getattr(request.user, "department_id", "") or request.user.claims.get("department_id", "")
            if not user_dept:
                return False

            from apps.academics.admin_client import AdminServiceClient

            admin_client = AdminServiceClient()
            return admin_client.is_department_hod(request.user, user_dept)

        return False


class IsFacultyCourseOwnerOrAdmin(permissions.BasePermission):
    """
    Allows access to Course Offering Reports:
      - Academic Administrators can access any course offering report.
      - Faculty instructors can access reports only for course offerings they teach.
      - Students and other faculty are rejected.
    """

    message = "Access restricted: you are not the assigned instructor for this course offering."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (getattr(request.user, "is_admin", False) or getattr(request.user, "is_faculty", False))
        )

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "is_admin", False):
            return True

        if getattr(request.user, "is_faculty", False):
            faculty_id = getattr(obj, "faculty_id", None)
            return str(faculty_id) == str(request.user.user_id)

        return False

