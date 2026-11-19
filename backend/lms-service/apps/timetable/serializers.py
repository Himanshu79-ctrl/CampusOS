"""
Serializers for Timetable & Calendar Management in CampusOS LMS.
Implements data validation and serialization for timetable slots and calendar events (SRS Section 3.E).
"""

from rest_framework import serializers
from .models import CalendarEvent, CalendarEventType, ClassType, DayOfWeek, TimetableEntry


class TimetableEntrySerializer(serializers.ModelSerializer):
    """
    Read serializer for a TimetableEntry.
    Includes course and academic term contextual fields.
    """

    course_id = serializers.CharField(source="course_offering.course_id", read_only=True)
    section = serializers.CharField(source="course_offering.section", read_only=True)
    academic_term = serializers.CharField(source="course_offering.academic_term.name", read_only=True)
    academic_term_id = serializers.IntegerField(source="course_offering.academic_term_id", read_only=True)

    class Meta:
        model = TimetableEntry
        fields = [
            "id",
            "course_offering",
            "course_id",
            "section",
            "academic_term",
            "academic_term_id",
            "faculty_id",
            "day_of_week",
            "start_time",
            "end_time",
            "room",
            "building",
            "entry_type",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "course_offering",
            "course_id",
            "section",
            "academic_term",
            "academic_term_id",
            "created_at",
            "updated_at",
        ]


class TimetableEntryCreateUpdateSerializer(serializers.Serializer):
    """
    Serializer for creating and updating timetable class slots.
    """

    day_of_week = serializers.ChoiceField(choices=DayOfWeek.choices)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    room = serializers.CharField(max_length=64)
    building = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    entry_type = serializers.ChoiceField(choices=ClassType.choices, required=False, default=ClassType.LECTURE)
    faculty_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    is_active = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "Class end time must be strictly after the start time."})
        return attrs


class CalendarEventSerializer(serializers.ModelSerializer):
    """
    Serializer for CalendarEvent records.
    """

    course_id = serializers.CharField(source="course_offering.course_id", read_only=True, default=None)
    section = serializers.CharField(source="course_offering.section", read_only=True, default=None)
    academic_term_name = serializers.CharField(source="academic_term.name", read_only=True, default=None)

    class Meta:
        model = CalendarEvent
        fields = [
            "id",
            "title",
            "description",
            "event_type",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "academic_term",
            "academic_term_name",
            "course_offering",
            "course_id",
            "section",
            "created_by_user_id",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "course_id",
            "section",
            "academic_term_name",
            "created_by_user_id",
            "created_at",
            "updated_at",
        ]


class CalendarEventCreateUpdateSerializer(serializers.Serializer):
    """
    Serializer for creating and updating calendar events.
    """

    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    event_type = serializers.ChoiceField(choices=CalendarEventType.choices, required=False, default=CalendarEventType.EVENT)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    start_time = serializers.TimeField(required=False, allow_null=True, default=None)
    end_time = serializers.TimeField(required=False, allow_null=True, default=None)
    academic_term_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    course_offering_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    is_published = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "Event end date cannot precede start date."})

        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")
        if start_date and end_date and start_date == end_date and start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError({"end_time": "Event end time must be after the start time on the same date."})

        return attrs

