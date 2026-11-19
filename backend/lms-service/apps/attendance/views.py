"""
Views for Attendance Management in CampusOS LMS.
Implements endpoints for session scheduling, attendance marking, audited corrections,
course-wise reports, and student summaries/histories (SRS Section 3.D).
"""

from datetime import datetime
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
from apps.students.models import StudentProfile
from .models import AttendanceRecord, AttendanceSession
from .permissions import CanViewOrAccessAttendanceRecord, IsAttendanceInstructorOrAdmin
from .serializers import (
    AttendanceMarkBulkSerializer,
    AttendanceRecordCorrectionSerializer,
    AttendanceRecordSerializer,
    AttendanceSessionCreateSerializer,
    AttendanceSessionDetailSerializer,
    AttendanceSessionListSerializer,
    StudentAttendanceHistorySerializer,
    StudentAttendanceSummarySerializer,
)
from .services import AttendanceService


class CourseOfferingAttendanceSessionsView(APIView):
    """
    GET /api/attendance/offerings/<int:offering_id>/sessions/
      - Lists attendance sessions for the course offering.
      - Faculty/Admin: all sessions.
      - Enrolled Students: can view session schedule.

    POST /api/attendance/offerings/<int:offering_id>/sessions/
      - Creates a new attendance session (Assigned Instructor or Admin only).
      - Optionally accepts an initial batch of student attendance marks.
    """

    def get(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)

        # Access check
        if getattr(request.user, "is_student", False):
            profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
            if not profile or not Enrollment.objects.filter(
                student=profile, course_offering=offering, status=EnrollmentStatus.ENROLLED
            ).exists():
                raise PermissionDenied("You must be actively enrolled in this course to view attendance sessions.")
        else:
            try:
                AttendanceService.check_faculty_or_admin_permission(request.user, offering)
            except DjangoPermissionDenied as exc:
                raise PermissionDenied(str(exc))

        qs = AttendanceSession.objects.filter(course_offering=offering).order_by("-session_date", "-created_at")

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            qs = qs.filter(session_date__gte=start_date)
        if end_date:
            qs = qs.filter(session_date__lte=end_date)

        serializer = AttendanceSessionListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)
        if not IsAttendanceInstructorOrAdmin().has_object_permission(request, self, offering):
            raise PermissionDenied("Only the assigned instructor or an administrator can create attendance sessions.")

        serializer = AttendanceSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            session = AttendanceService.create_session(
                user=request.user,
                course_offering=offering,
                session_date=data["session_date"],
                title=data.get("title", ""),
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
                description=data.get("description", ""),
                initial_records=data.get("records", []),
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(AttendanceSessionDetailSerializer(session).data, status=status.HTTP_201_CREATED)


class AttendanceSessionDetailView(APIView):
    """
    GET /api/attendance/sessions/<int:pk>/
      - Retrieve session details and student roster records (Assigned Instructor or Admin only).

    PATCH /api/attendance/sessions/<int:pk>/
      - Update session metadata (title, date, time) (Assigned Instructor or Admin only).

    DELETE /api/attendance/sessions/<int:pk>/
      - Delete attendance session and associated records (Assigned Instructor or Admin only).
    """

    permission_classes = [IsAttendanceInstructorOrAdmin]

    def get_object(self, pk, request):
        session = get_object_or_404(
            AttendanceSession.objects.select_related("course_offering").prefetch_related("records__student"), pk=pk
        )
        if not IsAttendanceInstructorOrAdmin().has_object_permission(request, self, session):
            raise PermissionDenied("You do not have permission to manage this attendance session.")
        return session

    def get(self, request, pk):
        session = self.get_object(pk, request)
        serializer = AttendanceSessionDetailSerializer(session)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        session = self.get_object(pk, request)
        for field in ["title", "description", "session_date", "start_time", "end_time"]:
            if field in request.data:
                setattr(session, field, request.data[field])

        try:
            session.save()
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)

        return Response(AttendanceSessionDetailSerializer(session).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        session = self.get_object(pk, request)
        session.delete()
        return Response({"message": "Attendance session deleted successfully."}, status=status.HTTP_200_OK)


class AttendanceSessionMarkView(APIView):
    """
    POST /api/attendance/sessions/<int:pk>/mark/
      - Bulk marks or updates student attendance records for a session.
      - Enforces that students are actively enrolled in the course offering.
      - Accepts: {"records": [{"student_id": 1, "status": "PRESENT", "remarks": ""}, ...]}
    """

    permission_classes = [IsAttendanceInstructorOrAdmin]

    def post(self, request, pk):
        session = get_object_or_404(AttendanceSession.objects.select_related("course_offering"), pk=pk)
        if not IsAttendanceInstructorOrAdmin().has_object_permission(request, self, session):
            raise PermissionDenied("Only the assigned instructor or an administrator can mark attendance.")

        serializer = AttendanceMarkBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        records_data = serializer.validated_data["records"]
        default_audit = serializer.validated_data.get("default_audit_reason", "")

        try:
            results = AttendanceService.mark_or_update_session_records(
                user=request.user,
                session=session,
                records_data=records_data,
                default_audit_reason=default_audit,
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(AttendanceRecordSerializer(results, many=True).data, status=status.HTTP_200_OK)


class AttendanceRecordDetailView(APIView):
    """
    GET /api/attendance/records/<int:pk>/
      - View details of an individual attendance record.
      - Protected by CanViewOrAccessAttendanceRecord (Student owner, Instructor, Admin).

    PATCH /api/attendance/records/<int:pk>/
      - Correct attendance record status with an audit reason (SRS Section 3.D).
      - Body: {"status": "PRESENT|ABSENT|LATE", "audit_reason": "Explanation"}
    """

    permission_classes = [CanViewOrAccessAttendanceRecord]

    def get(self, request, pk):
        record = get_object_or_404(
            AttendanceRecord.objects.select_related("session__course_offering", "student"), pk=pk
        )
        if not CanViewOrAccessAttendanceRecord().has_object_permission(request, self, record):
            raise PermissionDenied("You do not have permission to view this attendance record.")

        return Response(AttendanceRecordSerializer(record).data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        record = get_object_or_404(
            AttendanceRecord.objects.select_related("session__course_offering", "student"), pk=pk
        )
        if not IsAttendanceInstructorOrAdmin().has_object_permission(request, self, record):
            raise PermissionDenied("Only the assigned instructor or an administrator can correct attendance.")

        serializer = AttendanceRecordCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        audit_reason = serializer.validated_data["audit_reason"]
        remarks = serializer.validated_data.get("remarks")

        try:
            corrected = AttendanceService.correct_record(
                user=request.user,
                record=record,
                new_status=new_status,
                audit_reason=audit_reason,
                remarks=remarks,
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(AttendanceRecordSerializer(corrected).data, status=status.HTTP_200_OK)


class CourseAttendanceReportView(APIView):
    """
    GET /api/attendance/offerings/<int:offering_id>/report/
      - Course-wise attendance report (SRS Section 3.D).
      - Query params:
          ?threshold=75.0 (optional configurable percentage)
          ?start_date=YYYY-MM-DD
          ?end_date=YYYY-MM-DD
    """

    def get(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)
        if not IsAttendanceInstructorOrAdmin().has_object_permission(request, self, offering):
            raise PermissionDenied("Only the assigned instructor or an administrator can generate attendance reports.")

        threshold = request.query_params.get("threshold")
        threshold_val = float(threshold) if threshold is not None else None

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        try:
            report = AttendanceService.get_course_attendance_report(
                user=request.user,
                course_offering=offering,
                start_date=start_date,
                end_date=end_date,
                threshold=threshold_val,
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)

        return Response(report, status=status.HTTP_200_OK)


class StudentMyAttendanceSummaryView(APIView):
    """
    GET /api/attendance/my-summary/
      - View subject-wise attendance percentages across all enrolled courses (SRS Section 3.D).
      - Optional query param: ?offering_id=<id>
    """

    def get(self, request):
        if not getattr(request.user, "is_student", False):
            raise PermissionDenied("Only students can view personal attendance summaries.")

        profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
        if not profile:
            raise NotFound("No student academic profile found.")

        offering_id = request.query_params.get("offering_id")
        offering_id_val = int(offering_id) if offering_id else None

        summaries = AttendanceService.get_student_attendance_summary(
            student_profile=profile,
            course_offering_id=offering_id_val,
        )
        serializer = StudentAttendanceSummarySerializer(summaries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentMyAttendanceHistoryView(APIView):
    """
    GET /api/attendance/my-history/
      - View attendance history for the authenticated student (SRS Section 3.D).
      - Optional query param: ?offering_id=<id>
    """

    def get(self, request):
        if not getattr(request.user, "is_student", False):
            raise PermissionDenied("Only students can view personal attendance history.")

        profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
        if not profile:
            raise NotFound("No student academic profile found.")

        offering_id = request.query_params.get("offering_id")
        offering_id_val = int(offering_id) if offering_id else None

        records = AttendanceService.get_student_attendance_history(
            student_profile=profile,
            course_offering_id=offering_id_val,
        )
        serializer = StudentAttendanceHistorySerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

