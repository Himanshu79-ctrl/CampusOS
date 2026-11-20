import re
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that embeds the user's role into access and refresh token claims.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'role', 'first_name', 'last_name', 'full_name')

    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name or obj.username


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'first_name', 'last_name')

    def create(self, validated_data):
        role = self.context.get('role', 'student')
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=role,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        return user


class StudentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for Super Admin provisioning a new student authentication account.
    Validates username and email uniqueness, initializes user with role='student'
    and an unusable password awaiting initial secure setup.
    """
    full_name = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'full_name')
        read_only_fields = ('id',)

    def validate_username(self, value):
        val = value.strip().lower()
        if not val:
            raise serializers.ValidationError("Username cannot be blank.")
        if len(val) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", val):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, underscores, periods, and hyphens."
            )
        if CustomUser.objects.filter(username__iexact=val).exists():
            raise serializers.ValidationError(f"A user with username '{val}' already exists.")
        return val

    def validate_email(self, value):
        val = value.strip().lower()
        if not val:
            raise serializers.ValidationError("Email address cannot be blank.")
        if CustomUser.objects.filter(email__iexact=val).exists():
            raise serializers.ValidationError(f"A user with email '{val}' already exists.")
        return val

    def create(self, validated_data):
        full_name = validated_data.pop('full_name', '').strip()
        first_name = validated_data.get('first_name', '').strip()
        last_name = validated_data.get('last_name', '').strip()

        if full_name and not first_name:
            parts = full_name.split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''

        user = CustomUser(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=first_name,
            last_name=last_name,
            role='student',
            is_active=True,
        )
        user.set_unusable_password()
        user.save()
        return user


class FacultyCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for Super Admin provisioning a new faculty authentication account.
    Validates username and email uniqueness, initializes user with role='faculty'
    and an unusable password awaiting initial secure setup.
    """
    full_name = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'full_name')
        read_only_fields = ('id',)

    def validate_username(self, value):
        val = value.strip().lower()
        if not val:
            raise serializers.ValidationError("Username cannot be blank.")
        if len(val) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", val):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, underscores, periods, and hyphens."
            )
        if CustomUser.objects.filter(username__iexact=val).exists():
            raise serializers.ValidationError(f"A user with username '{val}' already exists.")
        return val

    def validate_email(self, value):
        val = value.strip().lower()
        if not val:
            raise serializers.ValidationError("Email address cannot be blank.")
        if CustomUser.objects.filter(email__iexact=val).exists():
            raise serializers.ValidationError(f"A user with email '{val}' already exists.")
        return val

    def create(self, validated_data):
        full_name = validated_data.pop('full_name', '').strip()
        first_name = validated_data.get('first_name', '').strip()
        last_name = validated_data.get('last_name', '').strip()

        if full_name and not first_name:
            parts = full_name.split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''

        user = CustomUser(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=first_name,
            last_name=last_name,
            role='faculty',
            is_active=True,
        )
        user.set_unusable_password()
        user.save()
        return user


class PasswordSetupSerializer(serializers.Serializer):
    """
    Serializer for verifying and setting initial password using a secure setup token.
    """
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value
