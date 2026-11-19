"""
Service layer for Reports & Analytics in CampusOS LMS (SRS Section 3.16 / 3.H).
Performs database aggregations, statistical calculations, and CSV/JSON export generation.
"""

import csv
import io
import logging
from decimal import Decimal
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.utils import timezone

from apps.academics.models import (
    AcademicTerm,
    CourseOffering,
    Enrollment,
    EnrollmentStatus,
    OfferingStatus,
    TermStatus,
)
from apps.assignments.models import Assignment, AssignmentSubmission, SubmissionStatus
from apps.attendance.models import AttendanceRecord, AttendanceSession, AttendanceStatus
from apps.grades.models import FinalCourseGrade, GradeItem, GradeRecord
from apps.learning.models import CourseModule, LearningResource, Lesson
from apps.students.models import StudentProfile

logger = logging.getLogger(__name__)


class ReportService:
    """
    Business logic coordinator for institutional, departmental, course-level,
    and attendance reports, as well as CSV/JSON data export generation.
    """

    @classmethod
    def get_admin_overview(cls, term_id: int = None, department_id: str = None) -> dict:
        """
        Generates high-level institutional KPI overview.
        Filters by academic term and/or department if specified.
        """
        # 1. Term information
        active_term = AcademicTerm.objects.filter(status=TermStatus.ACTIVE).first()
        selected_term = None
        if term_id:
            selected_term = AcademicTerm.objects.filter(id=term_id).first()
            if not selected_term:
                raise ValidationError({"term_id": f"Academic term with ID {term_id} does not exist."})

        effective_term = selected_term or active_term

        # Parse department filter to support single ID, code, or comma-separated cross-service identifiers
        dept_list = None
        if department_id:
            dept_list = [d.strip() for d in str(department_id).split(",") if d.strip()]

        # 2. Student metrics
        students_qs = StudentProfile.objects.all()
        if dept_list:
            students_qs = students_qs.filter(department_id__in=dept_list)

        total_students = students_qs.count()
        active_students = students_qs.filter(is_active=True).count()
        inactive_students = total_students - active_students

        # 3. Course offerings metrics
        offerings_qs = CourseOffering.objects.all()
        if effective_term:
            offerings_qs = offerings_qs.filter(academic_term=effective_term)
        if dept_list:
            offerings_qs = offerings_qs.filter(department_id__in=dept_list)

        total_offerings = offerings_qs.count()
        published_offerings = offerings_qs.filter(status=OfferingStatus.PUBLISHED).count()
        draft_offerings = offerings_qs.filter(status=OfferingStatus.DRAFT).count()
        completed_offerings = offerings_qs.filter(status=OfferingStatus.COMPLETED).count()

        # Faculty count teaching these offerings
        active_faculty_count = offerings_qs.values("faculty_id").distinct().count()

        # 4. Enrollment metrics
        enrollments_qs = Enrollment.objects.filter(course_offering__in=offerings_qs)
        total_enrollments = enrollments_qs.count()
        active_enrollments = enrollments_qs.filter(status=EnrollmentStatus.ENROLLED).count()
        dropped_enrollments = enrollments_qs.filter(status=EnrollmentStatus.DROPPED).count()
        completed_enrollments = enrollments_qs.filter(status=EnrollmentStatus.COMPLETED).count()

        # 5. Attendance metrics
        sessions_qs = AttendanceSession.objects.filter(course_offering__in=offerings_qs)
        total_sessions = sessions_qs.count()

        attendance_records_qs = AttendanceRecord.objects.filter(session__in=sessions_qs)
        total_attendance_records = attendance_records_qs.count()
        present_count = attendance_records_qs.filter(status=AttendanceStatus.PRESENT).count()
        late_count = attendance_records_qs.filter(status=AttendanceStatus.LATE).count()
        absent_count = attendance_records_qs.filter(status=AttendanceStatus.ABSENT).count()

        if total_attendance_records > 0:
            overall_attendance_rate = round(((present_count + late_count) / total_attendance_records) * 100, 2)
        else:
            overall_attendance_rate = 0.0

        # 6. Assignment metrics
        assignments_qs = Assignment.objects.filter(course_offering__in=offerings_qs)
        total_assignments = assignments_qs.count()
        published_assignments = assignments_qs.filter(is_published=True).count()

        submissions_qs = AssignmentSubmission.objects.filter(assignment__in=assignments_qs)
        total_submissions = submissions_qs.count()
        graded_submissions = submissions_qs.filter(status=SubmissionStatus.GRADED).count()
        late_submissions = submissions_qs.filter(is_late=True).count()

        # 7. Gradebook & Results metrics
        grade_items_qs = GradeItem.objects.filter(course_offering__in=offerings_qs)
        total_grade_items = grade_items_qs.count()
        published_grade_items = grade_items_qs.filter(is_published=True).count()

        grade_records_qs = GradeRecord.objects.filter(grade_item__in=grade_items_qs, is_published=True)
        published_records_count = grade_records_qs.count()

        final_grades_qs = FinalCourseGrade.objects.filter(course_offering__in=offerings_qs, is_published=True)
        final_grades_count = final_grades_qs.count()

        return {
            "filters_applied": {
                "term_id": effective_term.id if effective_term else None,
                "term_name": effective_term.name if effective_term else None,
                "department_id": department_id,
            },
            "institution_metrics": {
                "total_students": total_students,
                "active_students": active_students,
                "inactive_students": inactive_students,
                "total_course_offerings": total_offerings,
                "published_course_offerings": published_offerings,
                "draft_course_offerings": draft_offerings,
                "completed_course_offerings": completed_offerings,
                "active_faculty_count": active_faculty_count,
                "total_enrollments": total_enrollments,
                "active_enrollments": active_enrollments,
                "dropped_enrollments": dropped_enrollments,
                "completed_enrollments": completed_enrollments,
            },
            "attendance_overview": {
                "total_sessions": total_sessions,
                "total_records": total_attendance_records,
                "present_count": present_count,
                "late_count": late_count,
                "absent_count": absent_count,
                "overall_attendance_rate": overall_attendance_rate,
            },
            "assignments_overview": {
                "total_assignments": total_assignments,
                "published_assignments": published_assignments,
                "total_submissions": total_submissions,
                "graded_submissions": graded_submissions,
                "late_submissions": late_submissions,
            },
            "grades_overview": {
                "total_grade_items": total_grade_items,
                "published_grade_items": published_grade_items,
                "published_grade_records": published_records_count,
                "finalized_course_grades": final_grades_count,
            },
            "external_integrations": {
                "exam_engine": {
                    "status": "PENDING_INTEGRATION",
                    "message": "Exam engine integration is handled by the Exam Engine team. External exam scores ingest via GradeItem sync.",
                },
                "proctoring": {
                    "status": "UNAVAILABLE",
                    "message": "Live proctoring integration is handled externally and not configured in LMS.",
                },
            },
        }

    @classmethod
    def get_admin_students(
        cls,
        department_id: str = None,
        admission_year: int = None,
        current_semester: int = None,
        is_active: bool = None,
        search: str = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """
        Generates student performance, enrollment, and demographic report for administrators.
        """
        qs = StudentProfile.objects.all().order_by("registration_number")

        if department_id:
            dept_list = [d.strip() for d in str(department_id).split(",") if d.strip()]
            qs = qs.filter(department_id__in=dept_list)
        if admission_year:
            qs = qs.filter(admission_year=admission_year)
        if current_semester:
            qs = qs.filter(current_semester=current_semester)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if search:
            qs = qs.filter(
                Q(registration_number__icontains=search.strip())
                | Q(auth_user_id__icontains=search.strip())
            )

        total_count = qs.count()

        # Pagination slice
        try:
            page = max(1, int(page))
            page_size = max(1, min(100, int(page_size)))
        except (ValueError, TypeError):
            page, page_size = 1, 20

        start = (page - 1) * page_size
        end = start + page_size
        students_page = qs[start:end]

        results = []
        for s in students_page:
            # Enrollments
            active_enrollments = Enrollment.objects.filter(student=s, status=EnrollmentStatus.ENROLLED).count()

            # Attendance
            records = AttendanceRecord.objects.filter(student=s)
            total_sessions = records.count()
            attended = records.filter(status__in=[AttendanceStatus.PRESENT, AttendanceStatus.LATE]).count()
            att_pct = round((attended / total_sessions * 100), 2) if total_sessions > 0 else None

            # Assignments
            submissions = AssignmentSubmission.objects.filter(student=s)
            submitted_count = submissions.count()
            graded_count = submissions.filter(status=SubmissionStatus.GRADED).count()

            # Grades
            grades = GradeRecord.objects.filter(student=s, is_published=True, marks_obtained__isnull=False)
            scores = []
            for g in grades.select_related("grade_item"):
                if g.grade_item.max_marks > Decimal("0.00"):
                    scores.append((float(g.marks_obtained) / float(g.grade_item.max_marks)) * 100.0)

            avg_score = round(sum(scores) / len(scores), 2) if scores else None

            results.append({
                "student_id": s.id,
                "auth_user_id": s.auth_user_id,
                "registration_number": s.registration_number,
                "department_id": s.department_id,
                "admission_year": s.admission_year,
                "current_semester": s.current_semester,
                "is_active": s.is_active,
                "enrolled_courses_count": active_enrollments,
                "attendance": {
                    "total_sessions": total_sessions,
                    "attended_sessions": attended,
                    "attendance_percentage": att_pct,
                },
                "assignments": {
                    "submitted_count": submitted_count,
                    "graded_count": graded_count,
                },
                "grades": {
                    "published_records_count": len(scores),
                    "average_score_percentage": avg_score,
                },
            })

        return {
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 1,
            "results": results,
        }

    @classmethod
    def get_department_report(cls, department_id: str, term_id: int = None) -> dict:
        """
        Generates department-level academic report for HOD / Administrators.
        """
        if not department_id or not str(department_id).strip():
            raise ValidationError({"department_id": "Department ID is required."})

        dept_list = [d.strip() for d in str(department_id).split(",") if d.strip()]
        dept_id = dept_list[0] if dept_list else str(department_id).strip()

        # Students in department
        students_qs = StudentProfile.objects.filter(department_id__in=dept_list)
        total_students = students_qs.count()
        active_students = students_qs.filter(is_active=True).count()

        # Semester distribution
        semester_breakdown = list(
            students_qs.values("current_semester")
            .annotate(count=Count("id"))
            .order_by("current_semester")
        )

        # Course offerings in department
        offerings_qs = CourseOffering.objects.filter(department_id__in=dept_list)
        if term_id:
            offerings_qs = offerings_qs.filter(academic_term_id=term_id)

        total_offerings = offerings_qs.count()
        published_offerings = offerings_qs.filter(status=OfferingStatus.PUBLISHED).count()
        assigned_faculty_count = offerings_qs.values("faculty_id").distinct().count()

        enrollments_qs = Enrollment.objects.filter(course_offering__in=offerings_qs)
        total_enrollments = enrollments_qs.count()
        active_enrollments = enrollments_qs.filter(status=EnrollmentStatus.ENROLLED).count()

        # Attendance in department offerings
        dept_sessions = AttendanceSession.objects.filter(course_offering__in=offerings_qs)
        total_sessions = dept_sessions.count()

        dept_records = AttendanceRecord.objects.filter(session__in=dept_sessions)
        total_records = dept_records.count()
        present_count = dept_records.filter(status=AttendanceStatus.PRESENT).count()
        late_count = dept_records.filter(status=AttendanceStatus.LATE).count()
        absent_count = dept_records.filter(status=AttendanceStatus.ABSENT).count()

        avg_attendance_rate = (
            round(((present_count + late_count) / total_records) * 100, 2)
            if total_records > 0
            else 0.0
        )

        # Course breakdown list
        courses_summary = []
        for off in offerings_qs.select_related("academic_term"):
            off_enrolled = Enrollment.objects.filter(course_offering=off, status=EnrollmentStatus.ENROLLED).count()
            off_sessions = AttendanceSession.objects.filter(course_offering=off)
            off_records = AttendanceRecord.objects.filter(session__in=off_sessions)
            off_total_rec = off_records.count()
            off_pres = off_records.filter(status__in=[AttendanceStatus.PRESENT, AttendanceStatus.LATE]).count()
            off_att_rate = round(off_pres / off_total_rec * 100, 2) if off_total_rec > 0 else None

            courses_summary.append({
                "offering_id": off.id,
                "course_id": off.course_id,
                "section": off.section,
                "faculty_id": off.faculty_id,
                "term_name": off.academic_term.name if off.academic_term else "",
                "capacity": off.capacity,
                "enrolled_count": off_enrolled,
                "status": off.status,
                "sessions_conducted": off_sessions.count(),
                "attendance_rate": off_att_rate,
            })

        return {
            "department_id": dept_id,
            "students_summary": {
                "total_students": total_students,
                "active_students": active_students,
                "semester_distribution": semester_breakdown,
            },
            "offerings_summary": {
                "total_offerings": total_offerings,
                "published_offerings": published_offerings,
                "assigned_faculty_count": assigned_faculty_count,
                "total_enrollments": total_enrollments,
                "active_enrollments": active_enrollments,
            },
            "attendance_analytics": {
                "total_sessions": total_sessions,
                "total_records": total_records,
                "present_count": present_count,
                "late_count": late_count,
                "absent_count": absent_count,
                "average_attendance_rate": avg_attendance_rate,
            },
            "courses_breakdown": courses_summary,
            "external_integrations": {
                "exam_engine": {
                    "status": "PENDING_INTEGRATION",
                    "message": "Exam engine integration is handled by the Exam Engine team.",
                },
                "proctoring": {
                    "status": "UNAVAILABLE",
                    "message": "Live proctoring integration is handled externally and not configured in LMS.",
                },
            },
        }

    @classmethod
    def get_course_report(cls, course_offering: CourseOffering) -> dict:
        """
        Generates in-depth course offering performance and progress analytics.
        """
        # 1. Enrollments
        enrolled_students = Enrollment.objects.filter(
            course_offering=course_offering,
            status=EnrollmentStatus.ENROLLED,
        ).select_related("student")
        total_enrolled = enrolled_students.count()

        occupancy_rate = (
            round((total_enrolled / course_offering.capacity) * 100, 2)
            if course_offering.capacity > 0
            else 0.0
        )
        dropped_count = Enrollment.objects.filter(
            course_offering=course_offering,
            status=EnrollmentStatus.DROPPED,
        ).count()
        completed_count = Enrollment.objects.filter(
            course_offering=course_offering,
            status=EnrollmentStatus.COMPLETED,
        ).count()

        # 2. Attendance
        sessions = AttendanceSession.objects.filter(course_offering=course_offering)
        total_sessions = sessions.count()

        records = AttendanceRecord.objects.filter(session__in=sessions)
        total_records = records.count()
        present_count = records.filter(status=AttendanceStatus.PRESENT).count()
        late_count = records.filter(status=AttendanceStatus.LATE).count()
        absent_count = records.filter(status=AttendanceStatus.ABSENT).count()

        avg_attendance_rate = (
            round(((present_count + late_count) / total_records) * 100, 2)
            if total_records > 0
            else 0.0
        )

        # Count at-risk students (< 75% attendance)
        at_risk_count = 0
        if total_sessions > 0:
            for enr in enrolled_students:
                stu_recs = records.filter(student=enr.student)
                stu_att = stu_recs.filter(status__in=[AttendanceStatus.PRESENT, AttendanceStatus.LATE]).count()
                stu_rate = (stu_att / total_sessions) * 100
                if stu_rate < 75.0:
                    at_risk_count += 1

        # 3. Learning Materials
        modules_count = CourseModule.objects.filter(course_offering=course_offering).count()
        lessons_count = Lesson.objects.filter(module__course_offering=course_offering).count()
        resources_count = LearningResource.objects.filter(module__course_offering=course_offering).count()

        # 4. Assignments
        assignments = Assignment.objects.filter(course_offering=course_offering).order_by("created_at")
        total_assignments = assignments.count()
        assignments_summary = []
        for a in assignments:
            subs = AssignmentSubmission.objects.filter(assignment=a)
            sub_count = subs.count()
            graded_subs = subs.filter(status=SubmissionStatus.GRADED)
            graded_count = graded_subs.count()

            avg_marks = graded_subs.aggregate(avg=Avg("marks_obtained"))["avg"]
            assignments_summary.append({
                "assignment_id": a.id,
                "title": a.title,
                "max_marks": float(a.max_marks),
                "is_published": a.is_published,
                "submissions_count": sub_count,
                "graded_count": graded_count,
                "average_marks": round(float(avg_marks), 2) if avg_marks is not None else None,
            })

        # 5. Grades & Final Results
        grade_items = GradeItem.objects.filter(course_offering=course_offering)
        total_grade_items = grade_items.count()
        published_grade_items = grade_items.filter(is_published=True).count()

        final_grades = FinalCourseGrade.objects.filter(course_offering=course_offering, is_published=True)
        final_grades_count = final_grades.count()

        letter_grade_dist = dict(
            final_grades.values("final_letter_grade")
            .annotate(count=Count("id"))
            .values_list("final_letter_grade", "count")
        )

        return {
            "course_offering": {
                "id": course_offering.id,
                "course_id": course_offering.course_id,
                "faculty_id": course_offering.faculty_id,
                "department_id": course_offering.department_id,
                "section": course_offering.section,
                "term_name": course_offering.academic_term.name if course_offering.academic_term else "",
                "capacity": course_offering.capacity,
                "status": course_offering.status,
            },
            "enrollment_analytics": {
                "total_enrolled": total_enrolled,
                "capacity": course_offering.capacity,
                "occupancy_rate_percentage": occupancy_rate,
                "dropped_count": dropped_count,
                "completed_count": completed_count,
            },
            "attendance_analytics": {
                "total_sessions_conducted": total_sessions,
                "total_records": total_records,
                "present_count": present_count,
                "late_count": late_count,
                "absent_count": absent_count,
                "average_attendance_percentage": avg_attendance_rate,
                "at_risk_students_count": at_risk_count,
            },
            "learning_content_summary": {
                "modules_count": modules_count,
                "lessons_count": lessons_count,
                "resources_count": resources_count,
            },
            "assignments_analytics": {
                "total_assignments": total_assignments,
                "breakdown": assignments_summary,
            },
            "gradebook_analytics": {
                "total_grade_items": total_grade_items,
                "published_grade_items": published_grade_items,
                "finalized_grades_count": final_grades_count,
                "letter_grade_distribution": letter_grade_dist,
            },
            "external_integrations": {
                "exam_engine": {
                    "status": "PENDING_INTEGRATION",
                    "message": "External exam scores are ingested via GradeItem external_exam_id synchronization.",
                },
            },
        }

    @classmethod
    def get_attendance_report(
        cls,
        user,
        course_offering_id: int = None,
        department_id: str = None,
        start_date=None,
        end_date=None,
        threshold: float = None,
    ) -> dict:
        """
        Generates role-scoped attendance report:
          - Students: their personal subject-wise attendance summary.
          - Faculty: attendance breakdown for their assigned offerings.
          - Administrators: institution/department/course attendance analytics.
        """
        # Student personal view
        if getattr(user, "is_student", False):
            profile = StudentProfile.objects.filter(auth_user_id=str(user.user_id)).first()
            if not profile:
                raise ValidationError("Student profile not found.")

            enrollments = Enrollment.objects.filter(student=profile, status=EnrollmentStatus.ENROLLED).select_related(
                "course_offering", "course_offering__academic_term"
            )
            if course_offering_id:
                enrollments = enrollments.filter(course_offering_id=course_offering_id)

            subject_breakdown = []
            total_all_sessions = 0
            total_all_attended = 0

            for enr in enrollments:
                off = enr.course_offering
                sessions = AttendanceSession.objects.filter(course_offering=off)
                if start_date and end_date:
                    sessions = sessions.filter(session_date__range=[start_date, end_date])

                sess_count = sessions.count()
                records = AttendanceRecord.objects.filter(session__in=sessions, student=profile)
                pres_count = records.filter(status=AttendanceStatus.PRESENT).count()
                late_count = records.filter(status=AttendanceStatus.LATE).count()
                abs_count = records.filter(status=AttendanceStatus.ABSENT).count()
                att_count = pres_count + late_count

                att_pct = round((att_count / sess_count * 100), 2) if sess_count > 0 else None

                total_all_sessions += sess_count
                total_all_attended += att_count

                subject_breakdown.append({
                    "course_offering_id": off.id,
                    "course_id": off.course_id,
                    "section": off.section,
                    "term_name": off.academic_term.name if off.academic_term else "",
                    "total_sessions": sess_count,
                    "present_count": pres_count,
                    "late_count": late_count,
                    "absent_count": abs_count,
                    "attendance_percentage": att_pct,
                })

            overall_pct = (
                round((total_all_attended / total_all_sessions * 100), 2)
                if total_all_sessions > 0
                else None
            )

            return {
                "student_registration_number": profile.registration_number,
                "overall_attendance_percentage": overall_pct,
                "total_sessions": total_all_sessions,
                "total_attended": total_all_attended,
                "subjects": subject_breakdown,
            }

        # Faculty / Admin view
        offerings_qs = CourseOffering.objects.all()
        if getattr(user, "is_faculty", False) and not getattr(user, "is_admin", False):
            offerings_qs = offerings_qs.filter(faculty_id=str(user.user_id))

        if course_offering_id:
            offerings_qs = offerings_qs.filter(id=course_offering_id)
            if not offerings_qs.exists():
                raise PermissionDenied("You do not have access to this course offering.")

        if department_id and getattr(user, "is_admin", False):
            offerings_qs = offerings_qs.filter(department_id=department_id)

        sessions_qs = AttendanceSession.objects.filter(course_offering__in=offerings_qs)
        if start_date and end_date:
            sessions_qs = sessions_qs.filter(session_date__range=[start_date, end_date])

        total_sessions = sessions_qs.count()
        records_qs = AttendanceRecord.objects.filter(session__in=sessions_qs)
        total_records = records_qs.count()
        present_count = records_qs.filter(status=AttendanceStatus.PRESENT).count()
        late_count = records_qs.filter(status=AttendanceStatus.LATE).count()
        absent_count = records_qs.filter(status=AttendanceStatus.ABSENT).count()

        overall_pct = (
            round(((present_count + late_count) / total_records) * 100, 2)
            if total_records > 0
            else 0.0
        )

        # Roster student breakdown if single course offering requested
        roster_data = []
        if course_offering_id:
            offering = offerings_qs.first()
            enrolled = Enrollment.objects.filter(
                course_offering=offering, status=EnrollmentStatus.ENROLLED
            ).select_related("student")

            for enr in enrolled:
                stu = enr.student
                stu_recs = records_qs.filter(student=stu)
                s_tot = total_sessions
                s_pres = stu_recs.filter(status=AttendanceStatus.PRESENT).count()
                s_late = stu_recs.filter(status=AttendanceStatus.LATE).count()
                s_abs = stu_recs.filter(status=AttendanceStatus.ABSENT).count()
                s_att = s_pres + s_late
                s_pct = round((s_att / s_tot * 100), 2) if s_tot > 0 else 0.0

                is_below = False
                if threshold is not None:
                    is_below = s_pct < float(threshold)

                if threshold is None or is_below:
                    roster_data.append({
                        "student_id": stu.id,
                        "registration_number": stu.registration_number,
                        "auth_user_id": stu.auth_user_id,
                        "total_sessions": s_tot,
                        "present_count": s_pres,
                        "late_count": s_late,
                        "absent_count": s_abs,
                        "attendance_percentage": s_pct,
                        "below_threshold": is_below,
                    })

        return {
            "summary": {
                "course_offering_id": course_offering_id,
                "total_sessions": total_sessions,
                "total_records": total_records,
                "present_count": present_count,
                "late_count": late_count,
                "absent_count": absent_count,
                "overall_attendance_rate": overall_pct,
            },
            "roster": roster_data,
        }

    @classmethod
    def generate_export(cls, user, report_type: str, export_format: str = "csv", **params) -> tuple[str, str, str]:
        """
        Generates exported report data.
        Returns (content: str, content_type: str, filename: str).
        """
        valid_types = ["admin_overview", "admin_students", "department", "course", "attendance"]
        if report_type not in valid_types:
            raise ValidationError(
                {"type": f"Invalid report type '{report_type}'. Allowed types: {', '.join(valid_types)}"}
            )

        fmt = export_format.lower()
        if fmt not in ("csv", "json"):
            raise ValidationError({"format": f"Invalid format '{export_format}'. Allowed formats: 'csv', 'json'."})

        # 1. Enforce RBAC per report type
        if report_type in ("admin_overview", "admin_students") and not getattr(user, "is_admin", False):
            raise PermissionDenied(f"Administrator privileges are required to export '{report_type}'.")

        if report_type == "department":
            dept_id = params.get("department_id")
            if not getattr(user, "is_admin", False):
                user_dept = getattr(user, "department_id", "") or user.claims.get("department_id", "")
                if not (getattr(user, "is_faculty", False) and user_dept and str(user_dept) == str(dept_id)):
                    raise PermissionDenied("You do not have permission to export this department's reports.")
                from apps.academics.admin_client import AdminServiceClient

                admin_client = AdminServiceClient()
                if not admin_client.is_department_hod(user, user_dept):
                    raise PermissionDenied("Only the designated Department Head (HOD) may export this department's reports.")

        if report_type == "course":
            offering_id = params.get("course_offering_id")
            if not offering_id:
                raise ValidationError({"course_offering_id": "course_offering_id is required to export course report."})
            offering = CourseOffering.objects.filter(id=offering_id).first()
            if not offering:
                raise ValidationError({"course_offering_id": "Course offering does not exist."})
            if not getattr(user, "is_admin", False):
                if not (getattr(user, "is_faculty", False) and str(offering.faculty_id) == str(user.user_id)):
                    raise PermissionDenied("You are not the assigned instructor for this course offering.")

        # 2. Fetch data
        if report_type == "admin_overview":
            data = cls.get_admin_overview(
                term_id=params.get("term_id"),
                department_id=params.get("department_id"),
            )
            filename = f"admin_overview_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        elif report_type == "admin_students":
            data = cls.get_admin_students(
                department_id=params.get("department_id"),
                admission_year=params.get("admission_year"),
                current_semester=params.get("current_semester"),
                is_active=params.get("is_active"),
                search=params.get("search"),
                page=1,
                page_size=1000,
            )
            filename = f"students_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        elif report_type == "department":
            data = cls.get_department_report(
                department_id=params.get("department_id"),
                term_id=params.get("term_id"),
            )
            filename = f"department_{params.get('department_id')}_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        elif report_type == "course":
            offering = CourseOffering.objects.get(id=params.get("course_offering_id"))
            data = cls.get_course_report(offering)
            filename = f"course_{offering.id}_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        elif report_type == "attendance":
            data = cls.get_attendance_report(
                user=user,
                course_offering_id=params.get("course_offering_id"),
                department_id=params.get("department_id"),
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                threshold=params.get("threshold"),
            )
            filename = f"attendance_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        # 3. Format
        if fmt == "json":
            import json
            return json.dumps(data, indent=2, default=str), "application/json", f"{filename}.json"

        # CSV formatting
        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == "admin_students":
            writer.writerow([
                "Student ID", "Registration Number", "Auth User ID", "Department ID",
                "Admission Year", "Semester", "Active", "Enrolled Courses",
                "Attendance %", "Published Grades Count", "Average Score %"
            ])
            for r in data.get("results", []):
                writer.writerow([
                    r["student_id"],
                    r["registration_number"],
                    r["auth_user_id"],
                    r["department_id"],
                    r["admission_year"],
                    r["current_semester"],
                    "Yes" if r["is_active"] else "No",
                    r["enrolled_courses_count"],
                    f"{r['attendance']['attendance_percentage']}%" if r['attendance']['attendance_percentage'] is not None else "N/A",
                    r["grades"]["published_records_count"],
                    f"{r['grades']['average_score_percentage']}%" if r['grades']['average_score_percentage'] is not None else "N/A",
                ])

        elif report_type == "admin_overview":
            writer.writerow(["Metric Category", "Metric Name", "Value"])
            for cat, metrics in data.items():
                if isinstance(metrics, dict):
                    for k, v in metrics.items():
                        writer.writerow([cat.replace("_", " ").title(), k.replace("_", " ").title(), v])

        elif report_type == "department":
            writer.writerow(["Department Report", data.get("department_id", "")])
            writer.writerow([])
            writer.writerow(["Course Offerings Breakdown"])
            writer.writerow(["Offering ID", "Course ID", "Section", "Faculty ID", "Capacity", "Enrolled", "Attendance Rate %"])
            for c in data.get("courses_breakdown", []):
                writer.writerow([
                    c["offering_id"], c["course_id"], c["section"], c["faculty_id"],
                    c["capacity"], c["enrolled_count"], f"{c['attendance_rate']}%" if c["attendance_rate"] is not None else "N/A"
                ])

        elif report_type == "course":
            off = data.get("course_offering", {})
            writer.writerow(["Course Report", f"{off.get('course_id')} - Section {off.get('section')}"])
            writer.writerow([])
            writer.writerow(["Category", "Metric", "Value"])
            for section in ["enrollment_analytics", "attendance_analytics", "learning_content_summary"]:
                for k, v in data.get(section, {}).items():
                    writer.writerow([section.replace("_", " ").title(), k.replace("_", " ").title(), v])

            writer.writerow([])
            writer.writerow(["Assignment Title", "Max Marks", "Submissions", "Graded", "Average Marks"])
            for a in data.get("assignments_analytics", {}).get("breakdown", []):
                writer.writerow([a["title"], a["max_marks"], a["submissions_count"], a["graded_count"], a["average_marks"]])

        elif report_type == "attendance":
            if "subjects" in data:
                # Student personal report
                writer.writerow(["Course ID", "Section", "Term", "Total Sessions", "Present", "Late", "Absent", "Attendance %"])
                for s in data.get("subjects", []):
                    writer.writerow([
                        s["course_id"], s["section"], s["term_name"], s["total_sessions"],
                        s["present_count"], s["late_count"], s["absent_count"],
                        f"{s['attendance_percentage']}%" if s['attendance_percentage'] is not None else "N/A"
                    ])
            else:
                # Faculty/Admin roster view
                writer.writerow(["Student ID", "Registration Number", "Total Sessions", "Present", "Late", "Absent", "Attendance %", "Below Threshold"])
                for r in data.get("roster", []):
                    writer.writerow([
                        r["student_id"], r["registration_number"], r["total_sessions"],
                        r["present_count"], r["late_count"], r["absent_count"],
                        f"{r['attendance_percentage']}%", "Yes" if r.get("below_threshold") else "No"
                    ])

        return output.getvalue(), "text/csv", f"{filename}.csv"
