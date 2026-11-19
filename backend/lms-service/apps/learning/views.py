"""
Views for Learning Management & Course Content in CampusOS LMS.
Implements endpoints for Modules, Lessons, Resources, and Student Progress.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import CourseOffering
from .models import CourseModule, Lesson, LearningResource, LessonProgress
from .permissions import CanViewOrManageLearningContent, IsOfferingInstructorOrAdmin
from .serializers import (
    CourseModuleCreateUpdateSerializer,
    CourseModuleSerializer,
    LessonCreateUpdateSerializer,
    LessonDetailSerializer,
    LessonProgressSerializer,
    LearningResourceSerializer,
)
from .services import LearningContentService


class CourseOfferingModulesView(APIView):
    """
    GET /api/learning/offerings/<int:offering_id>/modules/
      - Lists modules for the offering. Enrolled students see published modules only.
      - Instructors and Admins see both draft and published modules.

    POST /api/learning/offerings/<int:offering_id>/modules/
      - Creates a new module within the offering (Instructor or Admin only).
    """

    permission_classes = [CanViewOrManageLearningContent]

    def get(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)
        # Check permissions using service
        access_mode = LearningContentService.check_user_content_access(request.user, offering)
        modules_qs = LearningContentService.get_modules_queryset(request.user, offering)
        serializer = CourseModuleSerializer(modules_qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, offering_id):
        offering = get_object_or_404(CourseOffering, pk=offering_id)
        # Enforce instructor or admin
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, offering):
            raise PermissionDenied("Only the assigned instructor or an administrator can add modules.")

        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["course_offering"] = offering.id

        # Auto-compute order if not provided or if conflicting with existing orders
        existing_orders = set(CourseModule.objects.filter(course_offering=offering).values_list("order", flat=True))
        req_order = data.get("order")
        if req_order is None or req_order in existing_orders:
            max_order = max(existing_orders) if existing_orders else 0
            data["order"] = max_order + 1

        serializer = CourseModuleCreateUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        module = serializer.save()
        return Response(CourseModuleSerializer(module, context={"request": request}).data, status=status.HTTP_201_CREATED)


class CourseModuleDetailView(APIView):
    """
    GET /api/learning/modules/<int:pk>/
    PATCH /api/learning/modules/<int:pk>/
    DELETE /api/learning/modules/<int:pk>/
    """

    permission_classes = [CanViewOrManageLearningContent]

    def get_object(self, pk, request):
        module = get_object_or_404(CourseModule, pk=pk)
        if not CanViewOrManageLearningContent().has_object_permission(request, self, module):
            raise PermissionDenied("You do not have permission to view this module.")
        return module

    def get(self, request, pk):
        module = self.get_object(pk, request)
        serializer = CourseModuleSerializer(module, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        module = self.get_object(pk, request)
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, module):
            raise PermissionDenied("Only the assigned instructor or an administrator can update modules.")

        serializer = CourseModuleCreateUpdateSerializer(module, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(CourseModuleSerializer(updated, context={"request": request}).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        module = self.get_object(pk, request)
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, module):
            raise PermissionDenied("Only the assigned instructor or an administrator can delete modules.")

        module.delete()
        return Response({"message": "Module deleted successfully."}, status=status.HTTP_200_OK)


class CourseModulePublishView(APIView):
    """
    POST /api/learning/modules/<int:pk>/publish/
    Body: {"is_published": true|false, "cascade_lessons": true|false}
    """

    permission_classes = [IsOfferingInstructorOrAdmin]

    def post(self, request, pk):
        module = get_object_or_404(CourseModule, pk=pk)
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, module):
            raise PermissionDenied("Permission denied.")

        is_published = request.data.get("is_published")
        if isinstance(is_published, str):
            is_published = is_published.lower() in ("true", "1")
        if is_published is None or not isinstance(is_published, bool):
            raise ValidationError({"is_published": "This field is required and must be a boolean."})

        cascade = request.data.get("cascade_lessons", False)
        if isinstance(cascade, str):
            cascade = cascade.lower() in ("true", "1")

        updated = LearningContentService.publish_module(module, is_published=is_published, cascade_lessons=bool(cascade))
        return Response(CourseModuleSerializer(updated, context={"request": request}).data, status=status.HTTP_200_OK)


class ModuleLessonsView(APIView):
    """
    POST /api/learning/modules/<int:module_id>/lessons/
    Creates a new lesson in the module (Instructor or Admin only).
    """

    permission_classes = [IsOfferingInstructorOrAdmin]

    def post(self, request, module_id):
        module = get_object_or_404(CourseModule, pk=module_id)
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, module):
            raise PermissionDenied("Permission denied.")

        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["module"] = module.id

        existing_lesson_orders = set(Lesson.objects.filter(module=module).values_list("order", flat=True))
        req_lesson_order = data.get("order")
        if req_lesson_order is None or req_lesson_order in existing_lesson_orders:
            max_order = max(existing_lesson_orders) if existing_lesson_orders else 0
            data["order"] = max_order + 1

        serializer = LessonCreateUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        lesson = serializer.save()
        return Response(LessonDetailSerializer(lesson, context={"request": request}).data, status=status.HTTP_201_CREATED)


class LessonDetailView(APIView):
    """
    GET /api/learning/lessons/<int:pk>/
    PATCH /api/learning/lessons/<int:pk>/
    DELETE /api/learning/lessons/<int:pk>/
    """

    permission_classes = [CanViewOrManageLearningContent]

    def get_object(self, pk, request):
        lesson = get_object_or_404(Lesson, pk=pk)
        if not CanViewOrManageLearningContent().has_object_permission(request, self, lesson):
            raise PermissionDenied("You do not have permission to access this lesson.")
        return lesson

    def get(self, request, pk):
        lesson = self.get_object(pk, request)
        serializer = LessonDetailSerializer(lesson, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        lesson = self.get_object(pk, request)
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, lesson):
            raise PermissionDenied("Only the instructor or admin can update this lesson.")

        serializer = LessonCreateUpdateSerializer(lesson, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(LessonDetailSerializer(updated, context={"request": request}).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        lesson = self.get_object(pk, request)
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, lesson):
            raise PermissionDenied("Only the instructor or admin can delete this lesson.")

        lesson.delete()
        return Response({"message": "Lesson deleted successfully."}, status=status.HTTP_200_OK)


class LessonPublishView(APIView):
    """
    POST /api/learning/lessons/<int:pk>/publish/
    Body: {"is_published": true|false}
    """

    permission_classes = [IsOfferingInstructorOrAdmin]

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, lesson):
            raise PermissionDenied("Permission denied.")

        is_published = request.data.get("is_published")
        if isinstance(is_published, str):
            is_published = is_published.lower() in ("true", "1")
        if is_published is None or not isinstance(is_published, bool):
            raise ValidationError({"is_published": "This field is required and must be a boolean."})

        updated = LearningContentService.publish_lesson(lesson, is_published=is_published)
        return Response(LessonDetailSerializer(updated, context={"request": request}).data, status=status.HTTP_200_OK)


class LessonProgressView(APIView):
    """
    POST /api/learning/lessons/<int:pk>/progress/
    Body: {"is_completed": true|false}
    Enables enrolled students to mark a lesson completed or incomplete.
    """

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        is_completed = request.data.get("is_completed", True)
        if isinstance(is_completed, str):
            is_completed = is_completed.lower() in ("true", "1")

        progress = LearningContentService.record_lesson_progress(request.user, lesson, is_completed=bool(is_completed))
        return Response(LessonProgressSerializer(progress).data, status=status.HTTP_200_OK)


class LessonResourcesView(APIView):
    """
    POST /api/learning/lessons/<int:lesson_id>/resources/
    Accepts multipart/form-data for file uploads or JSON for external links.
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsOfferingInstructorOrAdmin]

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, pk=lesson_id)
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, lesson):
            raise PermissionDenied("Permission denied.")

        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["lesson"] = lesson.id
        data["module"] = lesson.module_id

        if "order" not in data or data["order"] is None:
            max_order = LearningResource.objects.filter(lesson=lesson).count()
            data["order"] = max_order + 1

        serializer = LearningResourceSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        resource = serializer.save()
        return Response(LearningResourceSerializer(resource, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ModuleResourcesView(APIView):
    """
    POST /api/learning/modules/<int:module_id>/resources/
    Attaches a resource directly at the module level.
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsOfferingInstructorOrAdmin]

    def post(self, request, module_id):
        module = get_object_or_404(CourseModule, pk=module_id)
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, module):
            raise PermissionDenied("Permission denied.")

        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["module"] = module.id

        if "order" not in data or data["order"] is None:
            max_order = LearningResource.objects.filter(module=module, lesson__isnull=True).count()
            data["order"] = max_order + 1

        serializer = LearningResourceSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        resource = serializer.save()
        return Response(LearningResourceSerializer(resource, context={"request": request}).data, status=status.HTTP_201_CREATED)


class LearningResourceDetailView(APIView):
    """
    GET /api/learning/resources/<int:pk>/
    DELETE /api/learning/resources/<int:pk>/
    """

    permission_classes = [CanViewOrManageLearningContent]

    def get_object(self, pk, request):
        resource = get_object_or_404(LearningResource, pk=pk)
        if not CanViewOrManageLearningContent().has_object_permission(request, self, resource):
            raise PermissionDenied("You do not have permission to access this resource.")
        return resource

    def get(self, request, pk):
        resource = self.get_object(pk, request)
        serializer = LearningResourceSerializer(resource, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        resource = self.get_object(pk, request)
        if not IsOfferingInstructorOrAdmin().has_object_permission(request, self, resource):
            raise PermissionDenied("Only the instructor or admin can delete this resource.")

        resource.delete()
        return Response({"message": "Resource deleted successfully."}, status=status.HTTP_200_OK)

