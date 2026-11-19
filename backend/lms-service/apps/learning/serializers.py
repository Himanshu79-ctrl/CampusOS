"""
Serializers for Learning & Course Content in CampusOS LMS.
Handles serialization and validation for CourseModules, Lessons, LearningResources, and Progress.
"""

from rest_framework import serializers
from .models import CourseModule, Lesson, LearningResource, LessonProgress, ResourceType
from .services import LearningContentService


class LearningResourceSerializer(serializers.ModelSerializer):
    """
    Serializer for LearningResource (files or external URLs).
    """

    is_published = serializers.BooleanField(default=True, required=False)

    class Meta:
        model = LearningResource
        fields = [
            "id",
            "title",
            "description",
            "resource_type",
            "module",
            "lesson",
            "file",
            "file_size_bytes",
            "file_mime_type",
            "external_url",
            "order",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "file_size_bytes", "file_mime_type", "created_at", "updated_at"]

    def validate(self, attrs):
        resource_type = attrs.get("resource_type", getattr(self.instance, "resource_type", ResourceType.FILE))
        file_obj = attrs.get("file", getattr(self.instance, "file", None))
        external_url = attrs.get("external_url", getattr(self.instance, "external_url", ""))

        if resource_type == ResourceType.FILE:
            if not file_obj and not self.instance:
                raise serializers.ValidationError({"file": "File is required when resource_type is FILE."})
            if "file" in attrs and file_obj:
                try:
                    size, mime = LearningContentService.validate_uploaded_resource_file(file_obj)
                    attrs["file_size_bytes"] = size
                    attrs["file_mime_type"] = mime
                except Exception as exc:
                    raise serializers.ValidationError({"file": str(exc)})

        elif resource_type == ResourceType.LINK:
            if not external_url:
                raise serializers.ValidationError({"external_url": "External URL is required when resource_type is LINK."})

        return attrs


class LessonListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing lessons within a module.
    """

    resources_count = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "description",
            "order",
            "is_published",
            "estimated_duration_minutes",
            "resources_count",
            "is_completed",
            "created_at",
        ]

    def get_resources_count(self, obj) -> int:
        request = self.context.get("request")
        if request and getattr(request.user, "is_student", False):
            return obj.resources.filter(is_published=True).count()
        return obj.resources.count()

    def get_is_completed(self, obj) -> bool:
        request = self.context.get("request")
        if request and getattr(request.user, "is_student", False):
            from apps.students.models import StudentProfile
            profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
            if profile:
                return LessonProgress.objects.filter(student=profile, lesson=obj, is_completed=True).exists()
        return False


class LessonDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a lesson, including content and child resources.
    """

    resources = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    module_title = serializers.CharField(source="module.title", read_only=True)
    course_offering_id = serializers.IntegerField(source="module.course_offering_id", read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "module",
            "module_title",
            "course_offering_id",
            "title",
            "description",
            "content",
            "order",
            "is_published",
            "estimated_duration_minutes",
            "resources",
            "is_completed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "module_title", "course_offering_id", "created_at", "updated_at"]

    def get_resources(self, obj):
        request = self.context.get("request")
        qs = obj.resources.all()
        if request and getattr(request.user, "is_student", False):
            qs = qs.filter(is_published=True)
        return LearningResourceSerializer(qs.order_by("order", "created_at"), many=True, context=self.context).data

    def get_is_completed(self, obj) -> bool:
        request = self.context.get("request")
        if request and getattr(request.user, "is_student", False):
            from apps.students.models import StudentProfile
            profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
            if profile:
                return LessonProgress.objects.filter(student=profile, lesson=obj, is_completed=True).exists()
        return False


class LessonCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating lessons.
    """

    class Meta:
        model = Lesson
        fields = [
            "id",
            "module",
            "title",
            "description",
            "content",
            "order",
            "is_published",
            "estimated_duration_minutes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CourseModuleSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a CourseModule, including nested lessons and module-level resources.
    """

    lessons = serializers.SerializerMethodField()
    resources = serializers.SerializerMethodField()
    course_offering_id = serializers.IntegerField(source="course_offering.id", read_only=True)

    class Meta:
        model = CourseModule
        fields = [
            "id",
            "course_offering",
            "course_offering_id",
            "title",
            "description",
            "order",
            "is_published",
            "lessons",
            "resources",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "course_offering_id", "created_at", "updated_at"]

    def get_lessons(self, obj):
        request = self.context.get("request")
        qs = obj.lessons.all()
        if request and getattr(request.user, "is_student", False):
            qs = qs.filter(is_published=True)
        return LessonListSerializer(qs.order_by("order", "created_at"), many=True, context=self.context).data

    def get_resources(self, obj):
        request = self.context.get("request")
        # Resources attached directly to module (lesson is null)
        qs = obj.resources.filter(lesson__isnull=True)
        if request and getattr(request.user, "is_student", False):
            qs = qs.filter(is_published=True)
        return LearningResourceSerializer(qs.order_by("order", "created_at"), many=True, context=self.context).data


class CourseModuleCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating course modules.
    """

    class Meta:
        model = CourseModule
        fields = [
            "id",
            "course_offering",
            "title",
            "description",
            "order",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LessonProgressSerializer(serializers.ModelSerializer):
    """
    Serializer for LessonProgress tracking.
    """

    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    student_registration_number = serializers.CharField(source="student.registration_number", read_only=True)

    class Meta:
        model = LessonProgress
        fields = [
            "id",
            "student",
            "student_registration_number",
            "lesson",
            "lesson_title",
            "is_completed",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "student", "student_registration_number", "lesson_title", "completed_at", "created_at", "updated_at"]

