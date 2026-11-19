"""
URL patterns for apps.students.
"""

from django.urls import path
from apps.students.views import (
    CurrentStudentEnrollmentsView,
    CurrentStudentProfileView,
    StudentProfileCreateView,
    StudentProfileDetailView,
    UnifiedStudentProvisionView,
)

app_name = "students"

urlpatterns = [
    path("unified-provision/", UnifiedStudentProvisionView.as_view(), name="unified-provision"),
    path("profile/", StudentProfileCreateView.as_view(), name="profile-create"),
    path("profile/me/", CurrentStudentProfileView.as_view(), name="profile-me"),
    path("profile/me/enrollments/", CurrentStudentEnrollmentsView.as_view(), name="profile-me-enrollments"),
    path("profile/<int:pk>/", StudentProfileDetailView.as_view(), name="profile-detail"),
]

