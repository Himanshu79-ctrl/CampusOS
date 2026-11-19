"""
Tests for AcademicTerm, CourseOffering, Enrollment models, and EnrollmentService in apps.academics.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connections, transaction
from django.test import TestCase, TransactionTestCase

from .models import (
    AcademicTerm,
    CourseOffering,
    Enrollment,
    EnrollmentStatus,
    OfferingStatus,
    TermStatus,
)
from .services import AcademicTermService, EnrollmentService
from apps.students.models import StudentProfile


class AcademicTermModelTests(TestCase):
    """
    Tests for AcademicTerm model constraints and lifecycle rules.
    """

    def setUp(self):
        self.term_data = {
            "name": "Fall 2026",
            "academic_year": "2026-2027",
            "term_number": 1,
            "start_date": date(2026, 8, 1),
            "end_date": date(2026, 12, 15),
            "status": TermStatus.UPCOMING,
            "is_enrollment_open": True,
        }

    def test_create_academic_term(self):
        """Test valid academic term creation."""
        term = AcademicTerm.objects.create(**self.term_data)
        self.assertEqual(term.name, "Fall 2026")
        self.assertIn("Fall 2026", str(term))

    def test_academic_year_format_and_consecutive_validation(self):
        """Test academic_year format and consecutive year validation rules."""
        # Invalid format (not YYYY-YYYY)
        invalid_format_data = self.term_data.copy()
        invalid_format_data["academic_year"] = "2026"
        with self.assertRaises(ValidationError) as ctx:
            AcademicTerm(**invalid_format_data).full_clean()
        self.assertIn("academic_year", ctx.exception.message_dict)

        # Non-consecutive years (e.g., 2026-2028)
        non_consecutive_data = self.term_data.copy()
        non_consecutive_data["academic_year"] = "2026-2028"
        with self.assertRaises(ValidationError) as ctx:
            AcademicTerm(**non_consecutive_data).full_clean()
        self.assertIn("consecutive", str(ctx.exception))

        # Valid consecutive format succeeds
        valid_term = AcademicTerm(**self.term_data)
        valid_term.full_clean()  # should not raise

    def test_end_date_must_be_after_start_date(self):
        """Test that end_date <= start_date violates validation and check constraint."""
        invalid_data = self.term_data.copy()
        invalid_data["end_date"] = invalid_data["start_date"] - timedelta(days=1)
        term = AcademicTerm(**invalid_data)

        with self.assertRaises(ValidationError):
            term.full_clean()

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                term.save()

    def test_unique_academic_term_per_year(self):
        """Test that academic_year and term_number combination must be unique."""
        AcademicTerm.objects.create(**self.term_data)
        duplicate_data = self.term_data.copy()
        duplicate_data["name"] = "Duplicate Fall"

        with self.assertRaises(IntegrityError):
            AcademicTerm.objects.create(**duplicate_data)

    def test_only_one_active_term_institution_wide(self):
        """
        Enforce that strictly only ONE AcademicTerm may have ACTIVE status at any time.
        Verified via model clean() and PostgreSQL conditional unique constraint.
        """
        first_term_data = self.term_data.copy()
        first_term_data["status"] = TermStatus.ACTIVE
        term1 = AcademicTerm.objects.create(**first_term_data)
        self.assertEqual(term1.status, TermStatus.ACTIVE)

        second_term_data = self.term_data.copy()
        second_term_data["name"] = "Spring 2027"
        second_term_data["term_number"] = 2
        second_term_data["start_date"] = date(2027, 1, 10)
        second_term_data["end_date"] = date(2027, 5, 20)
        second_term_data["status"] = TermStatus.ACTIVE

        term2 = AcademicTerm(**second_term_data)

        # 1. Model-level clean() catches the duplicate active term
        with self.assertRaises(ValidationError):
            term2.full_clean()

        # 2. Database-level conditional unique constraint also blocks it
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                term2.save()

        # When the first term is marked COMPLETED, the second term can become ACTIVE
        term1.status = TermStatus.COMPLETED
        term1.is_enrollment_open = False
        term1.save()

        term2.save()
        self.assertEqual(term2.status, TermStatus.ACTIVE)

    def test_completed_term_cannot_have_open_enrollment(self):
        """Test model validation prevents open enrollment on a completed term."""
        term_data = self.term_data.copy()
        term_data["status"] = TermStatus.COMPLETED
        term_data["is_enrollment_open"] = True
        term = AcademicTerm(**term_data)

        with self.assertRaises(ValidationError) as ctx:
            term.full_clean()
        self.assertIn("is_enrollment_open", ctx.exception.message_dict)


class AcademicTermServiceTests(TestCase):
    """
    Tests for AcademicTermService lifecycle methods.
    """

    def setUp(self):
        self.term1 = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )
        self.term2 = AcademicTerm.objects.create(
            name="Spring 2027",
            academic_year="2026-2027",
            term_number=2,
            start_date=date(2027, 1, 10),
            end_date=date(2027, 5, 20),
            status=TermStatus.UPCOMING,
            is_enrollment_open=False,
        )

    def test_activate_term_deactivates_previous_active_term(self):
        """Activating term2 should automatically mark term1 as COMPLETED with enrollment closed."""
        AcademicTermService.activate_term(self.term2)

        self.term1.refresh_from_db()
        self.term2.refresh_from_db()

        self.assertEqual(self.term1.status, TermStatus.COMPLETED)
        self.assertFalse(self.term1.is_enrollment_open)
        self.assertEqual(self.term2.status, TermStatus.ACTIVE)

    def test_complete_term_closes_enrollment(self):
        """Completing a term automatically closes enrollment."""
        AcademicTermService.complete_term(self.term1)

        self.term1.refresh_from_db()
        self.assertEqual(self.term1.status, TermStatus.COMPLETED)
        self.assertFalse(self.term1.is_enrollment_open)

    def test_set_enrollment_window_rejects_completed_term(self):
        """Opening enrollment for a completed term raises ValidationError."""
        AcademicTermService.complete_term(self.term1)

        with self.assertRaises(ValidationError):
            AcademicTermService.set_enrollment_window(self.term1, is_open=True)


class CourseOfferingModelTests(TestCase):
    """
    Tests for CourseOffering constraints and properties.
    """

    def setUp(self):
        self.term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )
        self.offering_data = {
            "course_id": "65a8e01b2c3d4e5f6a7b8c01",
            "faculty_id": "65a8e01b2c3d4e5f6a7b8f01",
            "department_id": "65a8e01b2c3d4e5f6a7b8d01",
            "academic_term": self.term,
            "section": "A",
            "capacity": 40,
            "status": OfferingStatus.PUBLISHED,
        }

    def test_create_course_offering(self):
        """Test valid course offering creation."""
        offering = CourseOffering.objects.create(**self.offering_data)
        self.assertEqual(offering.capacity, 40)
        self.assertIn("Sec A", str(offering))

    def test_capacity_must_be_positive(self):
        """Test check constraint that capacity must be > 0."""
        invalid_data = self.offering_data.copy()
        invalid_data["capacity"] = 0
        offering = CourseOffering(**invalid_data)

        with self.assertRaises(ValidationError):
            offering.full_clean()

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                offering.save()

    def test_unique_offering_per_course_term_section(self):
        """Test that duplicate section for the same course and term is rejected."""
        CourseOffering.objects.create(**self.offering_data)

        with self.assertRaises(IntegrityError):
            CourseOffering.objects.create(**self.offering_data)


class EnrollmentAndServiceTests(TestCase):
    """
    Tests for Enrollment constraints and EnrollmentService atomic business logic.
    """

    def setUp(self):
        self.student = StudentProfile.objects.create(
            auth_user_id="usr_auth_010",
            registration_number="2026-CSE-010",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            admission_year=2026,
            current_semester=1,
            is_active=True,
        )
        self.term = AcademicTerm.objects.create(
            name="Fall 2026",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )
        self.offering = CourseOffering.objects.create(
            course_id="65a8e01b2c3d4e5f6a7b8c01",
            faculty_id="65a8e01b2c3d4e5f6a7b8f01",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            academic_term=self.term,
            section="A",
            capacity=2,
            status=OfferingStatus.PUBLISHED,
        )

    def test_successful_enrollment(self):
        """Test standard student enrollment via EnrollmentService."""
        enrollment = EnrollmentService.enroll_student(self.student, self.offering)
        self.assertEqual(enrollment.status, EnrollmentStatus.ENROLLED)
        self.assertEqual(self.offering.enrollments.filter(status=EnrollmentStatus.ENROLLED).count(), 1)

    def test_duplicate_active_enrollment_rejected_by_database_constraint(self):
        """
        Verify PostgreSQL conditional unique constraint prevents duplicate active enrollment.
        """
        Enrollment.objects.create(
            student=self.student,
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Enrollment.objects.create(
                    student=self.student,
                    course_offering=self.offering,
                    status=EnrollmentStatus.ENROLLED,
                )

    def test_duplicate_active_enrollment_rejected_by_service(self):
        """Test service rejects duplicate enrollment with clear ValidationError."""
        EnrollmentService.enroll_student(self.student, self.offering)

        with self.assertRaises(ValidationError) as ctx:
            EnrollmentService.enroll_student(self.student, self.offering)
        self.assertIn("already actively enrolled", str(ctx.exception))

    def test_offering_capacity_enforced(self):
        """Test that enrollment is rejected when offering capacity is reached."""
        student2 = StudentProfile.objects.create(
            auth_user_id="usr_auth_011",
            registration_number="2026-CSE-011",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            admission_year=2026,
            current_semester=1,
            is_active=True,
        )
        student3 = StudentProfile.objects.create(
            auth_user_id="usr_auth_012",
            registration_number="2026-CSE-012",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            admission_year=2026,
            current_semester=1,
            is_active=True,
        )

        # Capacity is 2
        EnrollmentService.enroll_student(self.student, self.offering)
        EnrollmentService.enroll_student(student2, self.offering)

        # Third enrollment must fail
        with self.assertRaises(ValidationError) as ctx:
            EnrollmentService.enroll_student(student3, self.offering)
        self.assertIn("maximum capacity", str(ctx.exception))

    def test_inactive_student_cannot_enroll(self):
        """Test that inactive students cannot enroll."""
        self.student.is_active = False
        self.student.save()

        with self.assertRaises(ValidationError) as ctx:
            EnrollmentService.enroll_student(self.student, self.offering)
        self.assertIn("Inactive students", str(ctx.exception))

    def test_cannot_enroll_when_term_enrollment_closed(self):
        """Test enrollment rejected when term enrollment is closed."""
        self.term.is_enrollment_open = False
        self.term.save()

        with self.assertRaises(ValidationError) as ctx:
            EnrollmentService.enroll_student(self.student, self.offering)
        self.assertIn("closed for academic term", str(ctx.exception))

    def test_cannot_enroll_in_draft_offering(self):
        """Test enrollment rejected if offering is not PUBLISHED."""
        self.offering.status = OfferingStatus.DRAFT
        self.offering.save()

        with self.assertRaises(ValidationError) as ctx:
            EnrollmentService.enroll_student(self.student, self.offering)
        self.assertIn("Offering must be PUBLISHED", str(ctx.exception))

    def test_drop_and_reenroll_lifecycle(self):
        """
        Test that a student can enroll, drop the course, and subsequently re-enroll.
        Verified both at database constraint and service level.
        """
        # 1. Initial enrollment
        enrollment = EnrollmentService.enroll_student(self.student, self.offering)
        self.assertEqual(enrollment.status, EnrollmentStatus.ENROLLED)

        # 2. Drop the course
        dropped = EnrollmentService.drop_student(self.student, self.offering)
        self.assertEqual(dropped.status, EnrollmentStatus.DROPPED)
        self.assertIsNotNone(dropped.dropped_at)
        self.assertEqual(self.offering.enrollments.filter(status=EnrollmentStatus.ENROLLED).count(), 0)

        # 3. Re-enroll in the same course offering
        reenrolled = EnrollmentService.enroll_student(self.student, self.offering)
        self.assertEqual(reenrolled.status, EnrollmentStatus.ENROLLED)
        self.assertIsNone(reenrolled.dropped_at)
        self.assertEqual(self.offering.enrollments.filter(status=EnrollmentStatus.ENROLLED).count(), 1)


class EnrollmentConcurrencyTests(TransactionTestCase):
    """
    Genuine multi-threaded concurrency test verifying select_for_update() row locking
    and capacity protection under concurrent enrollment requests.
    """

    def setUp(self):
        self.term = AcademicTerm.objects.create(
            name="Fall 2026 Concurrency",
            academic_year="2026-2027",
            term_number=1,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
            status=TermStatus.ACTIVE,
            is_enrollment_open=True,
        )
        # Capacity is strictly 1 seat
        self.offering = CourseOffering.objects.create(
            course_id="65a8e01b2c3d4e5f6a7b8c01",
            faculty_id="65a8e01b2c3d4e5f6a7b8f01",
            department_id="65a8e01b2c3d4e5f6a7b8d01",
            academic_term=self.term,
            section="A",
            capacity=1,
            status=OfferingStatus.PUBLISHED,
        )
        self.students = [
            StudentProfile.objects.create(
                auth_user_id=f"concurrent_usr_{i}",
                registration_number=f"2026-CONC-{i:03d}",
                department_id="65a8e01b2c3d4e5f6a7b8d01",
                admission_year=2026,
                current_semester=1,
                is_active=True,
            )
            for i in range(1, 5)
        ]

    def tearDown(self):
        connections.close_all()

    def test_concurrent_enrollments_strictly_enforce_capacity(self):
        """
        Launch 4 simultaneous threads attempting to enroll in a 1-capacity offering.
        select_for_update() must guarantee that exactly 1 succeeds and 3 fail.
        """
        successes = []
        failures = []

        def worker(student):
            try:
                enrollment = EnrollmentService.enroll_student(student, self.offering)
                successes.append(enrollment.id)
            except ValidationError as exc:
                failures.append(str(exc))
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, s) for s in self.students]
            for f in futures:
                f.result()

        # Exactly 1 thread must have succeeded
        self.assertEqual(len(successes), 1)
        # Exactly 3 threads must have been rejected due to capacity limit
        self.assertEqual(len(failures), 3)
        for err in failures:
            self.assertIn("maximum capacity", err)

        # Database verification
        active_count = Enrollment.objects.filter(
            course_offering=self.offering,
            status=EnrollmentStatus.ENROLLED,
        ).count()
        self.assertEqual(active_count, 1)
