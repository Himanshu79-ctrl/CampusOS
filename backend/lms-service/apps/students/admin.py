from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("registration_number", "auth_user_id", "department_id", "current_semester", "is_active")
    list_filter = ("is_active", "department_id", "admission_year", "current_semester")
    search_fields = ("registration_number", "auth_user_id", "department_id")

