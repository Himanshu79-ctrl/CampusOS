"""
Service layer for Grades & Academic Results in CampusOS LMS.
Encapsulates business rules for GradeItems, GradeRecords, Assignment mark synchronization,
Exam Engine result ingestion, grade publication, and course-wise gradebook viewing (SRS Section 3.F).
"""

from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.academics.models import CourseOffering, Enrollment, EnrollmentStatus
from apps.assignments.models import Assignment, AssignmentSubmission, SubmissionStatus
from apps.students.models import StudentProfile
from .exam_client import ExamEngineClient
from .models import FinalCourseGrade, GradeItem, GradeItemType, GradeRecord


class GradeService:
    """
    Business logic coordinator for Course Gradebooks, Grade Records,
    Assignment integration, and Results publication.
    """

    @classmethod
    def check_faculty_or_admin_permission(cls, user, course_offering: CourseOffering) -> None:
        """
        Validates that the user is an academic admin or the assigned course faculty.
        """
        if getattr(user, "is_admin", False):
            return

        if getattr(user, "is_faculty", False):
            if str(course_offering.faculty_id) == str(user.user_id):
                return
            raise PermissionDenied("You are not the assigned instructor for this course offering.")

        raise PermissionDenied("Only faculty instructors or administrators can manage grades.")

    @classmethod
    def create_grade_item(
        cls,
        user,
        course_offering: CourseOffering,
        name: str,
        item_type: str = GradeItemType.ASSIGNMENT,
        max_marks: Decimal = Decimal("100.00"),
        weightage_percentage: Decimal = None,
        assignment: Assignment = None,
        external_exam_id: str = "",
        is_published: bool = False,
    ) -> GradeItem:
        """
        Creates a new assessment component for a course offering.
        """
        cls.check_faculty_or_admin_permission(user, course_offering)

        if max_marks <= Decimal("0.00"):
            raise ValidationError({"max_marks": "Maximum marks must be strictly greater than zero."})

        with transaction.atomic():
            item = GradeItem(
                course_offering=course_offering,
                name=name.strip(),
                item_type=item_type,
                max_marks=max_marks,
                weightage_percentage=weightage_percentage,
                assignment=assignment,
                external_exam_id=external_exam_id.strip() if external_exam_id else "",
                is_published=is_published,
            )
            item.save()
            return item

    @classmethod
    def update_grade_item(cls, user, grade_item: GradeItem, **attrs) -> GradeItem:
        """
        Updates an assessment component.
        """
        cls.check_faculty_or_admin_permission(user, grade_item.course_offering)

        with transaction.atomic():
            for key, val in attrs.items():
                if hasattr(grade_item, key):
                    setattr(grade_item, key, val)
            grade_item.save()
            return grade_item

    @classmethod
    def delete_grade_item(cls, user, grade_item: GradeItem) -> None:
        """
        Deletes a grade item and associated grade records.
        """
        cls.check_faculty_or_admin_permission(user, grade_item.course_offering)
        grade_item.delete()

    @classmethod
    def enter_or_update_grade_record(
        cls,
        user,
        grade_item: GradeItem,
        student_profile: StudentProfile,
        marks_obtained: Decimal = None,
        letter_grade: str = "",
        feedback: str = "",
        is_published: bool = None,
    ) -> GradeRecord:
        """
        Records or updates an individual student's grade record for a GradeItem.
        Enforces enrollment check and maximum marks boundaries.
        """
        cls.check_faculty_or_admin_permission(user, grade_item.course_offering)

        is_enrolled = Enrollment.objects.filter(
            student=student_profile,
            course_offering=grade_item.course_offering,
            status=EnrollmentStatus.ENROLLED,
        ).exists()
        if not is_enrolled:
            raise ValidationError(
                f"Student '{student_profile.registration_number}' is not actively enrolled in Course Offering #{grade_item.course_offering_id}."
            )

        if marks_obtained is not None:
            marks_dec = Decimal(str(marks_obtained))
            if marks_dec < Decimal("0.00"):
                raise ValidationError({"marks_obtained": "Marks cannot be negative."})
            if marks_dec > grade_item.max_marks:
                raise ValidationError(
                    {"marks_obtained": f"Marks cannot exceed maximum marks ({grade_item.max_marks})."}
                )
        else:
            marks_dec = None

        with transaction.atomic():
            record, _ = GradeRecord.objects.get_or_create(
                grade_item=grade_item,
                student=student_profile,
                defaults={
                    "marks_obtained": marks_dec,
                    "letter_grade": letter_grade.strip(),
                    "feedback": feedback.strip(),
                    "is_published": is_published if is_published is not None else grade_item.is_published,
                    "graded_by_faculty_id": str(user.user_id),
                    "graded_at": timezone.now(),
                },
            )

            if record.marks_obtained != marks_dec or record.letter_grade != letter_grade or record.feedback != feedback:
                record.marks_obtained = marks_dec
                record.letter_grade = letter_grade.strip()
                record.feedback = feedback.strip()
                if is_published is not None:
                    record.is_published = is_published
                record.graded_by_faculty_id = str(user.user_id)
                record.graded_at = timezone.now()
                record.save()

            return record

    @classmethod
    def bulk_enter_grades(cls, user, grade_item: GradeItem, records_data: list) -> list[GradeRecord]:
        """
        Bulk enters or updates grade records for a grade item.
        """
        cls.check_faculty_or_admin_permission(user, grade_item.course_offering)

        enrolled_students_map = {
            e.student_id: e.student
            for e in Enrollment.objects.filter(
                course_offering=grade_item.course_offering,
                status=EnrollmentStatus.ENROLLED,
            ).select_related("student")
        }

        results = []
        with transaction.atomic():
            for item in records_data:
                student_id = item.get("student_id")
                student = enrolled_students_map.get(student_id)
                if not student:
                    raise ValidationError(f"Student ID {student_id} is not actively enrolled in this course offering.")

                marks_raw = item.get("marks_obtained")
                marks_dec = Decimal(str(marks_raw)) if marks_raw is not None else None
                if marks_dec is not None:
                    if marks_dec < Decimal("0.00"):
                        raise ValidationError(f"Negative marks not allowed for student {student.registration_number}.")
                    if marks_dec > grade_item.max_marks:
                        raise ValidationError(
                            f"Marks for student {student.registration_number} exceed maximum marks ({grade_item.max_marks})."
                        )

                letter_grade = item.get("letter_grade", "")
                feedback = item.get("feedback", "")
                is_pub_raw = item.get("is_published")
                is_published = grade_item.is_published if is_pub_raw is None else bool(is_pub_raw)

                record, _ = GradeRecord.objects.get_or_create(
                    grade_item=grade_item,
                    student=student,
                    defaults={
                        "marks_obtained": marks_dec,
                        "letter_grade": letter_grade,
                        "feedback": feedback,
                        "is_published": is_published,
                        "graded_by_faculty_id": str(user.user_id),
                        "graded_at": timezone.now(),
                    },
                )
                record.marks_obtained = marks_dec
                record.letter_grade = letter_grade
                record.feedback = feedback
                record.is_published = is_published
                record.graded_by_faculty_id = str(user.user_id)
                record.graded_at = timezone.now()
                record.save()
                results.append(record)

        return results

    @classmethod
    def publish_grade_item(cls, user, grade_item: GradeItem, is_published: bool = True) -> GradeItem:
        """
        Publishes or unpublishes a grade item and cascades publication to child grade records.
        """
        cls.check_faculty_or_admin_permission(user, grade_item.course_offering)

        with transaction.atomic():
            grade_item.is_published = is_published
            grade_item.save(update_fields=["is_published", "updated_at"])
            grade_item.grade_records.update(is_published=is_published, updated_at=timezone.now())
            if is_published:
                try:
                    from apps.notifications.services import trigger_grade_published
                    for record in grade_item.grade_records.select_related("student", "grade_item"):
                        trigger_grade_published(record)
                except Exception:
                    pass
            return grade_item

    @classmethod
    def sync_assignment_grades(cls, user, grade_item: GradeItem) -> int:
        """
        Synchronizes graded assignment submissions into the gradebook for a linked GradeItem.
        """
        cls.check_faculty_or_admin_permission(user, grade_item.course_offering)

        if not grade_item.assignment:
            raise ValidationError("Grade item is not linked to an LMS Assignment.")

        submissions = AssignmentSubmission.objects.filter(
            assignment=grade_item.assignment,
            status=SubmissionStatus.GRADED,
        ).select_related("student")

        synced_count = 0
        with transaction.atomic():
            for sub in submissions:
                record, _ = GradeRecord.objects.get_or_create(
                    grade_item=grade_item,
                    student=sub.student,
                    defaults={
                        "marks_obtained": sub.marks_obtained,
                        "feedback": sub.feedback,
                        "is_published": grade_item.is_published,
                        "graded_by_faculty_id": sub.graded_by_faculty_id or str(user.user_id),
                        "graded_at": sub.graded_at or timezone.now(),
                    },
                )
                record.marks_obtained = sub.marks_obtained
                record.feedback = sub.feedback
                record.graded_by_faculty_id = sub.graded_by_faculty_id or str(user.user_id)
                record.graded_at = sub.graded_at or timezone.now()
                record.save()
                synced_count += 1

        return synced_count

    @classmethod
    def sync_exam_grades(cls, user, grade_item: GradeItem) -> dict:
        """
        Fetches external exam scores via the ExamEngineClient boundary and synchronizes them.
        """
        cls.check_faculty_or_admin_permission(user, grade_item.course_offering)

        if not grade_item.external_exam_id:
            raise ValidationError("Grade item is not linked to an external exam ID.")

        client_response = ExamEngineClient.fetch_exam_results(
            external_exam_id=grade_item.external_exam_id,
            course_offering_id=grade_item.course_offering_id,
        )

        if client_response.get("status") == "SUCCESS":
            results = client_response.get("results", [])
            synced_count = 0
            with transaction.atomic():
                for res in results:
                    student_auth_id = res.get("student_auth_id") or res.get("user_id")
                    marks = res.get("score") or res.get("marks_obtained")
                    if student_auth_id and marks is not None:
                        student = StudentProfile.objects.filter(auth_user_id=str(student_auth_id)).first()
                        if student and Enrollment.objects.filter(
                            student=student, course_offering=grade_item.course_offering, status=EnrollmentStatus.ENROLLED
                        ).exists():
                            record, _ = GradeRecord.objects.get_or_create(
                                grade_item=grade_item,
                                student=student,
                                defaults={
                                    "marks_obtained": Decimal(str(marks)),
                                    "is_published": grade_item.is_published,
                                    "graded_by_faculty_id": str(user.user_id),
                                    "graded_at": timezone.now(),
                                },
                            )
                            record.marks_obtained = Decimal(str(marks))
                            record.save()
                            synced_count += 1
            client_response["synced_records_count"] = synced_count

        return client_response

    @classmethod
    def get_course_gradebook(cls, user, course_offering: CourseOffering) -> dict:
        """
        Generates the comprehensive course-wise gradebook matrix for faculty and administrators.
        """
        cls.check_faculty_or_admin_permission(user, course_offering)

        grade_items = list(course_offering.grade_items.all().order_by("created_at"))
        item_ids = [item.id for item in grade_items]

        enrollments = Enrollment.objects.filter(
            course_offering=course_offering,
            status=EnrollmentStatus.ENROLLED,
        ).select_related("student").order_by("student__registration_number")

        records = GradeRecord.objects.filter(grade_item_id__in=item_ids).select_related("student", "grade_item")
        records_lookup = {}
        for r in records:
            records_lookup[(r.student_id, r.grade_item_id)] = r

        final_grades_map = {
            fg.student_id: fg
            for fg in FinalCourseGrade.objects.filter(course_offering=course_offering)
        }

        students_matrix = []
        for enrollment in enrollments:
            student = enrollment.student
            student_grades = []
            total_obtained = Decimal("0.00")
            total_max = Decimal("0.00")

            for item in grade_items:
                rec = records_lookup.get((student.id, item.id))
                marks = rec.marks_obtained if rec else None
                if marks is not None:
                    total_obtained += marks
                    total_max += item.max_marks

                student_grades.append({
                    "grade_item_id": item.id,
                    "grade_item_name": item.name,
                    "max_marks": str(item.max_marks),
                    "marks_obtained": str(marks) if marks is not None else None,
                    "letter_grade": rec.letter_grade if rec else "",
                    "feedback": rec.feedback if rec else "",
                    "is_published": rec.is_published if rec else False,
                })

            fg = final_grades_map.get(student.id)
            students_matrix.append({
                "student_id": student.id,
                "auth_user_id": student.auth_user_id,
                "registration_number": student.registration_number,
                "grades": student_grades,
                "total_marks_obtained": str(total_obtained),
                "total_max_marks": str(total_max),
                "final_grade": {
                    "final_letter_grade": fg.final_letter_grade if fg else "",
                    "percentage": str(fg.percentage) if fg and fg.percentage else None,
                    "feedback": fg.feedback if fg else "",
                    "is_published": fg.is_published if fg else False,
                } if fg else None,
            })

        return {
            "course_offering_id": course_offering.id,
            "course_id": course_offering.course_id,
            "section": course_offering.section,
            "grade_items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "item_type": item.item_type,
                    "max_marks": str(item.max_marks),
                    "weightage_percentage": str(item.weightage_percentage) if item.weightage_percentage else None,
                    "is_published": item.is_published,
                }
                for item in grade_items
            ],
            "students": students_matrix,
        }

    @classmethod
    def publish_final_course_grades(
        cls,
        user,
        course_offering: CourseOffering,
        final_grades_data: list = None,
    ) -> list[FinalCourseGrade]:
        """
        Publishes final course results for enrolled students in a CourseOffering.
        """
        cls.check_faculty_or_admin_permission(user, course_offering)

        enrolled_students = {
            e.student_id: e.student
            for e in Enrollment.objects.filter(
                course_offering=course_offering,
                status=EnrollmentStatus.ENROLLED,
            ).select_related("student")
        }

        now = timezone.now()
        results = []
        with transaction.atomic():
            if final_grades_data:
                for entry in final_grades_data:
                    student_id = entry.get("student_id")
                    student = enrolled_students.get(student_id)
                    if not student:
                        raise ValidationError(f"Student ID {student_id} is not actively enrolled in this offering.")

                    final_record, _ = FinalCourseGrade.objects.get_or_create(
                        course_offering=course_offering,
                        student=student,
                        defaults={
                            "total_marks_obtained": entry.get("total_marks_obtained"),
                            "total_max_marks": entry.get("total_max_marks"),
                            "percentage": entry.get("percentage"),
                            "final_letter_grade": entry.get("final_letter_grade", ""),
                            "feedback": entry.get("feedback", ""),
                            "is_published": True,
                            "published_at": now,
                            "graded_by_faculty_id": str(user.user_id),
                        },
                    )
                    final_record.final_letter_grade = entry.get("final_letter_grade", final_record.final_letter_grade)
                    final_record.feedback = entry.get("feedback", final_record.feedback)
                    final_record.is_published = True
                    final_record.published_at = now
                    final_record.graded_by_faculty_id = str(user.user_id)
                    final_record.save()
                    results.append(final_record)
            else:
                # Mark all existing final grades published
                for fg in FinalCourseGrade.objects.filter(course_offering=course_offering):
                    fg.is_published = True
                    fg.published_at = now
                    fg.save()
                    results.append(fg)

        return results

    @classmethod
    def get_student_grades(cls, student_profile: StudentProfile, course_offering_id: int = None) -> dict:
        """
        Retrieves all published grades and final course results for an enrolled student (IDOR safe).
        """
        # Only published records
        records_qs = GradeRecord.objects.filter(
            student=student_profile,
        ).filter(
            Q(is_published=True) | Q(grade_item__is_published=True)
        ).select_related("grade_item", "grade_item__course_offering").order_by("grade_item__course_offering", "grade_item__created_at")

        final_grades_qs = FinalCourseGrade.objects.filter(
            student=student_profile,
            is_published=True,
        ).select_related("course_offering")

        if course_offering_id:
            records_qs = records_qs.filter(grade_item__course_offering_id=course_offering_id)
            final_grades_qs = final_grades_qs.filter(course_offering_id=course_offering_id)

        return {
            "grade_records": records_qs,
            "final_grades": final_grades_qs,
        }

