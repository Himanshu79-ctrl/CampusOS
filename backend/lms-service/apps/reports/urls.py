"""
Main URL configuration for Reports & Analytics in CampusOS LMS.
"""

from django.urls import path
from .views import (
    AdminOverviewReportView,
    AdminStudentsReportView,
    AttendanceReportView,
    CourseReportView,
    DepartmentReportView,
    ReportExportView,
)

app_name = "reports"

urlpatterns = [
    # Top-level reports endpoints
    path("attendance/", AttendanceReportView.as_view(), name="attendance-report"),
    path("export/", ReportExportView.as_view(), name="report-export"),
    # Aliased sub-paths under /api/reports/
    path("admin/overview/", AdminOverviewReportView.as_view(), name="reports-admin-overview"),
    path("admin/students/", AdminStudentsReportView.as_view(), name="reports-admin-students"),
    path("hod/department/", DepartmentReportView.as_view(), name="reports-hod-department"),
    path("faculty/course/<int:course_offering_id>/", CourseReportView.as_view(), name="reports-faculty-course"),
]

