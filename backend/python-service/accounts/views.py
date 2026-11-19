import logging
from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import CustomUser
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    StudentCreateSerializer,
    FacultyCreateSerializer,
    PasswordSetupSerializer,
)
from .permissions import IsAdmin
from .token_utils import generate_setup_token, verify_setup_token

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


class CreateStaffView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (IsAdmin,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        role = request.data.get('role', 'faculty')
        serializer = self.get_serializer(data=request.data, context={'role': role})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    """
    GET /api/users/
    Lists users filtered by role (?role=student|faculty|super_admin).
    Restricted to administrators.
    """
    serializer_class = UserSerializer
    permission_classes = (IsAdmin,)

    def get_queryset(self):
        role = self.request.query_params.get('role')
        qs = CustomUser.objects.all().order_by('id')
        if role:
            qs = qs.filter(role=role)
        return qs


class CreateStudentView(APIView):
    """
    POST /api/students/create/
    Creates a new student authentication account with role='student'
    and generates a secure, time-limited, single-use password setup token.
    Restricted to Super Admin and Academic Administrators.
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = StudentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        uid, token = generate_setup_token(user)

        # Determine email delivery capability
        email_sent = False
        email_backend = getattr(settings, "EMAIL_BACKEND", "")
        email_host = getattr(settings, "EMAIL_HOST", None)

        if email_host and not str(email_backend).endswith("console.EmailBackend"):
            try:
                setup_link = f"http://localhost:3000/set-password?uid={uid}&token={token}"
                send_mail(
                    subject="CampusOS Student Account Password Setup",
                    message=(
                        f"Hello {user.first_name or user.username},\n\n"
                        f"Your CampusOS student account has been created.\n"
                        f"Please set your password using the link below:\n"
                        f"{setup_link}\n\n"
                        f"This link is single-use and time-limited."
                    ),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@campusos.edu"),
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                email_sent = True
                notice = f"Password setup link dispatched to {user.email}."
            except Exception as exc:
                logger.warning("Email delivery failed for %s: %s", user.email, exc)
                email_sent = False
                notice = f"Email delivery failed ({exc}). Share the setup link below directly with the student."
        else:
            email_sent = False
            notice = (
                "Email service is in local/console mode. "
                "Share the one-time secure link below with the student to set their initial password."
            )

        return Response(
            {
                "success": True,
                "user": UserSerializer(user).data,
                "password_setup": {
                    "uid": uid,
                    "token": token,
                    "setup_url": f"/set-password?uid={uid}&token={token}",
                    "email_sent": email_sent,
                    "notice": notice,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class DeleteStudentUserView(APIView):
    """
    DELETE /api/students/<int:pk>/
    Explicit rollback or cleanup endpoint for student accounts.
    Restricted to administrators; only allows deleting accounts with role='student'.
    """
    permission_classes = [IsAdmin]

    def delete(self, request, pk):
        user = CustomUser.objects.filter(pk=pk).first()
        if not user:
            return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.role != "student":
            return Response(
                {"message": "Only student accounts may be deleted through this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.delete()
        return Response({"success": True, "message": f"Student user #{pk} deleted successfully."}, status=status.HTTP_200_OK)


class CreateFacultyUserView(APIView):
    """
    POST /api/faculty/create/
    Creates a new faculty authentication account with role='faculty'
    and generates a secure, time-limited, single-use password setup token.
    Restricted to Super Admin and Academic Administrators.
    Handles idempotent retries safely.
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        username = str(request.data.get("username", "")).strip().lower()

        # Idempotent retry check: If exact faculty account already exists without usable password
        existing_user = None
        if email:
            existing_user = CustomUser.objects.filter(email__iexact=email).first()
        if not existing_user and username:
            existing_user = CustomUser.objects.filter(username__iexact=username).first()

        if existing_user:
            if existing_user.role == "faculty":
                # If account exists with unusable password (pending first-time setup), regenerate setup link
                if not existing_user.has_usable_password():
                    uid, token = generate_setup_token(existing_user)
                    return Response(
                        {
                            "success": True,
                            "user": UserSerializer(existing_user).data,
                            "password_setup": {
                                "uid": uid,
                                "token": token,
                                "setup_url": f"/set-password?uid={uid}&token={token}",
                                "email_sent": False,
                                "notice": (
                                    "Existing faculty account found with pending password setup. "
                                    "Share the one-time secure link below with the faculty member."
                                ),
                            },
                        },
                        status=status.HTTP_200_OK,
                    )
            # Otherwise duplicate conflict
            if CustomUser.objects.filter(username__iexact=username).exists():
                return Response(
                    {"username": [f"A user with username '{username}' already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if CustomUser.objects.filter(email__iexact=email).exists():
                return Response(
                    {"email": [f"A user with email '{email}' already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = FacultyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        uid, token = generate_setup_token(user)

        # Determine email delivery capability
        email_sent = False
        email_backend = getattr(settings, "EMAIL_BACKEND", "")
        email_host = getattr(settings, "EMAIL_HOST", None)

        if email_host and not str(email_backend).endswith("console.EmailBackend"):
            try:
                setup_link = f"http://localhost:3000/set-password?uid={uid}&token={token}"
                send_mail(
                    subject="CampusOS Faculty Account Password Setup",
                    message=(
                        f"Hello {user.first_name or user.username},\n\n"
                        f"Your CampusOS faculty account has been created.\n"
                        f"Please set your password using the link below:\n"
                        f"{setup_link}\n\n"
                        f"This link is single-use and time-limited."
                    ),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@campusos.edu"),
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                email_sent = True
                notice = f"Password setup link dispatched to {user.email}."
            except Exception as exc:
                logger.warning("Email delivery failed for %s: %s", user.email, exc)
                email_sent = False
                notice = f"Email delivery failed ({exc}). Share the setup link below directly with the faculty member."
        else:
            email_sent = False
            notice = (
                "Email service is in local/console mode. "
                "Share the one-time secure link below with the faculty member to set their initial password."
            )

        return Response(
            {
                "success": True,
                "user": UserSerializer(user).data,
                "password_setup": {
                    "uid": uid,
                    "token": token,
                    "setup_url": f"/set-password?uid={uid}&token={token}",
                    "email_sent": email_sent,
                    "notice": notice,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class GenerateFacultySetupLinkView(APIView):
    """
    POST /api/faculty/setup-link/
    Generates a secure, single-use password setup link for an existing faculty account.
    Restricted to administrators.
    Accepts: { "user_id": <int> } or { "email": <str> } or { "username": <str> }
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        user_id = request.data.get("user_id")
        email = request.data.get("email")
        username = request.data.get("username")

        user = None
        if user_id:
            user = CustomUser.objects.filter(pk=user_id, role="faculty").first()
        elif email:
            user = CustomUser.objects.filter(email__iexact=str(email).strip(), role="faculty").first()
        elif username:
            user = CustomUser.objects.filter(username__iexact=str(username).strip(), role="faculty").first()

        if not user:
            return Response(
                {"detail": "Faculty user account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        uid, token = generate_setup_token(user)

        return Response(
            {
                "success": True,
                "user": UserSerializer(user).data,
                "password_setup": {
                    "uid": uid,
                    "token": token,
                    "setup_url": f"/set-password?uid={uid}&token={token}",
                    "email_sent": False,
                    "notice": "One-time password setup link generated successfully. Share with faculty member.",
                },
            },
            status=status.HTTP_200_OK,
        )


class DeleteFacultyUserView(APIView):
    """
    DELETE /api/faculty/<int:pk>/
    Explicit rollback or cleanup endpoint for faculty accounts.
    Restricted to administrators; only allows deleting accounts with role='faculty'.
    """
    permission_classes = [IsAdmin]

    def delete(self, request, pk):
        user = CustomUser.objects.filter(pk=pk).first()
        if not user:
            return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.role != "faculty":
            return Response(
                {"message": "Only faculty accounts may be deleted through this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.delete()
        return Response({"success": True, "message": f"Faculty user #{pk} deleted successfully."}, status=status.HTTP_200_OK)


class VerifyPasswordSetupTokenView(APIView):
    """
    GET /api/password-setup/verify/?uid=<uid>&token=<token>
    Verifies whether a password setup token is valid, unexpired, and unused.
    Public endpoint used by student and faculty setup frontend pages.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        uid = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uid or not token:
            return Response(
                {"valid": False, "message": "Both 'uid' and 'token' parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_valid, user = verify_setup_token(uid, token)
        if not is_valid or not user:
            return Response(
                {
                    "valid": False,
                    "message": "This password setup link is invalid, expired, or has already been used.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "valid": True,
                "username": user.username,
                "first_name": user.first_name,
                "email": user.email,
                "role": user.role,
            },
            status=status.HTTP_200_OK,
        )


class ConfirmPasswordSetupView(APIView):
    """
    POST /api/password-setup/confirm/
    Accepts uid, token, and new_password.
    Validates token single-use, validates password strength, updates user password,
    invalidating the token immediately.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        is_valid, user = verify_setup_token(uid, token)
        if not is_valid or not user:
            return Response(
                {
                    "success": False,
                    "message": "This password setup link is invalid, expired, or has already been used.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user)
        except ValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {
                "success": True,
                "message": "Password has been successfully set. You may now log in.",
                "username": user.username,
            },
            status=status.HTTP_200_OK,
        )
