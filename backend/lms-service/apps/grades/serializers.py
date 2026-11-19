"""
Serializers for Grades & Academic Results in CampusOS LMS (SRS Section 3.F).
"""

from decimal import Decimal
from rest_framework import serializers
from .models import FinalCourseGrade, GradeItem, GradeItemType, GradeRecord


class GradeItemSerializer(serializers.ModelSerializer):
    """
    Serializer for assessment components (GradeItems).
    """

    class Meta:
        model = GradeItem
        fields = [
            "id",
            "course_offering",
            "name",
            "item_type",
            "max_marks",
            "weightage_percentage",
            "assignment",
            "external_exam_id",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "course_offering", "created_at", "updated_at"]


class GradeItemCreateUpdateSerializer(serializers.Serializer):
    """
    Serializer for creating and updating assessment components.
    """

    name = serializers.CharField(max_length=255)
    item_type = serializers.ChoiceField(choices=GradeItemType.choices, default=GradeItemType.ASSIGNMENT)
    max_marks = serializers.DecimalField(max_digits=6, decimal_places=2, default=Decimal("100.00"))
    weightage_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True, default=None)
    assignment_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    external_exam_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    is_published = serializers.BooleanField(required=False, default=False)

    def validate_max_marks(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Maximum marks must be greater than zero.")
        return value

    def validate_weightage_percentage(self, value):
        if value is not None and (value < Decimal("0.00") or value > Decimal("100.00")):
            raise serializers.ValidationError("Weightage percentage must be between 0 and 100.")
        return value


class GradeRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for student grade records.
    """

    student_registration_number = serializers.CharField(source="student.registration_number", read_only=True)
    grade_item_name = serializers.CharField(source="grade_item.name", read_only=True)
    max_marks = serializers.DecimalField(source="grade_item.max_marks", max_digits=6, decimal_places=2, read_only=True)
    course_offering_id = serializers.IntegerField(source="grade_item.course_offering_id", read_only=True)

    class Meta:
        model = GradeRecord
        fields = [
            "id",
            "grade_item",
            "grade_item_name",
            "course_offering_id",
            "student",
            "student_registration_number",
            "marks_obtained",
            "max_marks",
            "letter_grade",
            "feedback",
            "is_published",
            "graded_by_faculty_id",
            "graded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "grade_item",
            "grade_item_name",
            "course_offering_id",
            "student",
            "student_registration_number",
            "max_marks",
            "graded_by_faculty_id",
            "graded_at",
            "created_at",
            "updated_at",
        ]


class GradeRecordInputSerializer(serializers.Serializer):
    """
    Serializer for faculty entering or updating an individual student's marks.
    """

    student_id = serializers.IntegerField()
    marks_obtained = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    letter_grade = serializers.CharField(max_length=8, required=False, allow_blank=True, default="")
    feedback = serializers.CharField(required=False, allow_blank=True, default="")
    is_published = serializers.BooleanField(required=False, allow_null=True, default=None)

    def validate_marks_obtained(self, value):
        if value is not None and value < Decimal("0.00"):
            raise serializers.ValidationError("Marks obtained cannot be negative.")
        return value


class GradeBulkInputSerializer(serializers.Serializer):
    """
    Serializer for bulk submitting multiple students' grades for a GradeItem.
    """

    records = GradeRecordInputSerializer(many=True)

    def validate_records(self, value):
        if not value:
            raise serializers.ValidationError("At least one grade record is required.")
        return value


class FinalCourseGradeSerializer(serializers.ModelSerializer):
    """
    Serializer for final published course results.
    """

    student_registration_number = serializers.CharField(source="student.registration_number", read_only=True)

    class Meta:
        model = FinalCourseGrade
        fields = [
            "id",
            "course_offering",
            "student",
            "student_registration_number",
            "total_marks_obtained",
            "total_max_marks",
            "percentage",
            "final_letter_grade",
            "feedback",
            "is_published",
            "published_at",
            "graded_by_faculty_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "course_offering",
            "student",
            "student_registration_number",
            "published_at",
            "graded_by_faculty_id",
            "created_at",
            "updated_at",
        ]


class FinalCourseGradeInputSerializer(serializers.Serializer):
    """
    Serializer for faculty entering final course grade entries.
    """

    student_id = serializers.IntegerField()
    final_letter_grade = serializers.CharField(max_length=8, required=False, allow_blank=True, default="")
    total_marks_obtained = serializers.DecimalField(max_digits=7, decimal_places=2, required=False, allow_null=True)
    total_max_marks = serializers.DecimalField(max_digits=7, decimal_places=2, required=False, allow_null=True)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    feedback = serializers.CharField(required=False, allow_blank=True, default="")


class FinalGradeBulkPublishSerializer(serializers.Serializer):
    """
    Serializer for publishing final course grades.
    """

    grades = FinalCourseGradeInputSerializer(many=True, required=False, default=list)
