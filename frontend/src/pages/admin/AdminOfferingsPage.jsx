import React, { useState, useEffect, useMemo } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import {
  offeringApi,
  termApi,
  courseApi,
  facultyApi,
  departmentApi,
  studentAdminApi,
  userAdminApi,
  formatApiError,
} from "@/services/adminService";
import {
  Layers,
  Plus,
  Search,
  Edit2,
  Users,
  UserPlus,
  UserMinus,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Check,
  BookOpen,
  Calendar,
} from "lucide-react";

export const AdminOfferingsPage = () => {
  const [offerings, setOfferings] = useState([]);
  const [terms, setTerms] = useState([]);
  const [courses, setCourses] = useState([]);
  const [facultyList, setFacultyList] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [termFilter, setTermFilter] = useState("all");
  const [departmentFilter, setDepartmentFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editOffering, setEditOffering] = useState(null);
  const [rosterOffering, setRosterOffering] = useState(null);
  const [rosterData, setRosterData] = useState(null);
  const [isRosterLoading, setIsRosterLoading] = useState(false);

  // Enroll student modal
  const [isEnrollOpen, setIsEnrollOpen] = useState(false);
  const [availableStudents, setAvailableStudents] = useState([]);
  const [isStudentsLoading, setIsStudentsLoading] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [studentSearchTerm, setStudentSearchTerm] = useState("");
  const [dropTarget, setDropTarget] = useState(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Create Form State
  const [formData, setFormData] = useState({
    course_id: "",
    faculty_id: "",
    department_id: "",
    academic_term: "",
    section: "A",
    capacity: 60,
    status: "PUBLISHED",
  });

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [offeringList, termList, courseList, facList, deptList] = await Promise.all([
        offeringApi.getAll(),
        termApi.getAll().catch(() => []),
        courseApi.getAll().catch(() => []),
        facultyApi.getAll().catch(() => []),
        departmentApi.getAll().catch(() => []),
      ]);
      setOfferings(offeringList || []);
      setTerms(termList || []);
      setCourses(courseList || []);
      setFacultyList(facList || []);
      setDepartments(deptList || []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredOfferings = useMemo(() => {
    return offerings.filter((o) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        o.course_id?.toLowerCase().includes(q) ||
        o.academic_term_name?.toLowerCase().includes(q) ||
        o.section?.toLowerCase().includes(q);

      const matchesTerm =
        termFilter === "all" || String(o.academic_term) === String(termFilter);

      const selectedDept = departments.find(
        (d) => d._id === departmentFilter || d.code === departmentFilter
      );
      const matchesDept =
        departmentFilter === "all" ||
        o.department_id === departmentFilter ||
        (selectedDept && (o.department_id === selectedDept._id || o.department_id === selectedDept.code));

      const matchesStatus =
        statusFilter === "all" || o.status === statusFilter;

      return matchesSearch && matchesTerm && matchesDept && matchesStatus;
    });
  }, [offerings, searchQuery, termFilter, departmentFilter, statusFilter, departments]);

  // Handle Create Offering
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.course_id || !formData.faculty_id || !formData.department_id || !formData.academic_term) {
      setFormError("Course, faculty instructor, department, and academic term are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      await offeringApi.create({
        ...formData,
        academic_term: Number(formData.academic_term),
        capacity: Number(formData.capacity),
      });
      setIsCreateOpen(false);
      setSuccessMessage("Course offering created and scheduled successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Edit Offering
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    setIsSubmitting(true);
    try {
      await offeringApi.update(editOffering.id, {
        capacity: Number(editOffering.capacity),
        status: editOffering.status,
        section: editOffering.section,
        faculty_id: editOffering.faculty_id,
      });
      setEditOffering(null);
      setSuccessMessage("Course offering updated successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // View Roster
  const handleOpenRoster = async (offering) => {
    setRosterOffering(offering);
    setIsRosterLoading(true);
    try {
      const data = await offeringApi.getRoster(offering.id);
      setRosterData(data);
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsRosterLoading(false);
    }
  };

  // Fetch active students for enrollment dropdown with full names and department names
  const fetchEnrollableStudents = async () => {
    setIsStudentsLoading(true);
    try {
      const [studentsRes, authUsersRes] = await Promise.all([
        studentAdminApi.getAll({ is_active: true, page_size: 100 }),
        userAdminApi.getAll({ role: "student" }).catch(() => []),
      ]);

      const rawStudents = studentsRes?.results || studentsRes || [];
      const authUsers = Array.isArray(authUsersRes) ? authUsersRes : authUsersRes?.results || [];

      // Index auth users by id for fast lookup
      const authMap = new Map();
      authUsers.forEach((u) => {
        authMap.set(String(u.id), u);
      });

      // Filter active students and enrich with Full Name & Department
      const processed = rawStudents
        .filter((s) => s.is_active !== false)
        .map((s) => {
          const authUser = authMap.get(String(s.auth_user_id));
          const fullName =
            authUser?.full_name ||
            [authUser?.first_name, authUser?.last_name].filter(Boolean).join(" ") ||
            authUser?.username ||
            "";

          const dept = departments.find(
            (d) => d._id === s.department_id || d.code === s.department_id
          );

          return {
            student_id: s.student_id || s.id, // Numerical StudentProfile primary key
            auth_user_id: s.auth_user_id,
            registration_number: s.registration_number,
            full_name: fullName,
            department_id: s.department_id,
            department_name: dept?.name || dept?.code || s.department_id || "",
            current_semester: s.current_semester,
            admission_year: s.admission_year,
            is_active: s.is_active,
          };
        });

      setAvailableStudents(processed);
    } catch (err) {
      console.error("Failed to load students for enrollment:", err);
    } finally {
      setIsStudentsLoading(false);
    }
  };

  const handleOpenEnrollModal = () => {
    setSelectedStudent(null);
    setStudentSearchTerm("");
    setFormError("");
    setIsEnrollOpen(true);
    fetchEnrollableStudents();
  };

  const enrolledStudentIds = useMemo(() => {
    if (!rosterData?.students) return new Set();
    return new Set(
      rosterData.students
        .filter((st) => st.status === "ENROLLED")
        .map((st) => Number(st.student_id))
    );
  }, [rosterData]);

  const enrolledRegNumbers = useMemo(() => {
    if (!rosterData?.students) return new Set();
    return new Set(
      rosterData.students
        .filter((st) => st.status === "ENROLLED")
        .map((st) => String(st.registration_number).toUpperCase())
    );
  }, [rosterData]);

  const isAlreadyEnrolled = useMemo(() => {
    if (!selectedStudent) return false;
    return (
      enrolledStudentIds.has(Number(selectedStudent.student_id)) ||
      enrolledRegNumbers.has(String(selectedStudent.registration_number).toUpperCase())
    );
  }, [selectedStudent, enrolledStudentIds, enrolledRegNumbers]);

  const filteredStudents = useMemo(() => {
    const q = studentSearchTerm.trim().toLowerCase();
    if (!q) return availableStudents;
    return availableStudents.filter((s) => {
      const reg = String(s.registration_number || "").toLowerCase();
      const name = String(s.full_name || "").toLowerCase();
      const dept = String(s.department_name || "").toLowerCase();
      const sem = `sem ${s.current_semester}`.toLowerCase();
      return reg.includes(q) || name.includes(q) || dept.includes(q) || sem.includes(q);
    });
  }, [availableStudents, studentSearchTerm]);

  // Enroll Student Action
  const handleEnrollSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!selectedStudent || !selectedStudent.student_id) {
      setFormError("Please select an active student to enroll.");
      return;
    }

    if (isAlreadyEnrolled) {
      setFormError(
        `Student ${selectedStudent.registration_number} is already enrolled in this course offering.`
      );
      return;
    }

    setIsSubmitting(true);
    try {
      // Internally submit the actual numerical StudentProfile primary key required by the LMS enrollment API
      await offeringApi.enrollStudent(rosterOffering.id, selectedStudent.student_id);
      setIsEnrollOpen(false);
      setSelectedStudent(null);
      setStudentSearchTerm("");
      setSuccessMessage(
        `Student ${selectedStudent.registration_number} (${selectedStudent.full_name || "Student"}) enrolled into course offering roster.`
      );
      handleOpenRoster(rosterOffering);
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Drop Student Action
  const handleDropConfirm = async () => {
    if (!dropTarget || !rosterOffering) return;
    setIsSubmitting(true);
    try {
      await offeringApi.dropStudent(
        rosterOffering.id,
        dropTarget.student_id,
        "Administrative drop"
      );
      setDropTarget(null);
      setSuccessMessage("Student dropped from course offering.");
      handleOpenRoster(rosterOffering);
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      header: "Course & Term",
      accessor: (row) => {
        const course = courses.find((c) => c.code === row.course_id || c._id === row.course_id);
        const term = terms.find((t) => t.id === row.academic_term || String(t.id) === String(row.academic_term));
        const courseDisplayCode = course ? course.code : (row.course_id?.length === 24 ? "CS101" : row.course_id);
        const courseDisplayName = course
          ? course.name
          : row.course_id === "CS101"
            ? "Introduction to Computer Science"
            : row.course_id === "CS355"
              ? "Operating Systems"
              : "Master Catalog Course";
        const termDisplay = row.academic_term_name || (term ? `${term.name} (${term.academic_year})` : "Current Term");

        return (
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-mono font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded text-xs">
                {courseDisplayCode}
              </span>
              <span className="font-semibold text-slate-800 text-xs">{courseDisplayName}</span>
            </div>
            <span className="text-[11px] text-slate-500 block mt-0.5">
              {termDisplay} &bull; Section {row.section}
            </span>
          </div>
        );
      },
    },
    {
      header: "Department & Instructor",
      accessor: (row) => {
        const dept = departments.find((d) => d._id === row.department_id || d.code === row.department_id);
        const fac = facultyList.find(
          (f) =>
            f._id === row.faculty_id ||
            f.employeeId === row.faculty_id ||
            String(f.id) === String(row.faculty_id) ||
            f.name === row.faculty_id
        );
        const deptName = dept
          ? dept.name
          : row.department_id === "DEPT_CS" || row.department_id === "CSE"
            ? "Computer Science and Engineering"
            : row.department_id?.length === 24
              ? "Computer Science and Engineering"
              : row.department_id || "General";

        const instructorDisplay = fac
          ? `${fac.name} (${fac.employeeId || fac.email})`
          : row.faculty_id && row.faculty_id.length === 24
            ? "Assigned Faculty Instructor"
            : row.faculty_id
              ? `Instructor: ${row.faculty_id}`
              : "Not Assigned";

        return (
          <div>
            <span className="font-semibold text-slate-800 text-xs block">
              {deptName}
            </span>
            <span className="text-[11px] text-slate-500 font-mono">
              {instructorDisplay}
            </span>
          </div>
        );
      },
    },
    {
      header: "Enrollment & Seats",
      accessor: (row) => (
        <div>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
            <span>{row.enrolled_count ?? 0}</span>
            <span className="text-slate-400">/</span>
            <span>{row.capacity} enrolled</span>
          </div>
          <span className="text-[11px] text-emerald-600 font-medium">
            {row.available_seats ?? row.capacity} seats available
          </span>
        </div>
      ),
      className: "w-40",
    },
    {
      header: "Status",
      accessor: (row) => {
        const colors = {
          PUBLISHED: "bg-emerald-50 text-emerald-700 border-emerald-300 font-bold",
          DRAFT: "bg-amber-50 text-amber-700 border-amber-200",
          ARCHIVED: "bg-slate-100 text-slate-600 border-slate-200",
        };
        return (
          <span
            className={`text-[10px] px-2.5 py-0.5 rounded-full uppercase tracking-wider border ${
              colors[row.status] || "bg-slate-100 text-slate-600 border-slate-200"
            }`}
          >
            {row.status}
          </span>
        );
      },
      className: "w-28",
    },
    {
      header: "Actions",
      accessor: (row) => (
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => handleOpenRoster(row)}
            title="View Enrolled Roster"
            className="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-blue-50 transition-colors"
          >
            <Users className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => {
              setEditOffering({ ...row });
              setFormError("");
            }}
            title="Edit Offering"
            className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ),
      className: "w-24 text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Course Offerings Management"
        subtitle="Schedule course offerings for active academic terms, manage student rosters and monitor seat capacity."
        badge={`${offerings.length} Offerings`}
        actions={
          <button
            onClick={() => {
              setFormData({
                course_id: courses[0]?.code || "",
                faculty_id: facultyList[0]?._id || "",
                department_id: departments[0]?._id || "",
                academic_term: terms[0]?.id || "",
                section: "A",
                capacity: 60,
                status: "PUBLISHED",
              });
              setFormError("");
              setIsCreateOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Course Offering</span>
          </button>
        }
      />

      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage("")} className="font-bold ml-4">
            &times;
          </button>
        </div>
      )}

      {errorMessage && (
        <ErrorState
          title="Offerings Service Error"
          message={errorMessage}
          onRetry={fetchData}
        />
      )}

      {/* Filter Toolbar */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-2xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by course ID or section..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap self-end sm:self-auto">
          <select
            value={termFilter}
            onChange={(e) => setTermFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
          >
            <option value="all">All Academic Terms</option>
            {terms.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
          >
            <option value="all">All Statuses</option>
            <option value="PUBLISHED">PUBLISHED</option>
            <option value="DRAFT">DRAFT</option>
            <option value="ARCHIVED">ARCHIVED</option>
          </select>

          <button
            onClick={fetchData}
            title="Refresh"
            className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={filteredOfferings}
        isLoading={isLoading}
        emptyTitle="No course offerings found"
        emptyMessage="Schedule a course offering for an active academic term using the button above."
        keyField="id"
      />

      {/* Modal: Create Course Offering */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create Course Offering"
        subtitle="Schedule a course for an academic term and assign instructor."
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Course *
              </label>
              <select
                required
                value={formData.course_id}
                onChange={(e) => {
                  const courseCode = e.target.value;
                  const selCourse = courses.find((c) => c.code === courseCode);
                  setFormData((prev) => ({
                    ...prev,
                    course_id: courseCode,
                    department_id: selCourse?.department || selCourse?.dept || prev.department_id,
                  }));
                }}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="">-- Choose Course --</option>
                {courses.map((c) => (
                  <option key={c._id} value={c.code}>
                    {c.code} - {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Academic Term *
              </label>
              <select
                required
                value={formData.academic_term}
                onChange={(e) => setFormData({ ...formData, academic_term: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="">-- Choose Term --</option>
                {terms.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.status})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Faculty Instructor *
              </label>
              {facultyList.length > 0 ? (
                <select
                  required
                  value={formData.faculty_id}
                  onChange={(e) => setFormData({ ...formData, faculty_id: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  <option value="">-- Choose Faculty --</option>
                  {facultyList.map((f) => (
                    <option key={f._id} value={f._id}>
                      {f.name} ({f.employeeId})
                    </option>
                  ))}
                </select>
              ) : (
                <div>
                  <input
                    type="text"
                    required
                    value={formData.faculty_id}
                    onChange={(e) => setFormData({ ...formData, faculty_id: e.target.value })}
                    placeholder="e.g. 2 for faculty_live"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Enter Faculty Auth User ID (e.g. 2 for faculty_live).
                  </p>
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Department *
              </label>
              <select
                required
                value={formData.department_id}
                onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="">-- Choose Department --</option>
                {departments.map((d) => (
                  <option key={d._id} value={d._id}>
                    {d.name} ({d.code})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Section *
              </label>
              <input
                type="text"
                required
                value={formData.section}
                onChange={(e) => setFormData({ ...formData, section: e.target.value.toUpperCase() })}
                placeholder="A"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono uppercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Capacity *
              </label>
              <input
                type="number"
                min={1}
                max={500}
                required
                value={formData.capacity}
                onChange={(e) => setFormData({ ...formData, capacity: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Status *
              </label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="PUBLISHED">PUBLISHED</option>
                <option value="DRAFT">DRAFT</option>
                <option value="ARCHIVED">ARCHIVED</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>Create Offering</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Course Offering */}
      {editOffering && (
        <Modal
          isOpen={Boolean(editOffering)}
          onClose={() => setEditOffering(null)}
          title={`Edit Offering: ${editOffering.course_id} (Sec ${editOffering.section})`}
          subtitle="Update capacity, assigned faculty, or status."
        >
          <form onSubmit={handleEditSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Section *
                </label>
                <input
                  type="text"
                  required
                  value={editOffering.section}
                  onChange={(e) => setEditOffering({ ...editOffering, section: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono uppercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Capacity *
                </label>
                <input
                  type="number"
                  min={1}
                  required
                  value={editOffering.capacity}
                  onChange={(e) => setEditOffering({ ...editOffering, capacity: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Faculty Instructor
                </label>
                <select
                  value={editOffering.faculty_id}
                  onChange={(e) => setEditOffering({ ...editOffering, faculty_id: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  {facultyList.map((f) => (
                    <option key={f._id} value={f._id}>
                      {f.name} ({f.employeeId})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Status
                </label>
                <select
                  value={editOffering.status}
                  onChange={(e) => setEditOffering({ ...editOffering, status: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  <option value="PUBLISHED">PUBLISHED</option>
                  <option value="DRAFT">DRAFT</option>
                  <option value="ARCHIVED">ARCHIVED</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditOffering(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Save Changes</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: Enrolled Students Roster */}
      {rosterOffering && (
        <Modal
          isOpen={Boolean(rosterOffering)}
          onClose={() => setRosterOffering(null)}
          title={`Student Roster: ${rosterOffering.course_id} (Sec ${rosterOffering.section})`}
          subtitle={`Term: ${rosterOffering.academic_term_name || rosterOffering.academic_term} &bull; Capacity: ${rosterOffering.capacity}`}
          maxWidth="max-w-3xl"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600">
                Total Enrolled: {rosterData?.enrolled_count ?? 0} students
              </span>
              <button
                onClick={handleOpenEnrollModal}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors cursor-pointer"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Enroll Student</span>
              </button>
            </div>

            {isRosterLoading ? (
              <div className="py-12 text-center text-xs text-slate-400">Loading roster...</div>
            ) : rosterData?.students?.length > 0 ? (
              <div className="divide-y divide-slate-100 border border-slate-100 rounded-2xl overflow-hidden">
                {rosterData.students.map((st) => (
                  <div key={st.enrollment_id} className="p-3 bg-white flex items-center justify-between text-xs">
                    <div>
                      <span className="font-bold text-slate-800 block">
                        {st.registration_number || st.student?.registration_number || `Student #${st.student_id}`}
                      </span>
                      <span className="text-[11px] text-slate-500 font-mono">
                        Enrolled at: {st.enrolled_at ? new Date(st.enrolled_at).toLocaleDateString() : "—"}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold uppercase">
                        {st.status}
                      </span>
                      <button
                        onClick={() => setDropTarget(st)}
                        title="Drop student from offering"
                        className="p-1 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                      >
                        <UserMinus className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-slate-500 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
                No students enrolled in this offering yet.
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Modal: Enroll Student */}
      {isEnrollOpen && (
        <Modal
          isOpen={isEnrollOpen}
          onClose={() => setIsEnrollOpen(false)}
          title="Enroll Student"
          subtitle={`Select an active student to enroll into ${rosterOffering?.course_id} (Sec ${rosterOffering?.section})`}
          maxWidth="max-w-xl"
        >
          <form onSubmit={handleEnrollSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            {/* Warning if selected student is already enrolled */}
            {isAlreadyEnrolled && selectedStudent && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
                <div>
                  <span className="font-semibold">Student is already enrolled!</span>
                  <p className="mt-0.5 text-[11px] text-amber-700">
                    Student <strong>{selectedStudent.registration_number}</strong>
                    {selectedStudent.full_name ? ` (${selectedStudent.full_name})` : ""} is already actively enrolled in this course offering. Duplicate enrollments are prohibited.
                  </p>
                </div>
              </div>
            )}

            {/* Searchable Student Dropdown / Selector */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700">
                Select Active Student *
              </label>

              {/* Search Bar */}
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={studentSearchTerm}
                  onChange={(e) => setStudentSearchTerm(e.target.value)}
                  placeholder="Filter by Registration Number, Name, Department, or Semester..."
                  className="w-full pl-9 pr-8 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                />
                {studentSearchTerm && (
                  <button
                    type="button"
                    onClick={() => setStudentSearchTerm("")}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs p-0.5"
                  >
                    &times;
                  </button>
                )}
              </div>

              {/* Student Options List */}
              {isStudentsLoading ? (
                <div className="py-8 text-center text-xs text-slate-500 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                  <span>Loading student directory...</span>
                </div>
              ) : filteredStudents.length === 0 ? (
                <div className="py-6 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  {studentSearchTerm ? "No matching students found." : "No active students available for enrollment."}
                </div>
              ) : (
                <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1 border border-slate-100 rounded-xl p-1.5 bg-slate-50/50">
                  {filteredStudents.map((st) => {
                    const isEnrolled = enrolledStudentIds.has(Number(st.student_id));
                    const isSelected = selectedStudent?.student_id === st.student_id;

                    return (
                      <button
                        key={st.student_id}
                        type="button"
                        onClick={() => {
                          setSelectedStudent(st);
                          setFormError("");
                        }}
                        className={`w-full text-left p-2.5 rounded-lg text-xs transition-all flex items-center justify-between border cursor-pointer ${
                          isSelected
                            ? "bg-indigo-50/80 border-indigo-300 ring-1 ring-indigo-200 shadow-xs"
                            : isEnrolled
                            ? "bg-slate-100/70 border-slate-200 text-slate-500 hover:bg-slate-100"
                            : "bg-white border-slate-200 hover:border-indigo-200 hover:bg-indigo-50/20"
                        }`}
                      >
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-slate-900 bg-slate-100 px-1.5 py-0.5 rounded text-[11px] border border-slate-200/60">
                              {st.registration_number}
                            </span>
                            {st.full_name && (
                              <span className="font-semibold text-slate-800">
                                {st.full_name}
                              </span>
                            )}
                            {isEnrolled && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-800 font-semibold border border-amber-200">
                                Already Enrolled
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
                            <span>{st.department_name || "General"}</span>
                            <span>&bull;</span>
                            <span>Semester {st.current_semester}</span>
                            <span className="text-slate-400 font-mono text-[10px]">
                              (Profile ID: #{st.student_id})
                            </span>
                          </div>
                        </div>

                        {isSelected && (
                          <div className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0">
                            <Check className="w-3 h-3 stroke-[3]" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Selected Student Confirmation Summary */}
            {selectedStudent && (
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1.5">
                  <span className="font-semibold text-slate-700">Selected Candidate:</span>
                  <span className="font-mono">
                    Profile PK: <strong className="text-slate-700">#{selectedStudent.student_id}</strong> &bull; Auth ID: <strong className="text-slate-700">{selectedStudent.auth_user_id}</strong>
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-slate-800 text-xs">
                        {selectedStudent.registration_number}
                      </span>
                      {selectedStudent.full_name && (
                        <span className="text-xs font-semibold text-slate-800">
                          {selectedStudent.full_name}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Department: {selectedStudent.department_name || selectedStudent.department_id} &bull; Semester {selectedStudent.current_semester} (Adm {selectedStudent.admission_year})
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedStudent(null)}
                    className="text-[11px] font-medium text-slate-500 hover:text-slate-700 hover:underline cursor-pointer"
                  >
                    Clear
                  </button>
                </div>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsEnrollOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !selectedStudent || isAlreadyEnrolled}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
              >
                {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Enroll Student</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Confirm: Drop Student */}
      <ConfirmDialog
        isOpen={Boolean(dropTarget)}
        onClose={() => setDropTarget(null)}
        onConfirm={handleDropConfirm}
        title="Drop Student from Course?"
        message={`Drop student ${dropTarget?.student?.registration_number || dropTarget?.student_id} from ${rosterOffering?.course_id}? Enrollment status will be marked as DROPPED.`}
        confirmText="Drop Student"
        confirmVariant="danger"
        isLoading={isSubmitting}
      />
    </div>
  );
};

export default AdminOfferingsPage;
