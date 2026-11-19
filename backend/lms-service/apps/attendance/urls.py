"""
URL configuration for Attendance Management in CampusOS LMS (SRS Section 3.D).
"""

from django.urls import path
from .views import (
    CourseOfferingAttendanceSessionsView,
    AttendanceSessionDetailView,
    AttendanceSessionMarkView,
    AttendanceRecordDetailView,
    CourseAttendanceReportView,
    StudentMyAttendanceSummaryView,
    StudentMyAttendanceHistoryView,
)

app_name = "attendance"

urlpatterns = [
    # Course offering sessions & reporting
    path("offerings/<int:offering_id>/sessions/", CourseOfferingAttendanceSessionsView.as_view(), name="offering-sessions"),
    path("offerings/<int:offering_id>/report/", CourseAttendanceReportView.as_view(), name="offering-report"),

    # Attendance session detail, update, delete, and bulk marking
    path("sessions/<int:pk>/", AttendanceSessionDetailView.as_view(), name="session-detail"),
    path("sessions/<int:pk>/mark/", AttendanceSessionMarkView.as_view(), name="session-mark"),

    # Individual record detail and audit correction
    path("records/<int:pk>/", AttendanceRecordDetailView.as_view(), name="record-detail"),

    # Student personal attendance views
    path("my-summary/", StudentMyAttendanceSummaryView.as_view(), name="my-summary"),
    path("my-history/", StudentMyAttendanceHistoryView.as_view(), name="my-history"),
]

