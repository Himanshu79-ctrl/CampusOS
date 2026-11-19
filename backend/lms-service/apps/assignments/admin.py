from django.contrib import admin
from .models import Assignment, AssignmentSubmission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "course_offering",
        "due_date",
        "max_marks",
        "is_published",
        "allow_late_submissions",
        "allow_resubmissions",
    )
    list_filter = ("is_published", "allow_late_submissions", "allow_resubmissions")
    search_fields = ("title", "description", "instructions")


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "assignment",
        "student",
        "submission_number",
        "status",
        "marks_obtained",
        "is_late",
        "submitted_at",
    )
    list_filter = ("status", "is_late")
    search_fields = ("student__registration_number", "assignment__title", "feedback")

