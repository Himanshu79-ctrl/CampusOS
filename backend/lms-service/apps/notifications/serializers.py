"""
Serializers for Notifications & Announcements in CampusOS LMS.
"""

from rest_framework import serializers
from apps.academics.models import CourseOffering
from .models import Announcement, AnnouncementScope, AudienceType, Notification, NotificationType


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing and reading persistent notifications.
    """

    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient_user_id",
            "title",
            "message",
            "notification_type",
            "is_read",
            "read_at",
            "data",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "recipient_user_id",
            "title",
            "message",
            "notification_type",
            "read_at",
            "data",
            "created_at",
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    """
    Serializer for creating, updating, and viewing Announcements.
    """

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "content",
            "author_user_id",
            "author_role",
            "scope",
            "audience_type",
            "course_offering",
            "department_id",
            "is_published",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "author_user_id",
            "author_role",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        scope = attrs.get("scope") or (self.instance.scope if self.instance else AnnouncementScope.INSTITUTION)
        course_offering = attrs.get("course_offering") if "course_offering" in attrs else (self.instance.course_offering if self.instance else None)
        department_id = attrs.get("department_id") if "department_id" in attrs else (self.instance.department_id if self.instance else None)

        if course_offering:
            scope = AnnouncementScope.COURSE
            attrs["scope"] = scope
        elif department_id:
            scope = AnnouncementScope.DEPARTMENT
            attrs["scope"] = scope

        if scope == AnnouncementScope.COURSE and not course_offering:
            raise serializers.ValidationError({"course_offering": "Course offering is required for course-level announcements."})
        if scope == AnnouncementScope.DEPARTMENT and not department_id:
            raise serializers.ValidationError({"department_id": "Department ID is required for department-level announcements."})
        if scope == AnnouncementScope.INSTITUTION:
            if course_offering:
                raise serializers.ValidationError({"course_offering": "Course offering must be empty for institution-wide announcements."})
            if department_id:
                raise serializers.ValidationError({"department_id": "Department ID must be empty for institution-wide announcements."})

        return attrs

