import React, { useState, useEffect, useCallback } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { studentAdminApi, departmentApi, userAdminApi, formatApiError } from "@/services/adminService";
import {
  Users,
  Plus,
  Search,
  Eye,
  Edit2,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  GraduationCap,
  Calendar,
  CheckSquare,
  Award,
  Copy,
  Check,
  ExternalLink,
  Mail,
  User,
  Key,
} from "lucide-react";

export const AdminStudentsPage = () => {
  const [students, setStudents] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, page_size: 20, total_pages: 1, count: 0 });
  const [departments, setDepartments] = useState([]);
  const [authUsers, setAuthUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [semesterFilter, setSemesterFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [page, setPage] = useState(1);

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [provisionResult, setProvisionResult] = useState(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [editStudent, setEditStudent] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Create Form State
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    username: "",
    registration_number: "",
    department_id: "",
    admission_year: new Date().getFullYear(),
    current_semester: 1,
  });

  const fetchStudents = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const params = {
        page,
        page_size: 20,
      };
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (departmentFilter) {
        const selectedDept = departments.find(
          (d) => d._id === departmentFilter || d.code === departmentFilter
        );
        if (selectedDept) {
          params.department_id = `${selectedDept._id},${selectedDept.code}`;
        } else {
          params.department_id = departmentFilter;
        }
      }
      if (semesterFilter) params.current_semester = semesterFilter;
      if (activeFilter !== "") params.is_active = activeFilter;

      const data = await studentAdminApi.getAll(params);
      setStudents(data?.results || []);
      setPagination({
        page: data?.page || 1,
        page_size: data?.page_size || 20,
        total_pages: data?.total_pages || 1,
        count: data?.count || 0,
      });
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  }, [page, searchQuery, departmentFilter, semesterFilter, activeFilter]);

  useEffect(() => {
    fetchStudents();
  }, [fetchStudents]);

  useEffect(() => {
    Promise.all([
      departmentApi.getAll().catch(() => []),
      userAdminApi.getAll({ role: "student" }).catch(() => []),
    ]).then(([depts, users]) => {
      setDepartments(depts || []);
      setAuthUsers(Array.isArray(users) ? users : users?.results || []);
    });
  }, []);

  // Handle Search submit
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchStudents();
  };

  // Handle Create Student Profile
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    if (
      !formData.full_name.trim() ||
      !formData.email.trim() ||
      !formData.username.trim() ||
      !formData.registration_number.trim() ||
      !formData.department_id
    ) {
      setFormError("All required personal, login, and academic details must be provided.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await studentAdminApi.unifiedProvision({
        full_name: formData.full_name.trim(),
        email: formData.email.trim().toLowerCase(),
        username: formData.username.trim().toLowerCase(),
        registration_number: formData.registration_number.trim().toUpperCase(),
        department_id: formData.department_id.trim(),
        admission_year: Number(formData.admission_year),
        current_semester: Number(formData.current_semester),
      });

      setIsCreateOpen(false);
      setProvisionResult(res);
      setFormData({
        full_name: "",
        email: "",
        username: "",
        registration_number: "",
        department_id: departments[0]?._id || "",
        admission_year: new Date().getFullYear(),
        current_semester: 1,
      });
      setSuccessMessage(
        `Student account ${res.user?.username} (${res.profile?.registration_number}) provisioned successfully.`
      );
      fetchStudents();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Edit Student
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    setIsSubmitting(true);
    try {
      await studentAdminApi.update(editStudent.student_id, {
        current_semester: Number(editStudent.current_semester),
        is_active: editStudent.is_active,
      });
      setEditStudent(null);
      setSuccessMessage("Student academic profile updated successfully.");
      fetchStudents();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      header: "Student",
      accessor: (row) => {
        const user = authUsers.find((u) => String(u.id) === String(row.auth_user_id));
        const fullName =
          user?.full_name ||
          [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
          user?.username ||
          "Student";
        return (
          <div>
            <span className="font-semibold text-slate-900 block text-xs">
              {fullName}
            </span>
            <span className="text-[11px] text-slate-500 font-mono block">
              {user?.email || (user?.username ? `@${user.username}` : `User #${row.auth_user_id}`)}
            </span>
          </div>
        );
      },
    },
    {
      header: "Reg Number",
      accessor: (row) => (
        <span className="font-mono font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded text-xs">
          {row.registration_number}
        </span>
      ),
      className: "w-32",
    },
    {
      header: "Department & Year",
      accessor: (row) => {
        const dept = departments.find(
          (d) => d._id === row.department_id || d.code === row.department_id
        );
        const deptName = dept
          ? dept.name
          : row.department_id === "DEPT_CS" || row.department_id === "CSE"
            ? "Computer Science & Engineering"
            : row.department_id?.length === 24
              ? "Engineering"
              : row.department_id || "General";

        return (
          <div>
            <span className="font-semibold text-slate-800 block text-xs">
              {deptName}
            </span>
            <span className="text-[11px] text-slate-500 font-mono">
              Adm Year: {row.admission_year} &bull; Sem {row.current_semester}
            </span>
          </div>
        );
      },
    },
    {
      header: "Enrollments",
      accessor: (row) => (
        <span className="text-xs text-slate-700 font-medium">
          {row.enrolled_courses_count} courses
        </span>
      ),
      className: "w-24 text-center",
    },
    {
      header: "Attendance",
      accessor: (row) => {
        const pct = row.attendance?.attendance_percentage;
        if (pct === null || pct === undefined) {
          return <span className="text-slate-400 text-xs">—</span>;
        }
        return (
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
              pct >= 75
                ? "bg-emerald-50 text-emerald-700"
                : "bg-rose-50 text-rose-700"
            }`}
          >
            {pct}%
          </span>
        );
      },
      className: "w-24 text-center",
    },
    {
      header: "Avg Score",
      accessor: (row) => {
        const score = row.grades?.average_score_percentage;
        if (score === null || score === undefined) {
          return <span className="text-slate-400 text-xs">—</span>;
        }
        return <span className="text-xs font-bold text-indigo-700">{score}%</span>;
      },
      className: "w-24 text-center",
    },
    {
      header: "Status",
      accessor: (row) => (
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
            row.is_active
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : "bg-slate-100 text-slate-500 border border-slate-200"
          }`}
        >
          {row.is_active ? "Active" : "Inactive"}
        </span>
      ),
      className: "w-20",
    },
    {
      header: "Actions",
      accessor: (row) => (
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setSelectedStudent(row)}
            title="View Academic Record"
            className="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-blue-50 transition-colors"
          >
            <Eye className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => {
              setEditStudent({ ...row });
              setFormError("");
            }}
            title="Edit Semester or Status"
            className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ),
      className: "w-20 text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Student Management"
        subtitle="Manage student enrollment profiles, admission records, attendance compliance and academic progress."
        badge={`${pagination.count} Students`}
        actions={
          <button
            onClick={() => {
              setFormData({
                full_name: "",
                email: "",
                username: "",
                registration_number: "",
                department_id: departments[0]?._id || "",
                admission_year: new Date().getFullYear(),
                current_semester: 1,
              });
              setFormError("");
              setIsCreateOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Provision Student</span>
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
          title="Student Service Error"
          message={errorMessage}
          onRetry={fetchStudents}
        />
      )}

      {/* Filter Toolbar */}
      <form
        onSubmit={handleSearchSubmit}
        className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-2xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3"
      >
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by registration number or user ID..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap self-end sm:self-auto">
          <select
            value={departmentFilter}
            onChange={(e) => {
              setDepartmentFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d._id} value={d._id}>
                {d.code} - {d.name}
              </option>
            ))}
          </select>

          <select
            value={semesterFilter}
            onChange={(e) => {
              setSemesterFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
          >
            <option value="">All Semesters</option>
            {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
              <option key={s} value={s}>
                Semester {s}
              </option>
            ))}
          </select>

          <select
            value={activeFilter}
            onChange={(e) => {
              setActiveFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
          >
            <option value="">All Statuses</option>
            <option value="true">Active Only</option>
            <option value="false">Inactive Only</option>
          </select>

          <button
            type="submit"
            className="px-3 py-1.5 rounded-xl text-xs font-semibold text-white bg-slate-800 hover:bg-slate-900 transition-colors"
          >
            Filter
          </button>

          <button
            type="button"
            onClick={fetchStudents}
            title="Refresh"
            className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>

      <DataTable
        columns={columns}
        data={students}
        isLoading={isLoading}
        emptyTitle="No student records found"
        emptyMessage="No students match your filter criteria. Provision a student profile to begin tracking enrollment."
        keyField="student_id"
      />

      {/* Pagination controls */}
      {pagination.total_pages > 1 && (
        <div className="flex items-center justify-between px-2 text-xs text-slate-600">
          <span>
            Page {pagination.page} of {pagination.total_pages} &bull; Total {pagination.count} records
          </span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2 font-mono font-bold">{page}</span>
            <button
              onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
              disabled={page >= pagination.total_pages}
              className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Modal: Provision Student Account & Profile */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Register & Provision Student"
        subtitle="Create student authentication account and LMS academic profile in one unified workflow."
        maxWidth="max-w-xl"
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          {/* Section 1: Personal & Login Details */}
          <div className="space-y-3 pb-3 border-b border-slate-100">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-indigo-600" />
              <span>Personal & Login Credentials</span>
            </h4>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Full Name *
              </label>
              <input
                type="text"
                required
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                placeholder="e.g. Alex Johnson"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Address *
                </label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="alex.johnson@campusos.edu"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Username *
                </label>
                <input
                  type="text"
                  required
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  placeholder="e.g. alex_johnson"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 font-mono"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Academic Details */}
          <div className="space-y-3 pt-1">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <GraduationCap className="w-3.5 h-3.5 text-indigo-600" />
              <span>Academic Details</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Registration Number *
                </label>
                <input
                  type="text"
                  required
                  value={formData.registration_number}
                  onChange={(e) => setFormData({ ...formData, registration_number: e.target.value.toUpperCase() })}
                  placeholder="2026CSE001"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono uppercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
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

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Admission Year *
                </label>
                <input
                  type="number"
                  min={2000}
                  max={2100}
                  required
                  value={formData.admission_year}
                  onChange={(e) => setFormData({ ...formData, admission_year: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Current Semester (1-8) *
                </label>
                <input
                  type="number"
                  min={1}
                  max={8}
                  required
                  value={formData.current_semester}
                  onChange={(e) => setFormData({ ...formData, current_semester: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
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
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>Register & Provision Student</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Provision Success & Password Setup Link */}
      {provisionResult && (
        <Modal
          isOpen={Boolean(provisionResult)}
          onClose={() => setProvisionResult(null)}
          title="Student Provisioned Successfully"
          subtitle="Authentication account and LMS academic profile are now active."
          maxWidth="max-w-xl"
        >
          <div className="space-y-4">
            {/* Account Confirmation Banner */}
            <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-950 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <span className="font-bold text-sm">
                  {provisionResult.user?.first_name || provisionResult.user?.username} ({provisionResult.profile?.registration_number})
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs pt-2 border-t border-emerald-200/60 font-mono">
                <div>
                  <span className="text-[10px] text-emerald-700 font-sans block uppercase font-bold">Username</span>
                  <span>{provisionResult.user?.username}</span>
                </div>
                <div>
                  <span className="text-[10px] text-emerald-700 font-sans block uppercase font-bold">Auth User ID</span>
                  <span className="font-bold text-emerald-800">#{provisionResult.user?.id}</span>
                </div>
                <div>
                  <span className="text-[10px] text-emerald-700 font-sans block uppercase font-bold">Email</span>
                  <span className="truncate block" title={provisionResult.user?.email}>{provisionResult.user?.email}</span>
                </div>
              </div>
            </div>

            {/* Password Setup Link Box */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-800 flex items-center gap-1.5 uppercase tracking-wider">
                  <Key className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Single-Use Password Setup Link</span>
                </h4>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-semibold">
                  Time-Limited
                </span>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={`${window.location.origin}${provisionResult.password_setup?.setup_url || ""}`}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono text-slate-700 bg-white select-all focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => {
                    const fullUrl = `${window.location.origin}${provisionResult.password_setup?.setup_url || ""}`;
                    navigator.clipboard.writeText(fullUrl);
                    setCopiedLink(true);
                    setTimeout(() => setCopiedLink(false), 2500);
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shrink-0 transition-colors cursor-pointer"
                >
                  {copiedLink ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedLink ? "Copied!" : "Copy"}</span>
                </button>
              </div>

              <p className="text-[11px] text-slate-500 leading-relaxed">
                {provisionResult.password_setup?.notice ||
                  "Share this one-time link with the student so they can securely set their initial password and access their student portal."}
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <a
                href={`${window.location.origin}${provisionResult.password_setup?.setup_url || ""}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                <span>Test Setup Link</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
              <button
                type="button"
                onClick={() => setProvisionResult(null)}
                className="px-5 py-2 rounded-xl text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 transition-colors cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: View Student Academic Details */}
      {selectedStudent && (() => {
        const user = authUsers.find((u) => String(u.id) === String(selectedStudent.auth_user_id));
        const fullName =
          user?.full_name ||
          [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
          user?.username ||
          "Student";
        const dept = departments.find(
          (d) => d._id === selectedStudent.department_id || d.code === selectedStudent.department_id
        );
        const deptName = dept
          ? dept.name
          : selectedStudent.department_id === "DEPT_CS" || selectedStudent.department_id === "CSE"
            ? "Computer Science & Engineering"
            : selectedStudent.department_id?.length === 24
              ? "Engineering"
              : selectedStudent.department_id || "General";

        return (
          <Modal
            isOpen={Boolean(selectedStudent)}
            onClose={() => setSelectedStudent(null)}
            title={`Student Profile: ${fullName}`}
            subtitle={`Registration No: ${selectedStudent.registration_number} • ${deptName}`}
            maxWidth="max-w-2xl"
          >
            <div className="space-y-4">
              {/* Personal & Academic Summary Banner */}
              <div className="p-4 rounded-2xl bg-indigo-50/70 border border-indigo-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-sm shrink-0">
                    {fullName.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-indigo-950">{fullName}</h3>
                    <div className="flex items-center gap-2 text-xs text-indigo-700">
                      <span>{user?.email || "No email registered"}</span>
                      {user?.username && <span className="font-mono">(@{user.username})</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold px-2.5 py-1 rounded-lg bg-white border border-indigo-200 text-indigo-900">
                    {selectedStudent.registration_number}
                  </span>
                  <span
                    className={`text-[10px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wider border ${
                      selectedStudent.is_active
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : "bg-slate-100 text-slate-500 border-slate-200"
                    }`}
                  >
                    {selectedStudent.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>

              {/* Academic Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Department</span>
                  <span className="text-xs font-bold text-slate-800 line-clamp-1">{deptName}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Semester & Year</span>
                  <span className="text-xs font-bold text-slate-800">
                    Sem {selectedStudent.current_semester} (Adm {selectedStudent.admission_year})
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Enrolled Courses</span>
                  <span className="text-xs font-bold text-slate-800">
                    {selectedStudent.enrolled_courses_count} courses
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Attendance Rate</span>
                  <span className="text-xs font-bold text-slate-800">
                    {selectedStudent.attendance?.attendance_percentage != null
                      ? `${selectedStudent.attendance.attendance_percentage}%`
                      : "No records"}
                  </span>
                </div>
              </div>

              {/* Detailed Metrics */}
              <div className="space-y-2 border-t border-slate-100 pt-3">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Detailed Academic Standing
                </h4>
                <div className="text-xs text-slate-600 space-y-1.5 bg-slate-50 p-4 rounded-xl border border-slate-100">
                  <p>
                    <strong>Classroom Attendance:</strong> {selectedStudent.attendance?.attended_sessions || 0} of {selectedStudent.attendance?.total_sessions || 0} sessions attended
                  </p>
                  <p>
                    <strong>Assignments:</strong> {selectedStudent.assignments?.submitted_count || 0} submitted ({selectedStudent.assignments?.graded_count || 0} graded)
                  </p>
                  <p>
                    <strong>Grade Average:</strong> {selectedStudent.grades?.average_score_percentage != null ? `${selectedStudent.grades.average_score_percentage}%` : "No graded scorecards"}
                  </p>
                  <div className="pt-1 text-[11px] text-slate-400 font-mono flex items-center gap-3">
                    <span>Student Profile ID: #{selectedStudent.student_id || selectedStudent.id}</span>
                    <span>•</span>
                    <span>Auth User ID: #{selectedStudent.auth_user_id}</span>
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedStudent(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-white hover:bg-slate-900 transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          </Modal>
        );
      })()}

      {/* Modal: Edit Student Profile */}
      {editStudent && (
        <Modal
          isOpen={Boolean(editStudent)}
          onClose={() => setEditStudent(null)}
          title={`Edit Student: ${editStudent.registration_number}`}
          subtitle="Update semester progression or toggle active status."
        >
          <form onSubmit={handleEditSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Current Semester (1-8) *
              </label>
              <input
                type="number"
                min={1}
                max={8}
                required
                value={editStudent.current_semester}
                onChange={(e) => setEditStudent({ ...editStudent, current_semester: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={editStudent.is_active}
                  onChange={(e) => setEditStudent({ ...editStudent, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-xs font-semibold text-slate-700">Student is Active in LMS</span>
              </label>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditStudent(null)}
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
    </div>
  );
};

export default AdminStudentsPage;
