"""
API views for Reports & Analytics in CampusOS LMS (SRS Section 3.16 / 3.H).
"""

from datetime import datetime
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView


class CSVRenderer(BaseRenderer):
    media_type = "text/csv"
    format = "csv"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data

from apps.academics.models import CourseOffering
from .permissions import IsAdminUser, IsFacultyCourseOwnerOrAdmin, IsHODOrAdmin
from .services import ReportService
from config.permissions import IsAuthenticated


class AdminOverviewReportView(APIView):
    """
    GET /api/admin/reports/overview/
    Institutional overview and aggregate KPIs for administrators.
    Filters:
      - ?term_id=<int>
      - ?department_id=<str>
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        term_id = request.query_params.get("term_id")
        department_id = request.query_params.get("department_id")

        if term_id:
            try:
                term_id = int(term_id)
            except ValueError:
                raise ValidationError({"term_id": "term_id must be a valid integer."})

        data = ReportService.get_admin_overview(term_id=term_id, department_id=department_id)
        return Response(data, status=status.HTTP_200_OK)


class AdminStudentsReportView(APIView):
    """
    GET /api/admin/reports/students/
    Student progress, attendance, and performance summary for administrators.
    Filters:
      - ?department_id=<str>
      - ?admission_year=<int>
      - ?current_semester=<int>
      - ?is_active=true|false
      - ?search=<str>
      - ?page=<int>&page_size=<int>
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        department_id = request.query_params.get("department_id")
        admission_year = request.query_params.get("admission_year")
        current_semester = request.query_params.get("current_semester")
        is_active_param = request.query_params.get("is_active")
        search = request.query_params.get("search")
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)

        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1")

        if admission_year:
            try:
                admission_year = int(admission_year)
            except ValueError:
                raise ValidationError({"admission_year": "admission_year must be an integer."})

        if current_semester:
            try:
                current_semester = int(current_semester)
            except ValueError:
                raise ValidationError({"current_semester": "current_semester must be an integer."})

        data = ReportService.get_admin_students(
            department_id=department_id,
            admission_year=admission_year,
            current_semester=current_semester,
            is_active=is_active,
            search=search,
            page=page,
            page_size=page_size,
        )
        return Response(data, status=status.HTTP_200_OK)


class DepartmentReportView(APIView):
    """
    GET /api/hod/reports/department/
    Department-level analytics for authorized HODs or Administrators.
    Filters:
      - ?department_id=<str> (required for admin, inferred for HOD)
      - ?term_id=<int>
    """

    permission_classes = [IsHODOrAdmin]

    def get(self, request):
        user = request.user
        req_dept = request.query_params.get("department_id")
        term_id = request.query_params.get("term_id")

        if getattr(user, "is_admin", False):
            if not req_dept:
                raise ValidationError({"department_id": "department_id query parameter is required for administrators."})
            effective_dept = req_dept
        else:
            # Faculty / HOD
            user_dept = getattr(user, "department_id", "") or user.claims.get("department_id", "")
            if not user_dept:
                raise PermissionDenied("No department assigned to your profile.")
            if req_dept and req_dept != user_dept:
                raise PermissionDenied("You do not have permission to view other departments' reports.")
            effective_dept = user_dept

        if term_id:
            try:
                term_id = int(term_id)
            except ValueError:
                raise ValidationError({"term_id": "term_id must be a valid integer."})

        data = ReportService.get_department_report(department_id=effective_dept, term_id=term_id)
        return Response(data, status=status.HTTP_200_OK)


class CourseReportView(APIView):
    """
    GET /api/faculty/reports/course/<int:course_offering_id>/
    Course offering performance, enrollment, and attendance analytics for instructors and administrators.
    """

    permission_classes = [IsFacultyCourseOwnerOrAdmin]

    def get(self, request, course_offering_id):
        offering = get_object_or_404(CourseOffering, pk=course_offering_id)
        self.check_object_permissions(request, offering)

        data = ReportService.get_course_report(course_offering=offering)
        return Response(data, status=status.HTTP_200_OK)


class AttendanceReportView(APIView):
    """
    GET /api/reports/attendance/
    Role-based attendance reports:
      - Students: personal course-wise attendance summary.
      - Faculty: attendance breakdown for their assigned offerings.
      - Administrators: institution/department attendance metrics.
    Filters:
      - ?course_offering_id=<int>
      - ?department_id=<str>
      - ?start_date=YYYY-MM-DD
      - ?end_date=YYYY-MM-DD
      - ?threshold=<float> (e.g. 75.0)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        course_offering_id = request.query_params.get("course_offering_id")
        department_id = request.query_params.get("department_id")
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        threshold_str = request.query_params.get("threshold")

        if course_offering_id:
            try:
                course_offering_id = int(course_offering_id)
            except ValueError:
                raise ValidationError({"course_offering_id": "course_offering_id must be an integer."})

        start_date, end_date = None, None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError({"start_date": "start_date must follow format 'YYYY-MM-DD'."})

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError({"end_date": "end_date must follow format 'YYYY-MM-DD'."})

        threshold = None
        if threshold_str:
            try:
                threshold = float(threshold_str)
            except ValueError:
                raise ValidationError({"threshold": "threshold must be a valid number (e.g., 75.0)."})

        data = ReportService.get_attendance_report(
            user=request.user,
            course_offering_id=course_offering_id,
            department_id=department_id,
            start_date=start_date,
            end_date=end_date,
            threshold=threshold,
        )
        return Response(data, status=status.HTTP_200_OK)


class ReportExportView(APIView):
    """
    GET /api/reports/export/
    Downloads report data as CSV or JSON.
    Parameters:
      - type=admin_overview | admin_students | department | course | attendance (required)
      - format=csv | json (defaults to csv)
      - Filter parameters matching the specific report type
    """

    permission_classes = [IsAuthenticated]
    renderer_classes = [CSVRenderer, JSONRenderer]

    def get(self, request):
        report_type = request.query_params.get("type")
        if not report_type:
            raise ValidationError(
                {"type": "Report type is required. Allowed types: 'admin_overview', 'admin_students', 'department', 'course', 'attendance'."}
            )

        export_format = request.query_params.get("format", "csv")

        # Extract filters
        params = {}
        for key in ["term_id", "department_id", "course_offering_id", "admission_year", "current_semester", "is_active", "search", "start_date", "end_date", "threshold"]:
            val = request.query_params.get(key)
            if val is not None:
                params[key] = val

        content, content_type, filename = ReportService.generate_export(
            user=request.user,
            report_type=report_type,
            export_format=export_format,
            **params,
        )

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
