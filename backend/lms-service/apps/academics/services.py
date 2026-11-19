"""
Business service layer for Course Offering enrollments in CampusOS LMS.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import (
    AcademicTerm,
    CourseOffering,
    Enrollment,
    EnrollmentStatus,
    OfferingStatus,
    TermStatus,
)
from apps.students.models import StudentProfile


class EnrollmentService:
    """
    Handles atomic student course enrollment operations and lifecycle rules.
    """

    @classmethod
    @transaction.atomic
    def enroll_student(
        cls, student: StudentProfile, course_offering: CourseOffering
    ) -> Enrollment:
        """
        Enrolls an active student in a published course offering if capacity permits
        and enrollment is open for the term.
        Uses select_for_update() to prevent race conditions on capacity.
        """
        # 1. Validate student eligibility
        if not student.is_active:
            raise ValidationError("Inactive students cannot enroll in courses.")

        # 2. Lock the course offering to prevent concurrent overselling of seats
        locked_offering = (
            CourseOffering.objects.select_for_update()
            .select_related("academic_term")
            .get(pk=course_offering.pk)
        )

        # 3. Validate course offering status
        if locked_offering.status != OfferingStatus.PUBLISHED:
            raise ValidationError(
                f"Cannot enroll in course offering with status '{locked_offering.status}'. Offering must be PUBLISHED."
            )

        # 4. Validate academic term enrollment window
        term = locked_offering.academic_term
        if not term.is_enrollment_open:
            raise ValidationError(
                f"Course enrollment is currently closed for academic term '{term.name}'."
            )

        # 5. Check for existing active enrollment
        active_enrollment = Enrollment.objects.filter(
            student=student,
            course_offering=locked_offering,
            status=EnrollmentStatus.ENROLLED,
        ).first()

        if active_enrollment:
            raise ValidationError(
                f"Student {student.registration_number} is already actively enrolled in this course offering."
            )

        # 6. Check seat capacity
        current_active_count = Enrollment.objects.filter(
            course_offering=locked_offering,
            status=EnrollmentStatus.ENROLLED,
        ).count()

        if current_active_count >= locked_offering.capacity:
            raise ValidationError(
                f"Course offering has reached maximum capacity ({locked_offering.capacity} seats)."
            )

        # 7. Check if student previously dropped this offering and is now re-enrolling
        dropped_enrollment = Enrollment.objects.filter(
            student=student,
            course_offering=locked_offering,
            status=EnrollmentStatus.DROPPED,
        ).first()

        if dropped_enrollment:
            # Reactivate previously dropped enrollment
            dropped_enrollment.status = EnrollmentStatus.ENROLLED
            dropped_enrollment.dropped_at = None
            dropped_enrollment.save(update_fields=["status", "dropped_at", "updated_at"])
            return dropped_enrollment

        # 8. Create new enrollment record
        enrollment = Enrollment.objects.create(
            student=student,
            course_offering=locked_offering,
            status=EnrollmentStatus.ENROLLED,
        )
        return enrollment

    @classmethod
    @transaction.atomic
    def drop_student(
        cls, student: StudentProfile, course_offering: CourseOffering
    ) -> Enrollment:
        """
        Drops an active enrollment for a student in a course offering.
        """
        enrollment = Enrollment.objects.filter(
            student=student,
            course_offering=course_offering,
            status=EnrollmentStatus.ENROLLED,
        ).first()

        if not enrollment:
            raise ValidationError(
                f"No active enrollment found for student {student.registration_number} in this offering."
            )

        enrollment.status = EnrollmentStatus.DROPPED
        enrollment.dropped_at = timezone.now()
        enrollment.save(update_fields=["status", "dropped_at", "updated_at"])
        return enrollment


class AcademicTermService:
    """
    Manages AcademicTerm lifecycle transitions and enrollment window rules.
    """

    @classmethod
    @transaction.atomic
    def activate_term(cls, term: AcademicTerm) -> AcademicTerm:
        """
        Activates a term, marking any previously active term as COMPLETED.
        """
        AcademicTerm.objects.filter(status=TermStatus.ACTIVE).exclude(pk=term.pk).update(
            status=TermStatus.COMPLETED,
            is_enrollment_open=False,
            updated_at=timezone.now(),
        )
        term.status = TermStatus.ACTIVE
        term.save()
        return term

    @classmethod
    @transaction.atomic
    def complete_term(cls, term: AcademicTerm) -> AcademicTerm:
        """
        Completes an academic term and ensures enrollment is closed.
        """
        term.status = TermStatus.COMPLETED
        term.is_enrollment_open = False
        term.save()
        return term

    @classmethod
    def set_enrollment_window(cls, term: AcademicTerm, is_open: bool) -> AcademicTerm:
        """
        Opens or closes enrollment for a term, verifying COMPLETED/ARCHIVED terms cannot open enrollment.
        """
        if is_open and term.status in (TermStatus.COMPLETED, TermStatus.ARCHIVED):
            raise ValidationError(
                f"Cannot open enrollment for an academic term with status '{term.status}'."
            )
        term.is_enrollment_open = is_open
        term.save()
        return term


