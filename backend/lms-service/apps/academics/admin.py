from django.contrib import admin
from apps.academics.models import AcademicTerm, CourseOffering, Enrollment


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_year", "term_number", "start_date", "end_date", "status", "is_enrollment_open")
    list_filter = ("status", "academic_year", "is_enrollment_open")
    search_fields = ("name", "academic_year")


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = ("course_id", "section", "academic_term", "faculty_id", "department_id", "capacity", "status")
    list_filter = ("status", "academic_term", "department_id")
    search_fields = ("course_id", "faculty_id", "section")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course_offering", "status", "enrolled_at", "dropped_at")
    list_filter = ("status", "course_offering__academic_term")
    search_fields = ("student__registration_number", "course_offering__course_id")

