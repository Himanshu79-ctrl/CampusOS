"""
Views for Grades & Academic Results in CampusOS LMS.
Implements endpoints for GradeItems, gradebook viewing, marks entry, assignment sync,
exam result ingestion, and student results retrieval (SRS Section 3.F).
"""

from decimal import Decimal
from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import CourseOffering, Enrollment, EnrollmentStatus
from apps.assignments.models import Assignment
from apps.students.models import StudentProfile
from .models import FinalCourseGrade, GradeItem, GradeRecord
from .permissions import CanViewFinalGrade, CanViewGradeRecord, IsGradeInstructorOrAdmin
from .serializers import (
    FinalCourseGradeSerializer,
    FinalGradeBulkPublishSerializer,
    GradeBulkInputSerializer,
    GradeItemCreateUpdateSerializer,
    GradeItemSerializer,
    GradeRecordInputSerializer,
    GradeRecordSerializer,
)
from .services import GradeService


class CourseOfferingGradeItemsView(APIView):
    """
    GET /api/grades/offerings/<int:offering_id>/items/
      - Lists assessment components for a course offering.
      - Enrolled students see published components only.
      - Instructors/Admins see all components.

    POST /api/grades/offerings/<int:offering_id>/items/
      - Creates a new assessment component (Assigned Instructor or Admin only).
    """

    def get(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)

        if getattr(request.user, "is_student", False):
            profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
            if not profile or not Enrollment.objects.filter(
                student=profile, course_offering=offering, status=EnrollmentStatus.ENROLLED
            ).exists():
                raise PermissionDenied("You must be actively enrolled in this course to view its grade items.")
            qs = offering.grade_items.filter(is_published=True).order_by("created_at")
        else:
            try:
                GradeService.check_faculty_or_admin_permission(request.user, offering)
            except DjangoPermissionDenied as exc:
                raise PermissionDenied(str(exc))
            qs = offering.grade_items.all().order_by("created_at")

        serializer = GradeItemSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)
        if not IsGradeInstructorOrAdmin().has_object_permission(request, self, offering):
            raise PermissionDenied("Only the assigned instructor or an administrator can create grade items.")

        serializer = GradeItemCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        assignment = None
        if data.get("assignment_id"):
            assignment = get_object_or_404(Assignment, pk=data["assignment_id"])

        try:
            item = GradeService.create_grade_item(
                user=request.user,
                course_offering=offering,
                name=data["name"],
                item_type=data.get("item_type", "ASSIGNMENT"),
                max_marks=data.get("max_marks", Decimal("100.00")),
                weightage_percentage=data.get("weightage_percentage"),
                assignment=assignment,
                external_exam_id=data.get("external_exam_id", ""),
                is_published=data.get("is_published", False),
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(GradeItemSerializer(item).data, status=status.HTTP_201_CREATED)


class GradeItemDetailView(APIView):
    """
    GET /api/grades/items/<int:pk>/
      - Detail of an assessment component.

    PATCH /api/grades/items/<int:pk>/
      - Update assessment component parameters.

    DELETE /api/grades/items/<int:pk>/
      - Delete assessment component.
    """

    permission_classes = [IsGradeInstructorOrAdmin]

    def get_object(self, pk, request):
        item = get_object_or_404(GradeItem.objects.select_related("course_offering"), pk=pk)
        if not IsGradeInstructorOrAdmin().has_object_permission(request, self, item):
            raise PermissionDenied("You do not have permission to access this grade item.")
        return item

    def get(self, request, pk):
        item = self.get_object(pk, request)
        return Response(GradeItemSerializer(item).data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        item = self.get_object(pk, request)
        serializer = GradeItemCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            updated = GradeService.update_grade_item(request.user, item, **data)
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)

        return Response(GradeItemSerializer(updated).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        item = self.get_object(pk, request)
        GradeService.delete_grade_item(request.user, item)
        return Response({"message": "Grade item deleted successfully."}, status=status.HTTP_200_OK)


class GradeItemPublishView(APIView):
    """
    POST /api/grades/items/<int:pk>/publish/
    Body: {"is_published": true|false}
    """

    permission_classes = [IsGradeInstructorOrAdmin]

    def post(self, request, pk):
        item = get_object_or_404(GradeItem.objects.select_related("course_offering"), pk=pk)
        if not IsGradeInstructorOrAdmin().has_object_permission(request, self, item):
            raise PermissionDenied("Permission denied.")

        is_published = request.data.get("is_published", True)
        if isinstance(is_published, str):
            is_published = is_published.lower() in ("true", "1")

        updated = GradeService.publish_grade_item(request.user, item, is_published=bool(is_published))
        return Response(GradeItemSerializer(updated).data, status=status.HTTP_200_OK)


class GradeItemSyncAssignmentView(APIView):
    """
    POST /api/grades/items/<int:pk>/sync-assignment/
    Synchronizes graded LMS Assignment submissions into GradeRecords.
    """

    permission_classes = [IsGradeInstructorOrAdmin]

    def post(self, request, pk):
        item = get_object_or_404(GradeItem.objects.select_related("course_offering", "assignment"), pk=pk)
        if not IsGradeInstructorOrAdmin().has_object_permission(request, self, item):
            raise PermissionDenied("Permission denied.")

        try:
            count = GradeService.sync_assignment_grades(request.user, item)
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)

        return Response({"message": f"Successfully synced {count} assignment grade records.", "synced_count": count}, status=status.HTTP_200_OK)


class GradeItemSyncExamView(APIView):
    """
    POST /api/grades/items/<int:pk>/sync-exam/
    Triggers Exam Engine result ingestion via the integration boundary.
    """

    permission_classes = [IsGradeInstructorOrAdmin]

    def post(self, request, pk):
        item = get_object_or_404(GradeItem.objects.select_related("course_offering"), pk=pk)
        if not IsGradeInstructorOrAdmin().has_object_permission(request, self, item):
            raise PermissionDenied("Permission denied.")

        try:
            result = GradeService.sync_exam_grades(request.user, item)
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)

        return Response(result, status=status.HTTP_200_OK)


class GradeItemBulkMarksView(APIView):
    """
    POST /api/grades/items/<int:pk>/marks/
    Enters or updates student marks for a GradeItem.
    Body: {"records": [{"student_id": 1, "marks_obtained": "88.00", "letter_grade": "A", "feedback": "Well done"}]}
    """

    permission_classes = [IsGradeInstructorOrAdmin]

    def post(self, request, pk):
        item = get_object_or_404(GradeItem.objects.select_related("course_offering"), pk=pk)
        if not IsGradeInstructorOrAdmin().has_object_permission(request, self, item):
            raise PermissionDenied("Permission denied.")

        serializer = GradeBulkInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            results = GradeService.bulk_enter_grades(request.user, item, serializer.validated_data["records"])
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)

        return Response(GradeRecordSerializer(results, many=True).data, status=status.HTTP_200_OK)


class GradeRecordDetailView(APIView):
    """
    GET /api/grades/records/<int:pk>/
      - View details of an individual grade record (Student owner, Instructor, Admin).

    PATCH /api/grades/records/<int:pk>/
      - Update an individual student's marks and feedback (Assigned Instructor or Admin only).
    """

    def get_object(self, pk, request):
        record = get_object_or_404(
            GradeRecord.objects.select_related("grade_item__course_offering", "student"), pk=pk
        )
        if not CanViewGradeRecord().has_object_permission(request, self, record):
            raise PermissionDenied("You do not have permission to view this grade record.")
        return record

    def get(self, request, pk):
        record = self.get_object(pk, request)
        return Response(GradeRecordSerializer(record).data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        record = get_object_or_404(
            GradeRecord.objects.select_related("grade_item__course_offering", "student"), pk=pk
        )
        if not IsGradeInstructorOrAdmin().has_object_permission(request, self, record):
            raise PermissionDenied("Only the assigned instructor or an administrator can update marks.")

        serializer = GradeRecordInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            updated = GradeService.enter_or_update_grade_record(
                user=request.user,
                grade_item=record.grade_item,
                student_profile=record.student,
                marks_obtained=data.get("marks_obtained", record.marks_obtained),
                letter_grade=data.get("letter_grade", record.letter_grade),
                feedback=data.get("feedback", record.feedback),
                is_published=data.get("is_published", record.is_published),
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)

        return Response(GradeRecordSerializer(updated).data, status=status.HTTP_200_OK)


class CourseGradebookView(APIView):
    """
    GET /api/grades/offerings/<int:offering_id>/gradebook/
    Returns the complete course gradebook matrix (Assigned Instructor or Admin only).
    """

    def get(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)
        if not IsGradeInstructorOrAdmin().has_object_permission(request, self, offering):
            raise PermissionDenied("Only the assigned instructor or an administrator can view the course gradebook.")

        matrix = GradeService.get_course_gradebook(request.user, offering)
        return Response(matrix, status=status.HTTP_200_OK)


class CourseFinalGradesView(APIView):
    """
    GET /api/grades/offerings/<int:offering_id>/final-results/
      - Lists final course results.

    POST /api/grades/offerings/<int:offering_id>/final-results/
      - Finalizes and publishes final course results (Assigned Instructor or Admin only).
    """

    def get(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)

        if getattr(request.user, "is_student", False):
            profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
            if not profile:
                raise NotFound("No student profile found.")
            qs = FinalCourseGrade.objects.filter(course_offering=offering, student=profile, is_published=True)
        else:
            if not IsGradeInstructorOrAdmin().has_object_permission(request, self, offering):
                raise PermissionDenied("Permission denied.")
            qs = FinalCourseGrade.objects.filter(course_offering=offering)

        serializer = FinalCourseGradeSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)
        if not IsGradeInstructorOrAdmin().has_object_permission(request, self, offering):
            raise PermissionDenied("Only the assigned instructor or an administrator can publish final results.")

        serializer = FinalGradeBulkPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            results = GradeService.publish_final_course_grades(
                user=request.user,
                course_offering=offering,
                final_grades_data=serializer.validated_data.get("grades"),
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)

        return Response(FinalCourseGradeSerializer(results, many=True).data, status=status.HTTP_200_OK)


class StudentMyGradesView(APIView):
    """
    GET /api/grades/my-grades/
    Allows an enrolled student to view all their published grades and final course results (IDOR protected).
    Query param: ?offering_id=<int>
    """

    def get(self, request):
        if not getattr(request.user, "is_student", False):
            raise PermissionDenied("Only students have personal grades records.")

        profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
        if not profile:
            raise NotFound("No student academic profile found.")

        offering_id = request.query_params.get("offering_id")
        offering_id_val = int(offering_id) if offering_id else None

        results = GradeService.get_student_grades(profile, course_offering_id=offering_id_val)
        return Response({
            "grade_records": GradeRecordSerializer(results["grade_records"], many=True).data,
            "final_course_grades": FinalCourseGradeSerializer(results["final_grades"], many=True).data,
        }, status=status.HTTP_200_OK)

