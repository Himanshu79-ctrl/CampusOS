"""
API views for Student Academic Profiles in CampusOS LMS.
"""

import json
import logging
import urllib.error
import urllib.request
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import StudentProfile
from .serializers import (
    StudentProfileCreateSerializer,
    StudentProfileSerializer,
    StudentProfileUpdateSerializer,
)
from config.permissions import IsAcademicAdmin, IsAuthenticated, IsSelfStudentOrAdmin, IsStudent

logger = logging.getLogger(__name__)


class StudentProfileCreateView(generics.CreateAPIView):
    """
    POST /api/students/profile/
    Provisions a new StudentProfile linked to external auth_user_id.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = StudentProfileCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        output_serializer = StudentProfileSerializer(profile)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


def get_or_provision_student_profile(user):
    """
    Retrieves the StudentProfile for the given auth user.
    If the authenticated user has the student role but has not yet had a profile
    manually provisioned by Super Admin, seamlessly provisions an active base profile.
    """
    profile = StudentProfile.objects.filter(auth_user_id=user.user_id).first()
    if not profile:
        if getattr(user, "is_student", False):
            reg_num = (
                f"REG-STU-{int(user.user_id):04d}"
                if str(user.user_id).isdigit()
                else f"REG-STU-{user.user_id}"
            )
            base_reg = reg_num
            idx = 1
            while StudentProfile.objects.filter(registration_number=reg_num).exists():
                reg_num = f"{base_reg}-{idx}"
                idx += 1
            profile = StudentProfile.objects.create(
                auth_user_id=str(user.user_id),
                registration_number=reg_num,
                department_id="CSE",
                admission_year=2026,
                current_semester=1,
                is_active=True,
            )
        else:
            raise NotFound("No student profile found for the authenticated user.")
    return profile


class CurrentStudentProfileView(APIView):
    """
    GET /api/students/profile/me/
    PATCH /api/students/profile/me/
    Retrieves or updates permitted academic profile fields for the authenticated student.
    """

    permission_classes = [IsStudent]

    def get_object(self):
        return get_or_provision_student_profile(self.request.user)

    def get(self, request):
        profile = self.get_object()
        serializer = StudentProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = self.get_object()
        serializer = StudentProfileUpdateSerializer(
            profile, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        updated_profile = serializer.save()
        return Response(StudentProfileSerializer(updated_profile).data, status=status.HTTP_200_OK)


class CurrentStudentEnrollmentsView(APIView):
    """
    GET /api/students/profile/me/enrollments/
    Returns course offerings currently enrolled by the authenticated student.
    """

    permission_classes = [IsStudent]

    def get(self, request):
        from apps.academics.models import Enrollment, EnrollmentStatus
        from apps.academics.serializers import EnrollmentDetailSerializer

        profile = get_or_provision_student_profile(request.user)

        status_filter = request.query_params.get("status", EnrollmentStatus.ENROLLED)
        term_id = request.query_params.get("term")

        qs = Enrollment.objects.filter(student=profile).select_related(
            "course_offering", "course_offering__academic_term"
        )

        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        if term_id:
            qs = qs.filter(course_offering__academic_term_id=term_id)

        serializer = EnrollmentDetailSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/students/profile/<int:pk>/
    PATCH /api/students/profile/<int:pk>/
    Protected by IsSelfStudentOrAdmin to prevent IDOR access to other students' private data.
    """

    queryset = StudentProfile.objects.all()
    permission_classes = [IsSelfStudentOrAdmin]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return StudentProfileUpdateSerializer
        return StudentProfileSerializer


class UnifiedStudentProvisionView(APIView):
    """
    POST /api/students/unified-provision/
    Unified Student Provisioning Endpoint for Super Admin.
    Creates the student's Authentication Account in Auth Service (port 8001),
    retrieves the actual Auth User ID, creates the StudentProfile in LMS Service (port 8000),
    and generates a secure single-use password setup token.
    Includes pre-validation and explicit rollback on failure.
    """

    permission_classes = [IsAcademicAdmin]

    def post(self, request):
        data = request.data or {}

        full_name = str(data.get("full_name") or data.get("name") or "").strip()
        email = str(data.get("email") or "").strip().lower()
        username = str(data.get("username") or "").strip().lower()
        registration_number = str(data.get("registration_number") or "").strip().upper()
        department_id = str(data.get("department_id") or "").strip()
        admission_year = data.get("admission_year")
        current_semester = data.get("current_semester", 1)

        errors = {}
        if not full_name:
            errors["full_name"] = ["Full Name is required."]
        if not email:
            errors["email"] = ["Email address is required."]
        if not username:
            errors["username"] = ["Username is required."]
        if not registration_number:
            errors["registration_number"] = ["Registration Number is required."]
        if not department_id:
            errors["department_id"] = ["Department is required."]

        try:
            admission_year = int(admission_year)
            if admission_year < 2000 or admission_year > 2100:
                errors["admission_year"] = ["Admission year must be between 2000 and 2100."]
        except (ValueError, TypeError):
            errors["admission_year"] = ["A valid admission year is required."]

        try:
            current_semester = int(current_semester)
            if current_semester < 1 or current_semester > 8:
                errors["current_semester"] = ["Current semester must be between 1 and 8."]
        except (ValueError, TypeError):
            errors["current_semester"] = ["Current semester must be an integer between 1 and 8."]

        # Pre-validate registration number uniqueness in LMS
        if registration_number and StudentProfile.objects.filter(registration_number__iexact=registration_number).exists():
            errors["registration_number"] = [
                f"A student profile with registration number '{registration_number}' already exists."
            ]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # 1. Call Auth Service to create the authentication user account
        auth_base = getattr(settings, "AUTH_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
        auth_url = f"{auth_base}/api/students/create/"

        auth_payload = json.dumps({
            "username": username,
            "email": email,
            "full_name": full_name,
        }).encode("utf-8")

        auth_header = request.headers.get("Authorization", "")
        req = urllib.request.Request(
            auth_url,
            data=auth_payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": auth_header,
                "User-Agent": "CampusOS-LMS-Service",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                auth_res = json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8")
            logger.warning("Auth service returned %s: %s", exc.code, err_body)
            try:
                err_json = json.loads(err_body)
                return Response(err_json, status=exc.code)
            except Exception:
                return Response(
                    {"detail": f"Authentication Service error ({exc.code}): {err_body}"},
                    status=exc.code,
                )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.error("Auth service unreachable at %s: %s", auth_url, exc)
            return Response(
                {
                    "detail": (
                        "Authentication Service (Port 8001) is unreachable. "
                        "Please verify that the Auth microservice is running."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        created_user = auth_res.get("user", {})
        actual_auth_user_id = str(created_user.get("id"))

        if not actual_auth_user_id or actual_auth_user_id == "None":
            logger.error("Auth service returned successful response without user ID: %s", auth_res)
            return Response(
                {"detail": "Invalid response received from Authentication Service."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 2. Create the StudentProfile linked to actual_auth_user_id
        try:
            profile = StudentProfile.objects.create(
                auth_user_id=actual_auth_user_id,
                registration_number=registration_number,
                department_id=department_id,
                admission_year=admission_year,
                current_semester=current_semester,
                is_active=True,
            )
        except Exception as exc:
            # EXPLICIT ROLLBACK: Safely delete the newly created Auth user
            logger.error(
                "StudentProfile creation failed for auth user %s: %s. Initiating rollback...",
                actual_auth_user_id,
                exc,
            )
            try:
                del_req = urllib.request.Request(
                    f"{auth_base}/api/students/{actual_auth_user_id}/",
                    headers={
                        "Authorization": auth_header,
                        "User-Agent": "CampusOS-LMS-Service",
                    },
                    method="DELETE",
                )
                with urllib.request.urlopen(del_req, timeout=5):
                    logger.info("Rollback successful: Auth user %s deleted.", actual_auth_user_id)
            except Exception as rollback_err:
                logger.critical("Rollback failed for Auth user %s: %s", actual_auth_user_id, rollback_err)

            return Response(
                {
                    "detail": f"Failed to create academic profile in LMS database: {str(exc)}. Auth account was rolled back."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Student account and academic profile provisioned successfully.",
                "profile": StudentProfileSerializer(profile).data,
                "user": created_user,
                "password_setup": auth_res.get("password_setup", {}),
            },
            status=status.HTTP_201_CREATED,
        )

