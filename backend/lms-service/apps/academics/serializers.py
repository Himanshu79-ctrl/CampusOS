"""
Serializers for Academic Terms, Course Offerings, and Enrollments in CampusOS LMS.
"""

from rest_framework import serializers

from .models import (
    AcademicTerm,
    CourseOffering,
    Enrollment,
    EnrollmentStatus,
    OfferingStatus,
    TermStatus,
)
from apps.students.models import StudentProfile


class AcademicTermSerializer(serializers.ModelSerializer):
    """
    Serializer for AcademicTerm model.
    """

    class Meta:
        model = AcademicTerm
        fields = [
            "id",
            "name",
            "academic_year",
            "term_number",
            "start_date",
            "end_date",
            "status",
            "is_enrollment_open",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        start_date = attrs.get("start_date", getattr(instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(instance, "end_date", None))
        status_val = attrs.get("status", getattr(instance, "status", None))
        is_open = attrs.get("is_enrollment_open", getattr(instance, "is_enrollment_open", False))

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError({"end_date": "End date must be strictly after the start date."})

        if status_val == TermStatus.COMPLETED and is_open:
            raise serializers.ValidationError(
                {"is_enrollment_open": "Enrollment cannot be open for a completed academic term."}
            )

        return attrs


class CourseOfferingSerializer(serializers.ModelSerializer):
    """
    Serializer for CourseOffering with computed seat availability and decoded
    course & department details resolved from Admin service master catalog.
    """

    academic_term_name = serializers.CharField(source="academic_term.name", read_only=True)
    academic_term_status = serializers.CharField(source="academic_term.status", read_only=True)
    academic_year = serializers.CharField(source="academic_term.academic_year", read_only=True)
    enrolled_count = serializers.SerializerMethodField()
    available_seats = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()
    course_code = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    department_code = serializers.SerializerMethodField()

    class Meta:
        model = CourseOffering
        fields = [
            "id",
            "course_id",
            "course_name",
            "course_code",
            "faculty_id",
            "department_id",
            "department_name",
            "department_code",
            "academic_term",
            "academic_term_name",
            "academic_term_status",
            "academic_year",
            "section",
            "capacity",
            "status",
            "enrolled_count",
            "available_seats",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "course_name",
            "course_code",
            "department_name",
            "department_code",
            "created_at",
            "updated_at",
        ]

    def get_enrolled_count(self, obj) -> int:
        return obj.enrollments.filter(status=EnrollmentStatus.ENROLLED).count()

    def get_available_seats(self, obj) -> int:
        enrolled = self.get_enrolled_count(obj)
        return max(0, obj.capacity - enrolled)

    def get_course_name(self, obj) -> str:
        from .admin_client import AdminServiceClient
        client = AdminServiceClient()
        course = client.get_course(obj.course_id)
        if course and isinstance(course, dict):
            return course.get("name", "")
        return ""

    def get_course_code(self, obj) -> str:
        from .admin_client import AdminServiceClient
        client = AdminServiceClient()
        course = client.get_course(obj.course_id)
        if course and isinstance(course, dict) and course.get("code"):
            return course.get("code")
        return obj.course_id

    def get_department_name(self, obj) -> str:
        from .admin_client import AdminServiceClient
        client = AdminServiceClient()
        # 1. Try resolving directly from department_id
        dept = client.get_department(obj.department_id)
        if dept and isinstance(dept, dict) and dept.get("name"):
            return dept.get("name")
        # 2. Try resolving via course.department if course is populated
        course = client.get_course(obj.course_id)
        if course and isinstance(course, dict):
            c_dept = course.get("department")
            if isinstance(c_dept, dict) and c_dept.get("name"):
                return c_dept.get("name")
        return ""

    def get_department_code(self, obj) -> str:
        from .admin_client import AdminServiceClient
        client = AdminServiceClient()
        dept = client.get_department(obj.department_id)
        if dept and isinstance(dept, dict) and dept.get("code"):
            return dept.get("code")
        course = client.get_course(obj.course_id)
        if course and isinstance(course, dict):
            c_dept = course.get("department")
            if isinstance(c_dept, dict) and c_dept.get("code"):
                return c_dept.get("code")
        return obj.department_id

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be greater than zero.")
        return value

    def validate_course_id(self, value):
        from .admin_client import AdminServiceClient
        if not AdminServiceClient.is_valid_format(value):
            raise serializers.ValidationError(
                "Invalid course_id format. Must be a non-empty string of up to 64 characters."
            )
        return value.strip()

    def validate_faculty_id(self, value):
        from .admin_client import AdminServiceClient
        if not AdminServiceClient.is_valid_format(value):
            raise serializers.ValidationError(
                "Invalid faculty_id format. Must be a non-empty string of up to 64 characters."
            )
        return value.strip()

    def validate_department_id(self, value):
        from .admin_client import AdminServiceClient
        if not AdminServiceClient.is_valid_format(value):
            raise serializers.ValidationError(
                "Invalid department_id format. Must be a non-empty string of up to 64 characters."
            )
        return value.strip()


class CourseOfferingListSerializer(CourseOfferingSerializer):
    """
    Lightweight list serializer for catalog course browsing.
    """

    class Meta(CourseOfferingSerializer.Meta):
        fields = [
            "id",
            "course_id",
            "course_name",
            "course_code",
            "faculty_id",
            "department_id",
            "department_name",
            "department_code",
            "academic_term",
            "academic_term_name",
            "academic_term_status",
            "academic_year",
            "section",
            "capacity",
            "status",
            "enrolled_count",
            "available_seats",
        ]


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Standard serializer for Enrollment records.
    """

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "student",
            "course_offering",
            "status",
            "enrolled_at",
            "dropped_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "enrolled_at", "dropped_at", "created_at", "updated_at"]


class EnrollmentDetailSerializer(serializers.ModelSerializer):
    """
    Detailed enrollment serializer with nested course offering & term info.
    """

    course_id = serializers.CharField(source="course_offering.course_id", read_only=True)
    faculty_id = serializers.CharField(source="course_offering.faculty_id", read_only=True)
    department_id = serializers.CharField(source="course_offering.department_id", read_only=True)
    section = serializers.CharField(source="course_offering.section", read_only=True)
    term_name = serializers.CharField(source="course_offering.academic_term.name", read_only=True)
    academic_term_name = serializers.CharField(source="course_offering.academic_term.name", read_only=True)
    academic_term = serializers.IntegerField(source="course_offering.academic_term.id", read_only=True)
    academic_year = serializers.CharField(source="course_offering.academic_term.academic_year", read_only=True)
    student_registration_number = serializers.CharField(
        source="student.registration_number", read_only=True
    )

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "student_id",
            "student_registration_number",
            "course_offering_id",
            "course_id",
            "faculty_id",
            "department_id",
            "section",
            "term_name",
            "academic_term_name",
            "academic_term",
            "academic_year",
            "status",
            "enrolled_at",
            "dropped_at",
        ]


class RosterStudentSerializer(serializers.Serializer):
    """
    Roster serializer for faculty viewing students enrolled in their offering.
    """

    enrollment_id = serializers.IntegerField(source="id")
    student_id = serializers.IntegerField(source="student.id")
    registration_number = serializers.CharField(source="student.registration_number")
    admission_year = serializers.IntegerField(source="student.admission_year")
    current_semester = serializers.IntegerField(source="student.current_semester")
    enrolled_at = serializers.DateTimeField()
    status = serializers.CharField()


