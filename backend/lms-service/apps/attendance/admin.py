from django.contrib import admin
from .models import AttendanceSession, AttendanceRecord


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    fields = ("student", "status", "remarks", "audit_reason", "recorded_by_user_id")


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "course_offering", "session_date", "title", "start_time", "end_time", "created_by_faculty_id")
    list_filter = ("session_date", "course_offering")
    search_fields = ("title", "description", "course_offering__course_id")
    inlines = [AttendanceRecordInline]


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "student", "status", "recorded_by_user_id", "updated_at")
    list_filter = ("status", "session__session_date", "session__course_offering")
    search_fields = ("student__registration_number", "session__title", "audit_reason")

