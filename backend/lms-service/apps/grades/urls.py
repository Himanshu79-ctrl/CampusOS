"""
URL configuration for Grades & Academic Results in CampusOS LMS (SRS Section 3.F).
"""

from django.urls import path
from .views import (
    CourseFinalGradesView,
    CourseGradebookView,
    CourseOfferingGradeItemsView,
    GradeItemBulkMarksView,
    GradeItemDetailView,
    GradeItemPublishView,
    GradeItemSyncAssignmentView,
    GradeItemSyncExamView,
    GradeRecordDetailView,
    StudentMyGradesView,
)

app_name = "grades"

urlpatterns = [
    # Course assessment components (GradeItems) and Gradebook matrix
    path("offerings/<int:offering_id>/items/", CourseOfferingGradeItemsView.as_view(), name="offering-grade-items"),
    path("offerings/<int:offering_id>/gradebook/", CourseGradebookView.as_view(), name="course-gradebook"),
    path("offerings/<int:offering_id>/final-results/", CourseFinalGradesView.as_view(), name="course-final-results"),

    # GradeItem management, publishing, bulk marking, and external sync
    path("items/<int:pk>/", GradeItemDetailView.as_view(), name="grade-item-detail"),
    path("items/<int:pk>/publish/", GradeItemPublishView.as_view(), name="grade-item-publish"),
    path("items/<int:pk>/marks/", GradeItemBulkMarksView.as_view(), name="grade-item-marks"),
    path("items/<int:pk>/sync-assignment/", GradeItemSyncAssignmentView.as_view(), name="grade-item-sync-assignment"),
    path("items/<int:pk>/sync-exam/", GradeItemSyncExamView.as_view(), name="grade-item-sync-exam"),

    # Individual student grade records
    path("records/<int:pk>/", GradeRecordDetailView.as_view(), name="grade-record-detail"),

    # Student personal grades & academic results
    path("my-grades/", StudentMyGradesView.as_view(), name="my-grades"),
]

