"""
Service layer for Attendance Management in CampusOS LMS.
Encapsulates business rules for session creation, student enrollment eligibility,
bulk/individual attendance marking, audit-logged corrections, course-wise report generation,
and student attendance summaries (SRS Section 3.D).
"""

from datetime import date
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q

from apps.academics.models import CourseOffering, Enrollment, EnrollmentStatus
from apps.students.models import StudentProfile
from .models import AttendanceRecord, AttendanceSession, AttendanceStatus


class AttendanceService:
    """
    Business logic coordinator for Attendance Sessions, Attendance Records,
    Audited Corrections, and Course Attendance Reports.
    """

    @classmethod
    def check_faculty_or_admin_permission(cls, user, course_offering: CourseOffering) -> None:
        """
        Validates that the requesting user is either an academic administrator
        or the assigned instructor for the specified CourseOffering.
        """
        if getattr(user, "is_admin", False):
            return

        if getattr(user, "is_faculty", False):
            from apps.academics.faculty_matcher import is_faculty_assigned
            if is_faculty_assigned(user, course_offering.faculty_id):
                return
            raise PermissionDenied("You are not the assigned instructor for this course offering.")

        raise PermissionDenied("Only faculty instructors or administrators can manage attendance.")

    @classmethod
    def create_session(
        cls,
        user,
        course_offering: CourseOffering,
        session_date: date,
        title: str = "",
        start_time=None,
        end_time=None,
        description: str = "",
        initial_records: list = None,
    ) -> AttendanceSession:
        """
        Creates an attendance session for a CourseOffering.
        Optionally accepts a list of initial student attendance records to mark atomically.
        """
        cls.check_faculty_or_admin_permission(user, course_offering)

        # Handle duplicate session gracefully: check for existing session on same offering, date, and title
        existing_qs = AttendanceSession.objects.filter(
            course_offering=course_offering,
            session_date=session_date,
            title=title.strip(),
        )
        if start_time:
            existing_qs = existing_qs.filter(start_time=start_time)
        existing_session = existing_qs.first()
        if existing_session:
            if initial_records:
                cls.mark_or_update_session_records(
                    user=user,
                    session=existing_session,
                    records_data=initial_records,
                )
            return existing_session

        with transaction.atomic():
            session = AttendanceSession(
                course_offering=course_offering,
                session_date=session_date,
                title=title.strip(),
                start_time=start_time,
                end_time=end_time,
                description=description.strip(),
                created_by_faculty_id=str(user.user_id),
            )
            session.save()

            if initial_records:
                cls.mark_or_update_session_records(
                    user=user,
                    session=session,
                    records_data=initial_records,
                )
            else:
                # Automatically populate roster for actively enrolled students as PRESENT
                enrolled_student_ids = list(
                    Enrollment.objects.filter(
                        course_offering=course_offering,
                        status=EnrollmentStatus.ENROLLED,
                    ).values_list("student_id", flat=True)
                )
                if enrolled_student_ids:
                    auto_records = [
                        {"student_id": sid, "status": AttendanceStatus.PRESENT}
                        for sid in enrolled_student_ids
                    ]
                    cls.mark_or_update_session_records(
                        user=user,
                        session=session,
                        records_data=auto_records,
                    )

            return session

    @classmethod
    def mark_or_update_session_records(
        cls,
        user,
        session: AttendanceSession,
        records_data: list,
        default_audit_reason: str = "",
    ) -> list[AttendanceRecord]:
        """
        Marks or updates attendance records for enrolled students in a session.
        Enforces:
          - Assigned faculty or admin permission.
          - Student must be actively enrolled in the session's CourseOffering.
          - Valid AttendanceStatus choice (PRESENT, ABSENT, LATE).
          - Audit tracking when records are updated/corrected.
        """
        cls.check_faculty_or_admin_permission(user, session.course_offering)

        # Pre-fetch actively enrolled students for this course offering
        enrolled_student_ids = set(
            Enrollment.objects.filter(
                course_offering=session.course_offering,
                status=EnrollmentStatus.ENROLLED,
            ).values_list("student_id", flat=True)
        )

        results = []
        with transaction.atomic():
            for item in records_data:
                student_id = item.get("student_id")
                if not student_id:
                    raise ValidationError("student_id is required for each attendance entry.")

                if student_id not in enrolled_student_ids:
                    raise ValidationError(
                        f"Student ID {student_id} is not actively enrolled in Course Offering #{session.course_offering_id}."
                    )

                new_status = item.get("status", AttendanceStatus.PRESENT)
                if new_status not in AttendanceStatus.values:
                    raise ValidationError(
                        f"Invalid attendance status '{new_status}'. Allowed: {', '.join(AttendanceStatus.values)}"
                    )

                remarks = item.get("remarks", "")
                audit_reason = item.get("audit_reason", default_audit_reason)

                record, created = AttendanceRecord.objects.get_or_create(
                    session=session,
                    student_id=student_id,
                    defaults={
                        "status": new_status,
                        "remarks": remarks,
                        "audit_reason": audit_reason,
                        "recorded_by_user_id": str(user.user_id),
                    },
                )

                if not created:
                    # Update existing record (correction flow)
                    record.status = new_status
                    if remarks:
                        record.remarks = remarks
                    if audit_reason:
                        record.audit_reason = audit_reason
                    record.recorded_by_user_id = str(user.user_id)
                    record.save()

                results.append(record)

            if results:
                try:
                    from apps.notifications.services import trigger_attendance_alert
                    for rec in results:
                        if rec.status in (AttendanceStatus.ABSENT, AttendanceStatus.LATE):
                            trigger_attendance_alert(rec)
                except Exception:
                    pass

        return results

    @classmethod
    def correct_record(
        cls,
        user,
        record: AttendanceRecord,
        new_status: str,
        audit_reason: str,
        remarks: str = None,
    ) -> AttendanceRecord:
        """
        Corrects an existing attendance record with a required audit reason.
        """
        cls.check_faculty_or_admin_permission(user, record.session.course_offering)

        if not audit_reason or not audit_reason.strip():
            raise ValidationError({"audit_reason": "An audit reason is required when correcting an attendance record."})

        if new_status not in AttendanceStatus.values:
            raise ValidationError(
                {"status": f"Invalid status '{new_status}'. Allowed choices: {', '.join(AttendanceStatus.values)}."}
            )

        record.status = new_status
        record.audit_reason = audit_reason.strip()
        record.recorded_by_user_id = str(user.user_id)
        if remarks is not None:
            record.remarks = remarks.strip()
        record.save()
        return record

    @classmethod
    def get_course_attendance_report(
        cls,
        user,
        course_offering: CourseOffering,
        start_date: date = None,
        end_date: date = None,
        threshold: float = None,
    ) -> dict:
        """
        Generates course-wise aggregated attendance report.
        Includes total sessions, student attendance breakdown (present, late, absent),
        and optional configurable threshold flag.
        """
        cls.check_faculty_or_admin_permission(user, course_offering)

        sessions_qs = AttendanceSession.objects.filter(course_offering=course_offering)
        if start_date:
            sessions_qs = sessions_qs.filter(session_date__gte=start_date)
        if end_date:
            sessions_qs = sessions_qs.filter(session_date__lte=end_date)

        total_sessions = sessions_qs.count()
        session_ids = list(sessions_qs.values_list("id", flat=True))

        # Enrolled students
        enrollments = Enrollment.objects.filter(
            course_offering=course_offering,
            status=EnrollmentStatus.ENROLLED,
        ).select_related("student").order_by("student__registration_number")

        student_reports = []
        for enrollment in enrollments:
            student = enrollment.student
            records = AttendanceRecord.objects.filter(session_id__in=session_ids, student=student)

            present_count = records.filter(status=AttendanceStatus.PRESENT).count()
            late_count = records.filter(status=AttendanceStatus.LATE).count()
            absent_count = records.filter(status=AttendanceStatus.ABSENT).count()
            attended_count = present_count + late_count

            percentage = round((attended_count / total_sessions * 100), 2) if total_sessions > 0 else 0.0

            item = {
                "student_id": student.id,
                "auth_user_id": student.auth_user_id,
                "registration_number": student.registration_number,
                "total_sessions": total_sessions,
                "present_count": present_count,
                "late_count": late_count,
                "absent_count": absent_count,
                "attended_count": attended_count,
                "attendance_percentage": percentage,
            }

            if threshold is not None:
                item["below_threshold"] = percentage < float(threshold)

            student_reports.append(item)

        return {
            "course_offering_id": course_offering.id,
            "course_id": course_offering.course_id,
            "section": course_offering.section,
            "faculty_id": course_offering.faculty_id,
            "total_sessions": total_sessions,
            "configurable_threshold": threshold,
            "students": student_reports,
        }

    @classmethod
    def get_student_attendance_summary(
        cls,
        student_profile: StudentProfile,
        course_offering_id: int = None,
    ) -> list[dict]:
        """
        Returns subject-wise attendance percentages for an enrolled student
        across all active course enrollments (or a specific offering).
        """
        enrollments_qs = Enrollment.objects.filter(
            student=student_profile,
            status=EnrollmentStatus.ENROLLED,
        ).select_related("course_offering", "course_offering__academic_term")

        if course_offering_id:
            enrollments_qs = enrollments_qs.filter(course_offering_id=course_offering_id)

        summaries = []
        for enrollment in enrollments_qs:
            offering = enrollment.course_offering
            total_sessions = offering.attendance_sessions.count()

            records = AttendanceRecord.objects.filter(
                session__course_offering=offering,
                student=student_profile,
            )

            present_count = records.filter(status=AttendanceStatus.PRESENT).count()
            late_count = records.filter(status=AttendanceStatus.LATE).count()
            absent_count = records.filter(status=AttendanceStatus.ABSENT).count()
            attended_count = present_count + late_count

            percentage = round((attended_count / total_sessions * 100), 2) if total_sessions > 0 else 0.0

            summaries.append({
                "course_offering_id": offering.id,
                "course_id": offering.course_id,
                "section": offering.section,
                "academic_term": offering.academic_term.name,
                "total_sessions": total_sessions,
                "present_count": present_count,
                "late_count": late_count,
                "absent_count": absent_count,
                "attended_count": attended_count,
                "attendance_percentage": percentage,
            })

        return summaries

    @classmethod
    def get_student_attendance_history(
        cls,
        student_profile: StudentProfile,
        course_offering_id: int = None,
    ):
        """
        Returns chronological attendance history for a student.
        """
        records_qs = AttendanceRecord.objects.filter(
            student=student_profile,
        ).select_related("session", "session__course_offering").order_by(
            "-session__session_date", "-session__created_at"
        )

        if course_offering_id:
            records_qs = records_qs.filter(session__course_offering_id=course_offering_id)

        return records_qs

