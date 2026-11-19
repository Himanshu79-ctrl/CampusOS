"""
Models for Reports & Analytics in CampusOS LMS.

Reports and Analytics aggregates data dynamically from existing academic collections:
- StudentProfile (apps.students)
- AcademicTerm, CourseOffering, Enrollment (apps.academics)
- CourseModule, Lesson, LearningResource (apps.learning)
- Assignment, AssignmentSubmission (apps.assignments)
- AttendanceSession, AttendanceRecord (apps.attendance)
- TimetableEntry, CalendarEvent (apps.timetable)
- GradeItem, GradeRecord, FinalCourseGrade (apps.grades)
- Announcement, Notification (apps.notifications)

No separate database tables are duplicated or created for reporting.
"""

