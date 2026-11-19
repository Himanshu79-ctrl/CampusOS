from django.contrib import admin
from .models import Announcement, Notification


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "scope", "audience_type", "author_user_id", "is_published", "published_at")
    list_filter = ("scope", "audience_type", "is_published")
    search_fields = ("title", "content", "author_user_id")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient_user_id", "title", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("recipient_user_id", "title", "message")

