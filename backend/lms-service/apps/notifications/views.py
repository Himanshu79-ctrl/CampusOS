"""
Views for Notifications & Announcements in CampusOS LMS (SRS Section 3.G).
"""

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import CourseOffering, Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile
from .models import Announcement, AnnouncementScope, AudienceType, Notification
from .serializers import AnnouncementSerializer, NotificationSerializer
from .services import NotificationService


class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/
    Lists persistent in-app notifications for the authenticated user with optional filtering.
    Filters:
      - ?is_read=true / ?is_read=false
      - ?type=ANNOUNCEMENT|ASSIGNMENT|GRADE|ATTENDANCE|TIMETABLE|GENERAL
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Notification.objects.filter(recipient_user_id=str(user.user_id))

        is_read_param = self.request.query_params.get("is_read")
        if is_read_param is not None:
            if is_read_param.lower() in ("true", "1"):
                qs = qs.filter(is_read=True)
            elif is_read_param.lower() in ("false", "0"):
                qs = qs.filter(is_read=False)

        type_param = self.request.query_params.get("type")
        if type_param:
            qs = qs.filter(notification_type=type_param.upper())

        return qs.order_by("-created_at")


class NotificationUnreadCountView(APIView):
    """
    GET /api/notifications/unread-count/
    Returns the number of unread notifications for the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = NotificationService.get_unread_count(str(request.user.user_id))
        return Response({"unread_count": count}, status=status.HTTP_200_OK)


class NotificationMarkReadView(APIView):
    """
    POST /api/notifications/<int:pk>/read/
    Marks a specific notification as read. Enforces strict recipient isolation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient_user_id=str(request.user.user_id))
        notification.mark_as_read()
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(APIView):
    """
    POST /api/notifications/mark-all-read/
    Marks all notifications for the authenticated user as read.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = NotificationService.mark_all_as_read(str(request.user.user_id))
        return Response(
            {"message": "All notifications marked as read.", "marked_count": count},
            status=status.HTTP_200_OK,
        )


class AnnouncementListCreateView(generics.ListCreateAPIView):
    """
    GET /api/notifications/announcements/
    List announcements accessible to the current user based on role, scope, and enrollment.

    POST /api/notifications/announcements/
    Create a new announcement with scope, audience targeting, and optional course/department link.
    """

    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Announcement.objects.all()

        # Admin users can view all announcements
        if getattr(user, "is_admin", False):
            pass
        elif getattr(user, "is_faculty", False):
            # Faculty see published announcements targeted to them or all,
            # or announcements they authored, or announcements for offerings they teach.
            taught_offerings = CourseOffering.objects.filter(faculty_id=str(user.user_id))
            qs = qs.filter(
                Q(author_user_id=str(user.user_id))
                | (
                    Q(is_published=True)
                    & (
                        Q(scope=AnnouncementScope.INSTITUTION, audience_type__in=[AudienceType.ALL, AudienceType.FACULTY])
                        | Q(scope=AnnouncementScope.DEPARTMENT, audience_type__in=[AudienceType.ALL, AudienceType.FACULTY])
                        | Q(scope=AnnouncementScope.COURSE, course_offering__in=taught_offerings)
                    )
                )
            )
        else:
            # Student users: only published announcements matching audience and enrolled courses / department
            profile = StudentProfile.objects.filter(auth_user_id=str(user.user_id)).first()
            if not profile:
                return qs.none()

            enrolled_offerings = Enrollment.objects.filter(
                student=profile,
                status=EnrollmentStatus.ENROLLED,
            ).values_list("course_offering_id", flat=True)

            qs = qs.filter(
                is_published=True,
                audience_type__in=[AudienceType.ALL, AudienceType.STUDENTS],
            ).filter(
                Q(scope=AnnouncementScope.INSTITUTION)
                | Q(scope=AnnouncementScope.DEPARTMENT, department_id=profile.department_id)
                | Q(scope=AnnouncementScope.COURSE, course_offering_id__in=enrolled_offerings)
            )

        # Optional filters
        scope_param = self.request.query_params.get("scope")
        if scope_param:
            qs = qs.filter(scope=scope_param.upper())

        course_param = self.request.query_params.get("course_offering")
        if course_param:
            qs = qs.filter(course_offering_id=course_param)

        dept_param = self.request.query_params.get("department_id")
        if dept_param:
            qs = qs.filter(department_id=dept_param)

        return qs.distinct().order_by("-published_at", "-created_at")

    def perform_create(self, serializer):
        user = self.request.user
        if not (getattr(user, "is_admin", False) or getattr(user, "is_faculty", False)):
            raise PermissionDenied("Students are not permitted to create announcements.")

        scope = serializer.validated_data.get("scope", AnnouncementScope.INSTITUTION)
        course_offering = serializer.validated_data.get("course_offering")
        department_id = serializer.validated_data.get("department_id")

        if getattr(user, "is_faculty", False) and not getattr(user, "is_admin", False):
            # Faculty can only create course-level announcements for their assigned course offerings
            if not course_offering:
                raise PermissionDenied("Faculty instructors may only create course-level announcements.")
            if str(course_offering.faculty_id) != str(user.user_id):
                raise PermissionDenied("You are not the assigned instructor for this course offering.")

        with transaction.atomic():
            announcement = serializer.save(
                author_user_id=str(user.user_id),
                author_role=str(user.role),
            )
            if announcement.is_published:
                NotificationService.broadcast_announcement(announcement)


class AnnouncementDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/notifications/announcements/<int:pk>/
    PATCH / PUT /api/notifications/announcements/<int:pk>/
    DELETE /api/notifications/announcements/<int:pk>/
    """

    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]
    queryset = Announcement.objects.all()

    def get_object(self):
        announcement = super().get_object()
        user = self.request.user

        if self.request.method == "GET":
            # For GET, verify read permissions
            if getattr(user, "is_admin", False) or announcement.author_user_id == str(user.user_id):
                return announcement

            if not announcement.is_published:
                raise PermissionDenied("This announcement is not published.")

            if getattr(user, "is_faculty", False):
                if announcement.scope == AnnouncementScope.COURSE:
                    if announcement.course_offering and str(announcement.course_offering.faculty_id) != str(user.user_id):
                        raise PermissionDenied("You do not have access to this course announcement.")
            else:
                # Student
                profile = StudentProfile.objects.filter(auth_user_id=str(user.user_id)).first()
                if not profile:
                    raise PermissionDenied("Student profile not found.")
                if announcement.scope == AnnouncementScope.COURSE:
                    is_enrolled = Enrollment.objects.filter(
                        student=profile,
                        course_offering=announcement.course_offering,
                        status=EnrollmentStatus.ENROLLED,
                    ).exists()
                    if not is_enrolled:
                        raise PermissionDenied("You are not enrolled in this course offering.")
                elif announcement.scope == AnnouncementScope.DEPARTMENT:
                    if announcement.department_id != profile.department_id:
                        raise PermissionDenied("You do not belong to this department.")
            return announcement

        # For update/delete, only author or admin
        if not (getattr(user, "is_admin", False) or announcement.author_user_id == str(user.user_id)):
            raise PermissionDenied("Only the announcement author or an administrator can modify or delete it.")

        return announcement

    def perform_update(self, serializer):
        with transaction.atomic():
            was_published = self.get_object().is_published
            announcement = serializer.save()
            # If changed from unpublished to published, broadcast
            if announcement.is_published and not was_published:
                NotificationService.broadcast_announcement(announcement)


class AnnouncementPublishToggleView(APIView):
    """
    POST /api/notifications/announcements/<int:pk>/publish/
    Payload: { "is_published": true/false }
    Toggles publication status of an announcement and broadcasts when published.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        announcement = get_object_or_404(Announcement, pk=pk)
        user = request.user

        if not (getattr(user, "is_admin", False) or announcement.author_user_id == str(user.user_id)):
            raise PermissionDenied("Only the announcement author or an administrator can toggle publication.")

        is_published = request.data.get("is_published")
        if isinstance(is_published, str):
            is_published = is_published.lower() in ("true", "1")
        if is_published is None or not isinstance(is_published, bool):
            raise ValidationError({"is_published": "This field is required and must be a boolean."})

        was_published = announcement.is_published
        announcement.is_published = is_published
        if is_published and not announcement.published_at:
            announcement.published_at = timezone.now()
        announcement.save(update_fields=["is_published", "published_at", "updated_at"])

        if is_published and not was_published:
            NotificationService.broadcast_announcement(announcement)

        return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_200_OK)

