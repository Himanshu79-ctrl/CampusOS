"""
URL configuration for Notifications & Announcements in CampusOS LMS.
"""

from django.urls import path
from .views import (
    AnnouncementDetailView,
    AnnouncementListCreateView,
    AnnouncementPublishToggleView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
)

app_name = "notifications"

urlpatterns = [
    # Notification endpoints
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="notification-unread-count"),
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("mark-all-read/", NotificationMarkAllReadView.as_view(), name="notification-mark-all-read"),
    # Announcement endpoints
    path("announcements/", AnnouncementListCreateView.as_view(), name="announcement-list-create"),
    path("announcements/<int:pk>/", AnnouncementDetailView.as_view(), name="announcement-detail"),
    path("announcements/<int:pk>/publish/", AnnouncementPublishToggleView.as_view(), name="announcement-publish"),
]

