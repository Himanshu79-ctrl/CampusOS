"""
Faculty reports URL configuration for CampusOS LMS (mounted at /api/faculty/reports/).
"""

from django.urls import path
from .views import CourseReportView

urlpatterns = [
    path("course/<int:course_offering_id>/", CourseReportView.as_view(), name="faculty-course"),
]

