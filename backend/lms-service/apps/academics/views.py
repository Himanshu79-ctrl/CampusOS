"""
API views for Academic Terms, Course Offerings, and Enrollments in CampusOS LMS.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import (
    AcademicTerm,
    CourseOffering,
    Enrollment,
    EnrollmentStatus,
    OfferingStatus,
    TermStatus,
)
from apps.academics.serializers import (
    AcademicTermSerializer,
    CourseOfferingListSerializer,
    CourseOfferingSerializer,
    EnrollmentDetailSerializer,
    EnrollmentSerializer,
    RosterStudentSerializer,
)
from apps.academics.services import AcademicTermService, EnrollmentService
from apps.students.models import StudentProfile
from config.permissions import (
    IsAcademicAdmin,
    IsAuthenticated,
    IsEnrollmentOwnerOrAdmin,
    IsFacultyOfferingOwnerOrAdmin,
    IsStudent,
)


# ==============================================================================
# Academic Term Views
# ==============================================================================


class AcademicTermListCreateView(generics.ListCreateAPIView):
    """
    GET /api/academics/terms/ - List academic terms (authenticated).
    POST /api/academics/terms/ - Create a new term (academic admin only).
    """

    serializer_class = AcademicTermSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAcademicAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = AcademicTerm.objects.all().order_by("-start_date")
        status_param = self.request.query_params.get("status")
        year_param = self.request.query_params.get("academic_year")

        if status_param:
            qs = qs.filter(status=status_param.upper())
        if year_param:
            qs = qs.filter(academic_year=year_param)

        return qs


class CurrentAcademicTermView(APIView):
    """
    GET /api/academics/terms/current/
    Retrieves the currently ACTIVE academic term.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        term = AcademicTerm.objects.filter(status=TermStatus.ACTIVE).first()
        if not term:
            raise NotFound("No active academic term found.")
        serializer = AcademicTermSerializer(term)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcademicTermDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/academics/terms/<int:pk>/ - Retrieve term details (authenticated).
    PATCH /api/academics/terms/<int:pk>/ - Update term details (academic admin only).
    """

    queryset = AcademicTerm.objects.all()
    serializer_class = AcademicTermSerializer

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [IsAcademicAdmin()]
        return [IsAuthenticated()]


class AcademicTermActivateView(APIView):
    """
    POST /api/academics/terms/<int:pk>/activate/
    Activates the term and marks previously active term as COMPLETED.
    """

    permission_classes = [IsAcademicAdmin]

    def post(self, request, pk):
        term = get_object_or_404(AcademicTerm, pk=pk)
        try:
            activated_term = AcademicTermService.activate_term(term)
        except DjangoValidationError as exc:
            raise ValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else str(exc))
        return Response(AcademicTermSerializer(activated_term).data, status=status.HTTP_200_OK)


class AcademicTermCompleteView(APIView):
    """
    POST /api/academics/terms/<int:pk>/complete/
    Marks the term as COMPLETED and automatically closes enrollment.
    """

    permission_classes = [IsAcademicAdmin]

    def post(self, request, pk):
        term = get_object_or_404(AcademicTerm, pk=pk)
        try:
            completed_term = AcademicTermService.complete_term(term)
        except DjangoValidationError as exc:
            raise ValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else str(exc))
        return Response(AcademicTermSerializer(completed_term).data, status=status.HTTP_200_OK)


class AcademicTermEnrollmentWindowView(APIView):
    """
    POST /api/academics/terms/<int:pk>/enrollment-window/
    Body: {"is_open": true|false}
    Opens or closes the enrollment window for an academic term.
    """

    permission_classes = [IsAcademicAdmin]

    def post(self, request, pk):
        term = get_object_or_404(AcademicTerm, pk=pk)
        is_open = request.data.get("is_open")
        if isinstance(is_open, str):
            if is_open.lower() in ("true", "1"):
                is_open = True
            elif is_open.lower() in ("false", "0"):
                is_open = False
        if is_open is None or not isinstance(is_open, bool):
            raise ValidationError({"is_open": "This field is required and must be a boolean."})

        try:
            updated_term = AcademicTermService.set_enrollment_window(term, is_open=is_open)
        except DjangoValidationError as exc:
            raise ValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else str(exc))
        return Response(AcademicTermSerializer(updated_term).data, status=status.HTTP_200_OK)


# ==============================================================================
# Course Offering Views
# ==============================================================================


class CourseOfferingListCreateView(generics.ListCreateAPIView):
    """
    GET /api/academics/offerings/ - List offerings with filters for term, department, faculty, status.
    POST /api/academics/offerings/ - Create new offering (academic admin only).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAcademicAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CourseOfferingSerializer
        return CourseOfferingListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = CourseOffering.objects.select_related("academic_term").all()

        # Students can only view PUBLISHED course offerings
        if getattr(user, "is_student", False):
            qs = qs.filter(status=OfferingStatus.PUBLISHED)

        # Filters
        term = self.request.query_params.get("term")
        department = self.request.query_params.get("department")
        faculty = self.request.query_params.get("faculty")
        status_param = self.request.query_params.get("status")

        if term:
            qs = qs.filter(academic_term_id=term)
        if department:
            dept_list = [d.strip() for d in department.split(",") if d.strip()]
            qs = qs.filter(department_id__in=dept_list)
        if getattr(user, "is_faculty", False) and not getattr(user, "is_admin", False):
            from apps.academics.faculty_matcher import filter_offerings_for_faculty
            qs = filter_offerings_for_faculty(qs, user, faculty_param=faculty)
        elif faculty:
            qs = qs.filter(faculty_id=faculty)
        if status_param and not getattr(user, "is_student", False):
            qs = qs.filter(status=status_param.upper())

        return qs.order_by("academic_term", "course_id", "section")


class CourseOfferingDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/academics/offerings/<int:pk>/ - Retrieve offering details.
    PATCH /api/academics/offerings/<int:pk>/ - Update offering (academic admin only).
    """

    queryset = CourseOffering.objects.select_related("academic_term").all()
    serializer_class = CourseOfferingSerializer

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [IsAcademicAdmin()]
        return [IsAuthenticated()]


class CourseOfferingRosterView(APIView):
    """
    GET /api/academics/offerings/<int:pk>/students/
    Retrieves the roster of enrolled students for a course offering.
    Restricted to the assigned faculty instructor or academic administrators.
    """

    permission_classes = [IsFacultyOfferingOwnerOrAdmin]

    def get(self, request, pk):
        offering = get_object_or_404(
            CourseOffering.objects.select_related("academic_term"), pk=pk
        )
        self.check_object_permissions(request, offering)

        status_filter = request.query_params.get("status", EnrollmentStatus.ENROLLED)
        enrollments = (
            Enrollment.objects.filter(course_offering=offering)
            .select_related("student")
            .order_by("student__registration_number")
        )

        if status_filter:
            enrollments = enrollments.filter(status=status_filter.upper())

        serializer = RosterStudentSerializer(enrollments, many=True)
        return Response(
            {
                "offering_id": offering.id,
                "course_id": offering.course_id,
                "section": offering.section,
                "academic_term": offering.academic_term.name,
                "capacity": offering.capacity,
                "enrolled_count": enrollments.count(),
                "students": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# ==============================================================================
# Enrollment Action Views
# ==============================================================================


class EnrollStudentView(APIView):
    """
    POST /api/academics/offerings/<int:pk>/enroll/
    Enrolls a student in the specified course offering.
    Students enroll themselves; Admins can specify "student_id".
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        offering = get_object_or_404(
            CourseOffering.objects.select_related("academic_term"), pk=pk
        )

        # Resolve student profile
        if getattr(user, "is_admin", False) and "student_id" in request.data:
            student = get_object_or_404(StudentProfile, pk=request.data["student_id"])
        elif getattr(user, "is_student", False):
            student = StudentProfile.objects.filter(auth_user_id=user.user_id).first()
            if not student:
                raise NotFound("Student profile not found. Please provision your student profile first.")
        else:
            raise PermissionDenied("Only students or academic administrators can enroll in courses.")

        try:
            enrollment = EnrollmentService.enroll_student(student=student, course_offering=offering)
        except DjangoValidationError as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else str(exc)
            raise ValidationError(detail=msg)

        serializer = EnrollmentDetailSerializer(enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DropStudentView(APIView):
    """
    POST /api/academics/offerings/<int:pk>/drop/
    Drops an active enrollment in the specified course offering.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        offering = get_object_or_404(
            CourseOffering.objects.select_related("academic_term"), pk=pk
        )

        # Resolve student profile
        if getattr(user, "is_admin", False) and "student_id" in request.data:
            student = get_object_or_404(StudentProfile, pk=request.data["student_id"])
        elif getattr(user, "is_student", False):
            student = StudentProfile.objects.filter(auth_user_id=user.user_id).first()
            if not student:
                raise NotFound("Student profile not found.")
        else:
            raise PermissionDenied("Only students or academic administrators can drop course enrollments.")

        try:
            enrollment = EnrollmentService.drop_student(student=student, course_offering=offering)
        except DjangoValidationError as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else str(exc)
            raise ValidationError(detail=msg)

        serializer = EnrollmentDetailSerializer(enrollment)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EnrollmentListView(generics.ListAPIView):
    """
    GET /api/academics/enrollments/
    Lists enrollments scoped to the authenticated user's permissions:
    - Students see only their own enrollments.
    - Faculty see enrollments in offerings they teach.
    - Admins see all enrollments, filterable by student, offering, or term.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = EnrollmentDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Enrollment.objects.select_related(
            "student", "course_offering", "course_offering__academic_term"
        ).all()

        if getattr(user, "is_student", False):
            qs = qs.filter(student__auth_user_id=user.user_id)
        elif getattr(user, "is_faculty", False):
            from apps.academics.faculty_matcher import get_faculty_identifiers_for_user
            identifiers = get_faculty_identifiers_for_user(user)
            qs = qs.filter(course_offering__faculty_id__in=identifiers)
        elif getattr(user, "is_admin", False):
            student_id = self.request.query_params.get("student_id")
            offering_id = self.request.query_params.get("offering_id")
            term_id = self.request.query_params.get("term_id")
            if student_id:
                qs = qs.filter(student_id=student_id)
            if offering_id:
                qs = qs.filter(course_offering_id=offering_id)
            if term_id:
                qs = qs.filter(course_offering__academic_term_id=term_id)
        else:
            return Enrollment.objects.none()

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param.upper())

        return qs.order_by("-enrolled_at")

