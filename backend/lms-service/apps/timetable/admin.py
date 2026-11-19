from django.contrib import admin
from .models import TimetableEntry, CalendarEvent


@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "course_offering", "faculty_id", "day_of_week", "start_time", "end_time", "room", "building", "is_active")
    list_filter = ("day_of_week", "is_active", "entry_type")
    search_fields = ("room", "building", "faculty_id", "course_offering__course_id")


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "event_type", "start_date", "end_date", "academic_term", "course_offering", "is_published")
    list_filter = ("event_type", "is_published", "start_date")
    search_fields = ("title", "description", "created_by_user_id")

