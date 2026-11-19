"""
Serializers for Assignment Management & Student Submissions in CampusOS LMS.
"""

from decimal import Decimal
from rest_framework import serializers
from .models import Assignment, AssignmentSubmission, SubmissionStatus
from apps.students.models import StudentProfile


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """
    Serializer for AssignmentSubmission records, including evaluation marks and feedback.
    """

    student_registration_number = serializers.CharField(source="student.registration_number", read_only=True)
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    max_marks = serializers.DecimalField(source="assignment.max_marks", max_digits=6, decimal_places=2, read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = [
            "id",
            "assignment",
            "assignment_title",
            "student",
            "student_registration_number",
            "submission_text",
            "submission_file",
            "file_size_bytes",
            "file_mime_type",
            "submission_number",
            "submitted_at",
            "is_late",
            "status",
            "marks_obtained",
            "max_marks",
            "feedback",
            "graded_by_faculty_id",
            "graded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "student_registration_number",
            "assignment_title",
            "max_marks",
            "file_size_bytes",
            "file_mime_type",
            "submission_number",
            "submitted_at",
            "is_late",
            "status",
            "marks_obtained",
            "feedback",
            "graded_by_faculty_id",
            "graded_at",
            "created_at",
            "updated_at",
        ]


class AssignmentListSerializer(serializers.ModelSerializer):
    """
    Summary view of assignments for a course offering.
    Includes contextual student submission status or instructor submission totals.
    """

    submissions_count = serializers.SerializerMethodField()
    graded_count = serializers.SerializerMethodField()
    my_submission = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            "id",
            "course_offering",
            "module",
            "title",
            "description",
            "due_date",
            "max_marks",
            "is_published",
            "allow_late_submissions",
            "allow_resubmissions",
            "submissions_count",
            "graded_count",
            "my_submission",
            "created_at",
        ]

    def get_submissions_count(self, obj) -> int:
        request = self.context.get("request")
        if request and not getattr(request.user, "is_student", False):
            return obj.submissions.count()
        return 0

    def get_graded_count(self, obj) -> int:
        request = self.context.get("request")
        if request and not getattr(request.user, "is_student", False):
            return obj.submissions.filter(status=SubmissionStatus.GRADED).count()
        return 0

    def get_my_submission(self, obj):
        request = self.context.get("request")
        if request and getattr(request.user, "is_student", False):
            profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
            if profile:
                sub = obj.submissions.filter(student=profile).first()
                if sub:
                    return {
                        "id": sub.id,
                        "status": sub.status,
                        "submitted_at": sub.submitted_at,
                        "is_late": sub.is_late,
                        "marks_obtained": sub.marks_obtained,
                        "feedback": sub.feedback,
                    }
        return None


class AssignmentDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for an assignment, including full instructions and student submission.
    """

    course_offering_id = serializers.IntegerField(source="course_offering.id", read_only=True)
    my_submission = serializers.SerializerMethodField()
    submissions_count = serializers.SerializerMethodField()
    graded_count = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            "id",
            "course_offering",
            "course_offering_id",
            "module",
            "title",
            "description",
            "instructions",
            "max_marks",
            "due_date",
            "allow_late_submissions",
            "late_submission_deadline",
            "allow_resubmissions",
            "max_resubmissions",
            "is_published",
            "attachment",
            "submissions_count",
            "graded_count",
            "my_submission",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "course_offering_id", "created_at", "updated_at"]

    def get_my_submission(self, obj):
        request = self.context.get("request")
        if request and getattr(request.user, "is_student", False):
            profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
            if profile:
                sub = obj.submissions.filter(student=profile).first()
                if sub:
                    return AssignmentSubmissionSerializer(sub, context=self.context).data
        return None

    def get_submissions_count(self, obj) -> int:
        request = self.context.get("request")
        if request and not getattr(request.user, "is_student", False):
            return obj.submissions.count()
        return 0

    def get_graded_count(self, obj) -> int:
        request = self.context.get("request")
        if request and not getattr(request.user, "is_student", False):
            return obj.submissions.filter(status=SubmissionStatus.GRADED).count()
        return 0


class AssignmentCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating assignments (Faculty/Admin only).
    """

    class Meta:
        model = Assignment
        fields = [
            "id",
            "course_offering",
            "module",
            "title",
            "description",
            "instructions",
            "max_marks",
            "due_date",
            "allow_late_submissions",
            "late_submission_deadline",
            "allow_resubmissions",
            "max_resubmissions",
            "is_published",
            "attachment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        if instance and "course_offering" in attrs:
            attrs.pop("course_offering")

        due_date = attrs.get("due_date", getattr(instance, "due_date", None))
        allow_late = attrs.get("allow_late_submissions", getattr(instance, "allow_late_submissions", False))
        late_deadline = attrs.get("late_submission_deadline", getattr(instance, "late_submission_deadline", None))
        max_marks = attrs.get("max_marks", getattr(instance, "max_marks", None))

        if max_marks is not None and max_marks <= Decimal("0.00"):
            raise serializers.ValidationError({"max_marks": "Maximum marks must be greater than zero."})

        if allow_late and late_deadline and due_date:
            if late_deadline <= due_date:
                raise serializers.ValidationError(
                    {"late_submission_deadline": "Late submission deadline must be strictly after the due date."}
                )

        return attrs


class SubmissionCreateSerializer(serializers.Serializer):
    """
    Serializer for student submitting assignment content.
    Accepts text and/or an uploaded file.
    """

    submission_text = serializers.CharField(required=False, allow_blank=True, default="")
    submission_file = serializers.FileField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        text = attrs.get("submission_text", "").strip()
        file_obj = attrs.get("submission_file")
        if not text and not file_obj:
            raise serializers.ValidationError("A submission must include either text content or an uploaded file.")
        return attrs


class SubmissionGradeSerializer(serializers.Serializer):
    """
    Serializer for faculty evaluating and grading a student submission.
    """

    marks_obtained = serializers.DecimalField(max_digits=6, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_marks_obtained(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Marks obtained cannot be negative.")
        return value

