"""
URL routing for Assignment Management & Student Submissions in CampusOS LMS.
"""

from django.urls import path
from .views import (
    CourseOfferingAssignmentsView,
    AssignmentDetailView,
    AssignmentPublishView,
    AssignmentSubmitView,
    StudentMySubmissionView,
    AssignmentSubmissionsListView,
    AssignmentSubmissionDetailView,
    AssignmentSubmissionGradeView,
)

app_name = "assignments"

urlpatterns = [
    # Course offering assignments overview & creation
    path("offerings/<int:offering_id>/", CourseOfferingAssignmentsView.as_view(), name="offering-assignments"),

    # Assignment detail, update, delete, publish
    path("<int:pk>/", AssignmentDetailView.as_view(), name="assignment-detail"),
    path("<int:pk>/publish/", AssignmentPublishView.as_view(), name="assignment-publish"),

    # Student submission & viewing personal submission
    path("<int:pk>/submit/", AssignmentSubmitView.as_view(), name="assignment-submit"),
    path("<int:pk>/my-submission/", StudentMySubmissionView.as_view(), name="assignment-my-submission"),

    # Instructor submissions list & grading
    path("<int:pk>/submissions/", AssignmentSubmissionsListView.as_view(), name="assignment-submissions-list"),
    path("submissions/<int:pk>/", AssignmentSubmissionDetailView.as_view(), name="submission-detail"),
    path("submissions/<int:pk>/grade/", AssignmentSubmissionGradeView.as_view(), name="submission-grade"),
]

