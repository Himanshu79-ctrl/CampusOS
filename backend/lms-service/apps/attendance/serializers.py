"""
Serializers for Attendance Management in CampusOS LMS.
Implements data validation and response formatting for sessions, records, corrections,
and student summaries (SRS Section 3.D).
"""

from rest_framework import serializers
from .models import AttendanceRecord, AttendanceSession, AttendanceStatus


class AttendanceRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for individual attendance records.
    """

    student_registration_number = serializers.CharField(source="student.registration_number", read_only=True)
    student_auth_user_id = serializers.CharField(source="student.auth_user_id", read_only=True)
    session_id = serializers.IntegerField(source="session.id", read_only=True)
    session_date = serializers.DateField(source="session.session_date", read_only=True)
    session_title = serializers.CharField(source="session.title", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "session_id",
            "session_date",
            "session_title",
            "student",
            "student_registration_number",
            "student_auth_user_id",
            "status",
            "remarks",
            "audit_reason",
            "recorded_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "session_id",
            "session_date",
            "session_title",
            "student",
            "student_registration_number",
            "student_auth_user_id",
            "recorded_by_user_id",
            "created_at",
            "updated_at",
        ]


class AttendanceRecordInputSerializer(serializers.Serializer):
    """
    Input serializer for marking or updating a student's attendance within a session.
    """

    student_id = serializers.IntegerField(required=True)
    status = serializers.ChoiceField(choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    audit_reason = serializers.CharField(required=False, allow_blank=True, default="")


class AttendanceSessionListSerializer(serializers.ModelSerializer):
    """
    Summary view of attendance sessions for a course offering.
    """

    records_count = serializers.SerializerMethodField()
    present_count = serializers.SerializerMethodField()
    late_count = serializers.SerializerMethodField()
    absent_count = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = [
            "id",
            "course_offering",
            "session_date",
            "start_time",
            "end_time",
            "title",
            "description",
            "created_by_faculty_id",
            "records_count",
            "present_count",
            "late_count",
            "absent_count",
            "created_at",
            "updated_at",
        ]

    def get_records_count(self, obj) -> int:
        return obj.records.count()

    def get_present_count(self, obj) -> int:
        return obj.records.filter(status=AttendanceStatus.PRESENT).count()

    def get_late_count(self, obj) -> int:
        return obj.records.filter(status=AttendanceStatus.LATE).count()

    def get_absent_count(self, obj) -> int:
        return obj.records.filter(status=AttendanceStatus.ABSENT).count()


class AttendanceSessionDetailSerializer(serializers.ModelSerializer):
    """
    Detailed view of an attendance session including all student attendance records.
    """

    records = AttendanceRecordSerializer(many=True, read_only=True)
    records_count = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = [
            "id",
            "course_offering",
            "session_date",
            "start_time",
            "end_time",
            "title",
            "description",
            "created_by_faculty_id",
            "records_count",
            "records",
            "created_at",
            "updated_at",
        ]

    def get_records_count(self, obj) -> int:
        return obj.records.count()


class AttendanceSessionCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new attendance session.
    Optionally accepts a list of initial records to mark students atomically.
    Supports frontend aliases 'date' -> 'session_date' and 'topic' -> 'title'.
    """

    session_date = serializers.DateField(required=False)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    start_time = serializers.TimeField(required=False, allow_null=True, default=None)
    end_time = serializers.TimeField(required=False, allow_null=True, default=None)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    records = AttendanceRecordInputSerializer(many=True, required=False, default=list)

    def to_internal_value(self, data):
        mutable_data = data.copy() if hasattr(data, "copy") else dict(data)
        if "session_date" not in mutable_data and "date" in mutable_data:
            mutable_data["session_date"] = mutable_data["date"]
        if "title" not in mutable_data and "topic" in mutable_data:
            mutable_data["title"] = mutable_data["topic"]
        return super().to_internal_value(mutable_data)

    def validate(self, attrs):
        if not attrs.get("session_date"):
            raise serializers.ValidationError({"session_date": "Session date is required."})
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "Session end time must be after the start time."})
        return attrs


class AttendanceMarkBulkSerializer(serializers.Serializer):
    """
    Serializer for bulk marking or updating attendance records for an existing session.
    """

    records = AttendanceRecordInputSerializer(many=True, required=True)
    default_audit_reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_records(self, value):
        if not value:
            raise serializers.ValidationError("At least one attendance record is required.")
        return value


class AttendanceRecordCorrectionSerializer(serializers.Serializer):
    """
    Serializer for correcting an individual attendance record with a mandatory audit reason.
    """

    status = serializers.ChoiceField(choices=AttendanceStatus.choices, required=True)
    audit_reason = serializers.CharField(required=True, min_length=3, allow_blank=False)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class StudentAttendanceSummarySerializer(serializers.Serializer):
    """
    Serializer for subject-wise attendance percentages.
    """

    course_offering_id = serializers.IntegerField()
    course_id = serializers.CharField()
    section = serializers.CharField()
    academic_term = serializers.CharField()
    total_sessions = serializers.IntegerField()
    present_count = serializers.IntegerField()
    late_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    attended_count = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()


class StudentAttendanceHistorySerializer(serializers.ModelSerializer):
    """
    Chronological view of a student's personal attendance entries.
    """

    session_date = serializers.DateField(source="session.session_date", read_only=True)
    session_title = serializers.CharField(source="session.title", read_only=True)
    course_offering_id = serializers.IntegerField(source="session.course_offering_id", read_only=True)
    start_time = serializers.TimeField(source="session.start_time", read_only=True)
    end_time = serializers.TimeField(source="session.end_time", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "session_id",
            "session_date",
            "session_title",
            "course_offering_id",
            "start_time",
            "end_time",
            "status",
            "remarks",
            "audit_reason",
            "recorded_by_user_id",
            "updated_at",
        ]

