from django.contrib import admin
from .models import GradeItem, GradeRecord, FinalCourseGrade


class GradeRecordInline(admin.TabularInline):
    model = GradeRecord
    extra = 0
    fields = ("student", "marks_obtained", "letter_grade", "is_published", "feedback", "graded_by_faculty_id")


@admin.register(GradeItem)
class GradeItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "course_offering", "item_type", "max_marks", "is_published", "created_at")
    list_filter = ("item_type", "is_published", "course_offering")
    search_fields = ("name", "course_offering__course_id")
    inlines = [GradeRecordInline]


@admin.register(GradeRecord)
class GradeRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "grade_item", "student", "marks_obtained", "letter_grade", "is_published", "graded_by_faculty_id")
    list_filter = ("is_published", "grade_item__course_offering", "grade_item__item_type")
    search_fields = ("student__registration_number", "grade_item__name", "letter_grade")


@admin.register(FinalCourseGrade)
class FinalCourseGradeAdmin(admin.ModelAdmin):
    list_display = ("id", "course_offering", "student", "total_marks_obtained", "total_max_marks", "percentage", "final_letter_grade", "is_published")
    list_filter = ("is_published", "course_offering")
    search_fields = ("student__registration_number", "final_letter_grade")

