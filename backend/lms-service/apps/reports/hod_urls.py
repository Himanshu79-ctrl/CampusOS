"""
HOD reports URL configuration for CampusOS LMS (mounted at /api/hod/reports/).
"""

from django.urls import path
from .views import DepartmentReportView

urlpatterns = [
    path("department/", DepartmentReportView.as_view(), name="hod-department"),
]

