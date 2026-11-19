"""
Serializers for StudentProfile management in CampusOS LMS.
"""

from rest_framework import serializers
from apps.students.models import StudentProfile


class StudentProfileSerializer(serializers.ModelSerializer):
    """
    Standard serializer for viewing student profiles.
    """

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "auth_user_id",
            "registration_number",
            "department_id",
            "admission_year",
            "current_semester",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "auth_user_id", "created_at", "updated_at"]


class StudentProfileCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for provisioning a new StudentProfile.
    Enforces that students can only provision a profile for their own authenticated user ID.
    """

    auth_user_id = serializers.CharField(max_length=64, required=False)

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "auth_user_id",
            "registration_number",
            "department_id",
            "admission_year",
            "current_semester",
            "is_active",
        ]
        read_only_fields = ["id", "is_active"]

    def validate_registration_number(self, value):
        val = value.strip()
        if not val:
            raise serializers.ValidationError("Registration number cannot be blank.")
        if StudentProfile.objects.filter(registration_number__iexact=val).exists():
            raise serializers.ValidationError(
                f"A student profile with registration number '{val}' already exists."
            )
        return val

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # Determine target auth_user_id
        if user and getattr(user, "is_admin", False):
            # Admin can provision on behalf of any external user
            if "auth_user_id" not in attrs or not attrs["auth_user_id"].strip():
                raise serializers.ValidationError(
                    {"auth_user_id": "auth_user_id is required when an administrator creates a profile."}
                )
            attrs["auth_user_id"] = attrs["auth_user_id"].strip()
        else:
            # Student can only provision for themselves
            if not user or not getattr(user, "is_authenticated", False):
                raise serializers.ValidationError("Authentication required to create a student profile.")
            attrs["auth_user_id"] = user.user_id

        # Verify 1:1 mapping between Auth user and StudentProfile
        if StudentProfile.objects.filter(auth_user_id=attrs["auth_user_id"]).exists():
            raise serializers.ValidationError(
                {"auth_user_id": f"A student profile already exists for auth user '{attrs['auth_user_id']}'."}
            )

        return attrs


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating permitted academic profile fields.
    Prevents students from altering their registration number or Auth identity.
    """

    class Meta:
        model = StudentProfile
        fields = [
            "current_semester",
            "is_active",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # Students cannot toggle their own is_active status
        if user and not getattr(user, "is_admin", False):
            if "is_active" in attrs:
                attrs.pop("is_active")

        return attrs

