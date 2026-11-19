"""
URL patterns for apps.academics.
"""

from django.urls import path
from .views import (
    AcademicTermActivateView,
    AcademicTermCompleteView,
    AcademicTermDetailView,
    AcademicTermEnrollmentWindowView,
    AcademicTermListCreateView,
    CourseOfferingDetailView,
    CourseOfferingListCreateView,
    CourseOfferingRosterView,
    CurrentAcademicTermView,
    DropStudentView,
    EnrollmentListView,
    EnrollStudentView,
)

app_name = "academics"

urlpatterns = [
    # Academic Terms
    path("terms/", AcademicTermListCreateView.as_view(), name="term-list-create"),
    path("terms/current/", CurrentAcademicTermView.as_view(), name="term-current"),
    path("terms/<int:pk>/", AcademicTermDetailView.as_view(), name="term-detail"),
    path("terms/<int:pk>/activate/", AcademicTermActivateView.as_view(), name="term-activate"),
    path("terms/<int:pk>/complete/", AcademicTermCompleteView.as_view(), name="term-complete"),
    path(
        "terms/<int:pk>/enrollment-window/",
        AcademicTermEnrollmentWindowView.as_view(),
        name="term-enrollment-window",
    ),
    # Course Offerings
    path("offerings/", CourseOfferingListCreateView.as_view(), name="offering-list-create"),
    path("offerings/<int:pk>/", CourseOfferingDetailView.as_view(), name="offering-detail"),
    path("offerings/<int:pk>/students/", CourseOfferingRosterView.as_view(), name="offering-roster"),
    path("offerings/<int:pk>/enroll/", EnrollStudentView.as_view(), name="offering-enroll"),
    path("offerings/<int:pk>/drop/", DropStudentView.as_view(), name="offering-drop"),
    # Enrollments
    path("enrollments/", EnrollmentListView.as_view(), name="enrollment-list"),
]

