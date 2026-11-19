"""
URL configuration for CampusOS LMS service.
"""

from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve
from config.views import HealthCheckView

urlpatterns = [
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/students/", include("apps.students.urls", namespace="students")),
    path("api/academics/", include("apps.academics.urls", namespace="academics")),
    path("api/learning/", include("apps.learning.urls", namespace="learning")),
    path("api/assignments/", include("apps.assignments.urls", namespace="assignments")),
    path("api/attendance/", include("apps.attendance.urls", namespace="attendance")),
    path("api/timetable/", include("apps.timetable.urls", namespace="timetable")),
    path("api/grades/", include("apps.grades.urls", namespace="grades")),
    path("api/notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("api/reports/", include("apps.reports.urls", namespace="reports")),
    path("api/admin/reports/", include("apps.reports.admin_urls")),
    path("api/hod/reports/", include("apps.reports.hod_urls")),
    path("api/faculty/reports/", include("apps.reports.faculty_urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
