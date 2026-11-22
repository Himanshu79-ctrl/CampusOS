"""
Views for Timetable & Calendar Management in CampusOS LMS.
Implements endpoints for course schedules, conflict-checked slot management,
student/faculty timetables, and calendar events (SRS Section 3.E).
"""

from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.faculty_matcher import is_faculty_assigned
from apps.academics.models import AcademicTerm, CourseOffering, Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile
from .models import CalendarEvent, TimetableEntry
from .permissions import CanViewTimetableEntry, IsTimetableInstructorOrAdmin
from .serializers import (
    CalendarEventCreateUpdateSerializer,
    CalendarEventSerializer,
    TimetableEntryCreateUpdateSerializer,
    TimetableEntrySerializer,
)
from .services import TimetableService


class CourseOfferingTimetableView(APIView):
    """
    GET /api/timetable/offerings/<int:offering_id>/
      - Lists timetable class slots for a course offering.
      - Enrolled students, assigned faculty, and admins can view.

    POST /api/timetable/offerings/<int:offering_id>/
      - Creates a new timetable class slot (Assigned Faculty or Admin only).
      - Enforces room, faculty, and offering conflict validation.
    """

    def get(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)

        if getattr(request.user, "is_student", False):
            profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
            if not profile or not Enrollment.objects.filter(
                student=profile, course_offering=offering, status=EnrollmentStatus.ENROLLED
            ).exists():
                raise PermissionDenied("You must be actively enrolled in this course to view its timetable.")
        elif getattr(request.user, "is_faculty", False):
            if not is_faculty_assigned(request.user, offering.faculty_id) and not getattr(request.user, "is_admin", False):
                raise PermissionDenied("You are not the assigned instructor for this course offering.")

        entries = offering.timetable_entries.filter(is_active=True).order_by("day_of_week", "start_time")
        serializer = TimetableEntrySerializer(entries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)
        if not IsTimetableInstructorOrAdmin().has_object_permission(request, self, offering):
            raise PermissionDenied("Only the assigned instructor or an administrator can add timetable class slots.")

        serializer = TimetableEntryCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            entry = TimetableService.create_entry(
                user=request.user,
                course_offering=offering,
                day_of_week=data["day_of_week"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                room=data["room"],
                building=data.get("building", ""),
                entry_type=data.get("entry_type", "LECTURE"),
                faculty_id=data.get("faculty_id"),
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(TimetableEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class TimetableEntryDetailView(APIView):
    """
    GET /api/timetable/entries/<int:pk>/
      - Retrieve details of a timetable class slot.

    PATCH /api/timetable/entries/<int:pk>/
      - Update a timetable class slot with conflict validation (Assigned Faculty or Admin only).

    DELETE /api/timetable/entries/<int:pk>/
      - Delete a timetable class slot (Assigned Faculty or Admin only).
    """

    def get_object(self, pk, request):
        entry = get_object_or_404(
            TimetableEntry.objects.select_related("course_offering", "course_offering__academic_term"), pk=pk
        )
        if not CanViewTimetableEntry().has_object_permission(request, self, entry):
            raise PermissionDenied("You do not have permission to view this timetable slot.")
        return entry

    def get(self, request, pk):
        entry = self.get_object(pk, request)
        serializer = TimetableEntrySerializer(entry)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        entry = get_object_or_404(TimetableEntry.objects.select_related("course_offering"), pk=pk)
        if not IsTimetableInstructorOrAdmin().has_object_permission(request, self, entry):
            raise PermissionDenied("Only the assigned instructor or an administrator can update this timetable slot.")

        serializer = TimetableEntryCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            updated = TimetableService.update_entry(
                user=request.user,
                entry=entry,
                **serializer.validated_data,
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(TimetableEntrySerializer(updated).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        entry = get_object_or_404(TimetableEntry.objects.select_related("course_offering"), pk=pk)
        if not IsTimetableInstructorOrAdmin().has_object_permission(request, self, entry):
            raise PermissionDenied("Only the assigned instructor or an administrator can delete this timetable slot.")

        TimetableService.delete_entry(request.user, entry)
        return Response({"message": "Timetable slot deleted successfully."}, status=status.HTTP_200_OK)


class StudentMyTimetableView(APIView):
    """
    GET /api/timetable/my-timetable/
      - Show student's personal weekly class timetable across all enrolled courses (SRS Section 3.E).
      - Query params:
          ?term_id=<int>
          ?day_of_week=MONDAY|TUESDAY|...
    """

    def get(self, request):
        if not getattr(request.user, "is_student", False):
            raise PermissionDenied("Only students can access their personal student timetable.")

        profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
        if not profile:
            raise NotFound("No student academic profile found.")

        term_id = request.query_params.get("term_id")
        term_id_val = int(term_id) if term_id else None
        day_of_week = request.query_params.get("day_of_week")

        entries = TimetableService.get_student_timetable(
            student_profile=profile,
            term_id=term_id_val,
            day_of_week=day_of_week,
        )
        serializer = TimetableEntrySerializer(entries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FacultyMyTimetableView(APIView):
    """
    GET /api/timetable/faculty-timetable/
      - Show faculty teaching timetable (SRS Section 3.E).
      - Query params:
          ?faculty_id=<str> (Admin can query any faculty; Faculty queries self)
          ?term_id=<int>
          ?day_of_week=MONDAY|...
    """

    def get(self, request):
        param_faculty_id = request.query_params.get("faculty_id")

        if param_faculty_id and getattr(request.user, "is_admin", False):
            target_faculty_id = param_faculty_id
            user_arg = None
        elif getattr(request.user, "is_faculty", False):
            target_faculty_id = None
            user_arg = request.user
        elif getattr(request.user, "is_admin", False):
            target_faculty_id = param_faculty_id
            user_arg = None
        else:
            raise PermissionDenied("Only faculty members or administrators can access faculty timetables.")

        term_id = request.query_params.get("term_id")
        term_id_val = int(term_id) if term_id else None
        day_of_week = request.query_params.get("day_of_week")

        entries = TimetableService.get_faculty_timetable(
            faculty_id=target_faculty_id,
            term_id=term_id_val,
            day_of_week=day_of_week,
            user=user_arg,
        )
        serializer = TimetableEntrySerializer(entries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CalendarEventsView(APIView):
    """
    GET /api/timetable/calendar/
      - List calendar events scoped to the user's role and enrolled courses.
      - Query params: ?term_id=..., ?offering_id=..., ?start_date=..., ?end_date=...

    POST /api/timetable/calendar/
      - Create an institutional or course calendar event (Admin or Assigned Faculty).
    """

    def get(self, request):
        term_id = request.query_params.get("term_id")
        term_id_val = int(term_id) if term_id else None

        offering_id = request.query_params.get("offering_id")
        offering_id_val = int(offering_id) if offering_id else None

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        events = TimetableService.get_calendar_events(
            user=request.user,
            term_id=term_id_val,
            offering_id=offering_id_val,
            start_date=start_date,
            end_date=end_date,
        )
        serializer = CalendarEventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CalendarEventCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        term = None
        if data.get("academic_term_id"):
            term = get_object_or_404(AcademicTerm, pk=data["academic_term_id"])

        offering = None
        if data.get("course_offering_id"):
            offering = get_object_or_404(CourseOffering, pk=data["course_offering_id"])

        try:
            event = TimetableService.create_calendar_event(
                user=request.user,
                title=data["title"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                event_type=data.get("event_type", "EVENT"),
                description=data.get("description", ""),
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
                academic_term=term,
                course_offering=offering,
                is_published=data.get("is_published", True),
            )
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc))

        return Response(CalendarEventSerializer(event).data, status=status.HTTP_201_CREATED)


class CalendarEventDetailView(APIView):
    """
    GET /api/timetable/calendar/<int:pk>/
      - Retrieve calendar event details.

    PATCH /api/timetable/calendar/<int:pk>/
      - Update calendar event (Admin or Assigned Faculty for course events).

    DELETE /api/timetable/calendar/<int:pk>/
      - Delete calendar event (Admin or Assigned Faculty for course events).
    """

    def get_object(self, pk, request):
        event = get_object_or_404(CalendarEvent.objects.select_related("academic_term", "course_offering"), pk=pk)
        return event

    def get(self, request, pk):
        event = self.get_object(pk, request)
        if getattr(request.user, "is_student", False):
            if not event.is_published:
                raise PermissionDenied("This calendar event is not published.")
            if event.course_offering:
                profile = StudentProfile.objects.filter(auth_user_id=str(request.user.user_id)).first()
                if not profile or not Enrollment.objects.filter(
                    student=profile, course_offering=event.course_offering, status=EnrollmentStatus.ENROLLED
                ).exists():
                    raise PermissionDenied("You must be enrolled in this course to view its calendar event.")
        elif getattr(request.user, "is_faculty", False):
            if event.course_offering and not is_faculty_assigned(request.user, event.course_offering.faculty_id):
                raise PermissionDenied("You are not the assigned instructor for this course event.")
            if not event.course_offering and not event.is_published and not getattr(request.user, "is_admin", False):
                raise PermissionDenied("This calendar event is not published.")

        return Response(CalendarEventSerializer(event).data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        event = self.get_object(pk, request)
        if event.course_offering:
            TimetableService.check_faculty_or_admin_permission(request.user, event.course_offering)
        else:
            if not getattr(request.user, "is_admin", False):
                raise PermissionDenied("Only administrators can update institution-wide calendar events.")

        serializer = CalendarEventCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        for field in ["title", "description", "event_type", "start_date", "end_date", "start_time", "end_time", "is_published"]:
            if field in data:
                setattr(event, field, data[field])

        try:
            event.save()
        except (ValidationError, DjangoValidationError) as exc:
            msg = exc.message_dict if hasattr(exc, "message_dict") else (exc.messages if hasattr(exc, "messages") else str(exc))
            raise ValidationError(msg)

        return Response(CalendarEventSerializer(event).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        event = self.get_object(pk, request)
        if event.course_offering:
            TimetableService.check_faculty_or_admin_permission(request.user, event.course_offering)
        else:
            if not getattr(request.user, "is_admin", False):
                raise PermissionDenied("Only administrators can delete institution-wide calendar events.")

        event.delete()
        return Response({"message": "Calendar event deleted successfully."}, status=status.HTTP_200_OK)

