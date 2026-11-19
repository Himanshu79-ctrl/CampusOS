"""
URL configuration for Timetable & Calendar Management in CampusOS LMS (SRS Section 3.E).
"""

from django.urls import path
from .views import (
    CalendarEventDetailView,
    CalendarEventsView,
    CourseOfferingTimetableView,
    FacultyMyTimetableView,
    StudentMyTimetableView,
    TimetableEntryDetailView,
)

app_name = "timetable"

urlpatterns = [
    # Course offering class slots
    path("offerings/<int:offering_id>/", CourseOfferingTimetableView.as_view(), name="offering-timetable"),

    # Individual timetable class slot
    path("entries/<int:pk>/", TimetableEntryDetailView.as_view(), name="entry-detail"),

    # Student & faculty personal timetables
    path("my-timetable/", StudentMyTimetableView.as_view(), name="my-timetable"),
    path("faculty-timetable/", FacultyMyTimetableView.as_view(), name="faculty-timetable"),

    # Calendar events
    path("calendar/", CalendarEventsView.as_view(), name="calendar-list"),
    path("calendar/<int:pk>/", CalendarEventDetailView.as_view(), name="calendar-detail"),
]

