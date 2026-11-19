from django.contrib import admin
from .models import CourseModule, Lesson, LearningResource, LessonProgress


@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "course_offering", "order", "is_published", "created_at")
    list_filter = ("is_published", "course_offering")
    search_fields = ("title", "description")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "module", "order", "is_published", "created_at")
    list_filter = ("is_published", "module")
    search_fields = ("title", "content")


@admin.register(LearningResource)
class LearningResourceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "resource_type", "module", "lesson", "order", "is_published")
    list_filter = ("resource_type", "is_published")
    search_fields = ("title", "description", "external_url")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "lesson", "is_completed", "completed_at")
    list_filter = ("is_completed",)
    search_fields = ("student__registration_number", "lesson__title")

