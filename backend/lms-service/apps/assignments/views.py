"""
Views for Assignment Management & Student Submissions in CampusOS LMS.
"""

from decimal import Decimal
from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import CourseOffering
from apps.students.models import StudentProfile
from .models import Assignment, AssignmentSubmission, SubmissionStatus
from .permissions import (
    CanViewOrAccessAssignment,
    IsAssignmentInstructorOrAdmin,
    IsSubmissionOwnerOrInstructor,
)
from .serializers import (
    AssignmentCreateUpdateSerializer,
    AssignmentDetailSerializer,
    AssignmentListSerializer,
    AssignmentSubmissionSerializer,
    SubmissionCreateSerializer,
    SubmissionGradeSerializer,
)
from .services import AssignmentService


class CourseOfferingAssignmentsView(APIView):
    """
    GET /api/assignments/offerings/<int:offering_id>/
      - Lists assignments for the course offering.
      - Enrolled students see published assignments only.
      - Instructors and Admins see draft and published assignments.

    POST /api/assignments/offerings/<int:offering_id>/
      - Creates a new assignment (Assigned Instructor or Admin only).
    """

    permission_classes = [CanViewOrAccessAssignment]

    def get(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)
        # Access control via service
        try:
            AssignmentService.check_user_assignment_access(request.user, offering)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))
        qs = AssignmentService.get_assignments_queryset(request.user, offering)
        serializer = AssignmentListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)
        if not IsAssignmentInstructorOrAdmin().has_object_permission(request, self, offering):
            raise PermissionDenied("Only the assigned course instructor or an administrator can create assignments.")

        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["course_offering"] = offering.id

        serializer = AssignmentCreateUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        return Response(AssignmentDetailSerializer(assignment, context={"request": request}).data, status=status.HTTP_201_CREATED)


class AssignmentDetailView(APIView):
    """
    GET /api/assignments/<int:pk>/
      - Retrieve assignment details (published for enrolled students, all for instructors/admins).

    PATCH /api/assignments/<int:pk>/
      - Update assignment details (Instructor or Admin only).

    DELETE /api/assignments/<int:pk>/
      - Delete assignment (Instructor or Admin only).
    """

    permission_classes = [CanViewOrAccessAssignment]

    def get_object(self, pk, request):
        assignment = get_object_or_404(Assignment, pk=pk)
        if not CanViewOrAccessAssignment().has_object_permission(request, self, assignment):
            raise PermissionDenied("You do not have permission to access this assignment.")
        return assignment

    def get(self, request, pk):
        assignment = self.get_object(pk, request)
        serializer = AssignmentDetailSerializer(assignment, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        assignment = self.get_object(pk, request)
        if not IsAssignmentInstructorOrAdmin().has_object_permission(request, self, assignment):
            raise PermissionDenied("Only the assigned instructor or an administrator can update this assignment.")

        serializer = AssignmentCreateUpdateSerializer(assignment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(AssignmentDetailSerializer(updated, context={"request": request}).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        assignment = self.get_object(pk, request)
        if not IsAssignmentInstructorOrAdmin().has_object_permission(request, self, assignment):
            raise PermissionDenied("Only the assigned instructor or an administrator can delete this assignment.")

        assignment.delete()
        return Response({"message": "Assignment deleted successfully."}, status=status.HTTP_200_OK)


class AssignmentPublishView(APIView):
    """
    POST /api/assignments/<int:pk>/publish/
    Body: {"is_published": true|false}
    """

    permission_classes = [IsAssignmentInstructorOrAdmin]

    def post(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        if not IsAssignmentInstructorOrAdmin().has_object_permission(request, self, assignment):
            raise PermissionDenied("Permission denied.")

        is_published = request.data.get("is_published")
        if isinstance(is_published, str):
            is_published = is_published.lower() in ("true", "1")
        if is_published is None or not isinstance(is_published, bool):
            raise ValidationError({"is_published": "This field is required and must be a boolean."})

        updated = AssignmentService.publish_assignment(assignment, is_published=is_published)
        return Response(AssignmentDetailSerializer(updated, context={"request": request}).data, status=status.HTTP_200_OK)


class AssignmentSubmitView(APIView):
    """
    POST /api/assignments/<int:pk>/submit/
    Accepts text response and/or an uploaded file (multipart/form-data or json).
    Enforces student enrollment, published assignment, deadlines, and resubmission policies.
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)

        serializer = SubmissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission_text = serializer.validated_data.get("submission_text", "")
        submission_file = request.FILES.get("submission_file") or serializer.validated_data.get("submission_file")

        try:
            submission = AssignmentService.submit_assignment(
                user=request.user,
                assignment=assignment,
                submission_text=submission_text,
                submission_file=submission_file,
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(AssignmentSubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)


class StudentMySubmissionView(APIView):
    """
    GET /api/assignments/<int:pk>/my-submission/
    Allows an enrolled student to view their own submission, status, marks, and feedback.
    """

    def get(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        if not getattr(request.user, "is_student", False):
            raise PermissionDenied("Only students have personal submission records.")

        if not CanViewOrAccessAssignment().has_object_permission(request, self, assignment):
            raise PermissionDenied("You do not have permission to access this assignment.")

        profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
        if not profile:
            raise NotFound("No student academic profile found.")

        submission = AssignmentSubmission.objects.filter(assignment=assignment, student=profile).first()
        if not submission:
            raise NotFound("No submission found for this assignment.")

        return Response(AssignmentSubmissionSerializer(submission).data, status=status.HTTP_200_OK)


class AssignmentSubmissionsListView(APIView):
    """
    GET /api/assignments/<int:pk>/submissions/
    Lists all student submissions for an assignment (Assigned Instructor or Admin only).
    Filterable by query param: ?status=SUBMITTED|GRADED|RESUBMITTED
    """

    permission_classes = [IsAssignmentInstructorOrAdmin]

    def get(self, request, pk):
        assignment = get_object_or_404(Assignment, pk=pk)
        if not IsAssignmentInstructorOrAdmin().has_object_permission(request, self, assignment):
            raise PermissionDenied("Only the assigned instructor or an administrator can view class submissions.")

        qs = assignment.submissions.all().select_related("student", "assignment__course_offering")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        serializer = AssignmentSubmissionSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AssignmentSubmissionDetailView(APIView):
    """
    GET /api/assignments/submissions/<int:pk>/
    View details of an individual submission.
    Protected by IsSubmissionOwnerOrInstructor (Student owner, Instructor, or Admin).
    """

    permission_classes = [IsSubmissionOwnerOrInstructor]

    def get(self, request, pk):
        submission = get_object_or_404(
            AssignmentSubmission.objects.select_related("student", "assignment__course_offering"), pk=pk
        )
        if not IsSubmissionOwnerOrInstructor().has_object_permission(request, self, submission):
            raise PermissionDenied("You do not have permission to view this submission.")

        return Response(AssignmentSubmissionSerializer(submission).data, status=status.HTTP_200_OK)


class AssignmentSubmissionGradeView(APIView):
    """
    POST /api/assignments/submissions/<int:pk>/grade/
    Body: {"marks_obtained": 85.50, "feedback": "Well written solution."}
    Evaluates and grades a student submission (Assigned Instructor or Admin only).
    """

    permission_classes = [IsAssignmentInstructorOrAdmin]

    def post(self, request, pk):
        submission = get_object_or_404(
            AssignmentSubmission.objects.select_related("assignment__course_offering", "student"), pk=pk
        )
        if not IsAssignmentInstructorOrAdmin().has_object_permission(request, self, submission):
            raise PermissionDenied("Only the assigned instructor or an administrator can grade this submission.")

        serializer = SubmissionGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        marks = serializer.validated_data["marks_obtained"]
        feedback = serializer.validated_data.get("feedback", "")

        try:
            graded = AssignmentService.grade_submission(
                evaluator_user=request.user,
                submission=submission,
                marks_obtained=marks,
                feedback=feedback,
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(AssignmentSubmissionSerializer(graded).data, status=status.HTTP_200_OK)

