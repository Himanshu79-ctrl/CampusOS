"""
Admin reports URL configuration for CampusOS LMS (mounted at /api/admin/reports/).
"""

from django.urls import path
from .views import AdminOverviewReportView, AdminStudentsReportView

urlpatterns = [
    path("overview/", AdminOverviewReportView.as_view(), name="admin-overview"),
    path("students/", AdminStudentsReportView.as_view(), name="admin-students"),
]

