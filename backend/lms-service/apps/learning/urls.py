"""
URL routing for Course Content & Learning Management in CampusOS LMS.
"""

from django.urls import path
from .views import (
    CourseOfferingModulesView,
    CourseModuleDetailView,
    CourseModulePublishView,
    ModuleLessonsView,
    ModuleResourcesView,
    LessonDetailView,
    LessonPublishView,
    LessonProgressView,
    LessonResourcesView,
    LearningResourceDetailView,
)

app_name = "learning"

urlpatterns = [
    # Offering module overview & creation
    path("offerings/<int:offering_id>/modules/", CourseOfferingModulesView.as_view(), name="offering-modules"),

    # Module details, update, delete, publish
    path("modules/<int:pk>/", CourseModuleDetailView.as_view(), name="module-detail"),
    path("modules/<int:pk>/publish/", CourseModulePublishView.as_view(), name="module-publish"),
    path("modules/<int:module_id>/lessons/", ModuleLessonsView.as_view(), name="module-lessons"),
    path("modules/<int:module_id>/resources/", ModuleResourcesView.as_view(), name="module-resources"),

    # Lesson details, update, delete, publish, progress
    path("lessons/<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
    path("lessons/<int:pk>/publish/", LessonPublishView.as_view(), name="lesson-publish"),
    path("lessons/<int:pk>/progress/", LessonProgressView.as_view(), name="lesson-progress"),
    path("lessons/<int:lesson_id>/resources/", LessonResourcesView.as_view(), name="lesson-resources"),

    # Learning Resources details & deletion
    path("resources/<int:pk>/", LearningResourceDetailView.as_view(), name="resource-detail"),
]

