import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { courseApi, departmentApi, formatApiError } from "@/services/adminService";
import {
  BookOpen,
  Plus,
  Search,
  Edit2,
  Trash2,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Building2,
  Award,
} from "lucide-react";

export const AdminCoursesPage = () => {
  const [courses, setCourses] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editCourse, setEditCourse] = useState(null);
  const [deleteCourse, setDeleteCourse] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Form State
  const [formData, setFormData] = useState({
    name: "",
    code: "",
    department: "",
    credits: 3,
    description: "",
  });

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [courseData, deptData] = await Promise.all([
        courseApi.getAll(),
        departmentApi.getAll().catch(() => []),
      ]);
      setCourses(courseData || []);
      setDepartments(deptData || []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredCourses = useMemo(() => {
    return courses.filter((c) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        c.name?.toLowerCase().includes(q) ||
        c.code?.toLowerCase().includes(q) ||
        c.description?.toLowerCase().includes(q);

      const deptId = typeof c.department === "object" ? c.department?._id : c.department;
      const matchesDept = departmentFilter === "all" || deptId === departmentFilter;

      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" && c.isActive) ||
        (statusFilter === "inactive" && !c.isActive);

      return matchesSearch && matchesDept && matchesStatus;
    });
  }, [courses, searchQuery, departmentFilter, statusFilter]);

  // Create Course
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.name.trim() || !formData.code.trim() || !formData.department || formData.credits == null) {
      setFormError("Name, code, department, and credits are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      await courseApi.create({
        name: formData.name.trim(),
        code: formData.code.trim().toUpperCase(),
        department: formData.department,
        credits: Number(formData.credits),
        description: formData.description.trim(),
      });
      setIsCreateOpen(false);
      setFormData({
        name: "",
        code: "",
        department: "",
        credits: 3,
        description: "",
      });
      setSuccessMessage("Course created successfully in Master Catalog.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Edit Course
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!editCourse.name.trim() || !editCourse.code.trim() || !editCourse.department) {
      setFormError("Name, code, and department are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      const deptId =
        typeof editCourse.department === "object"
          ? editCourse.department?._id
          : editCourse.department;

      await courseApi.update(editCourse._id, {
        name: editCourse.name.trim(),
        code: editCourse.code.trim().toUpperCase(),
        department: deptId,
        credits: Number(editCourse.credits),
        description: editCourse.description?.trim() || "",
        isActive: editCourse.isActive,
      });
      setEditCourse(null);
      setSuccessMessage("Course updated successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Course
  const handleDeleteConfirm = async () => {
    if (!deleteCourse) return;
    setIsSubmitting(true);
    try {
      await courseApi.delete(deleteCourse._id);
      setDeleteCourse(null);
      setSuccessMessage("Course deleted successfully from catalog.");
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      header: "Course Code",
      accessor: (row) => (
        <span className="font-mono font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded text-xs">
          {row.code}
        </span>
      ),
      className: "w-28",
    },
    {
      header: "Course Title",
      accessor: (row) => (
        <div>
          <span className="font-semibold text-slate-900 block">{row.name}</span>
          {row.description && (
            <span className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
              {row.description}
            </span>
          )}
        </div>
      ),
    },
    {
      header: "Department",
      accessor: (row) => {
        const dept =
          typeof row.department === "object" && row.department !== null
            ? row.department
            : departments.find(
                (d) => d._id === row.department || d.code === row.department
              );
        const deptName = dept?.name || "Computer Science and Engineering";
        const deptCode = dept?.code || "CSE";
        return (
          <div className="flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="text-xs text-slate-800 font-medium truncate max-w-[150px]">
              {deptName}
            </span>
            {deptCode && (
              <span className="text-[10px] text-slate-400 font-mono">({deptCode})</span>
            )}
          </div>
        );
      },
    },
    {
      header: "Credits",
      accessor: (row) => (
        <span className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 rounded-full">
          <Award className="w-3 h-3 text-indigo-600" />
          <span>{row.credits} Cr</span>
        </span>
      ),
      className: "w-24 text-center",
    },
    {
      header: "Status",
      accessor: (row) => (
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
            row.isActive
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : "bg-slate-100 text-slate-500 border border-slate-200"
          }`}
        >
          {row.isActive ? "Active" : "Inactive"}
        </span>
      ),
      className: "w-24",
    },
    {
      header: "Actions",
      accessor: (row) => (
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => {
              setEditCourse({
                ...row,
                department: typeof row.department === "object" ? row.department?._id : row.department,
              });
              setFormError("");
            }}
            title="Edit Course"
            className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setDeleteCourse(row)}
            title="Delete Course"
            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ),
      className: "w-24 text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Course Master Catalog"
        subtitle="Master registry of curriculum courses, course codes, credit allocations and syllabus details."
        badge={`${courses.length} Courses`}
        actions={
          <button
            onClick={() => {
              setFormData({
                name: "",
                code: "",
                department: departments[0]?._id || "",
                credits: 3,
                description: "",
              });
              setFormError("");
              setIsCreateOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Create Course</span>
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
          title="Course Service Error"
          message={errorMessage}
          onRetry={fetchData}
        />
      )}

      {/* Curriculum Note Banner */}
      <div className="p-3.5 rounded-2xl bg-indigo-50/70 border border-indigo-100 flex items-center justify-between text-xs text-indigo-950">
        <div className="flex items-center gap-2.5">
          <BookOpen className="w-4 h-4 text-indigo-600 shrink-0" />
          <span>
            <strong>Master Curriculum Catalog:</strong> Courses defined here are available across the institution. To offer a course to enrolled students in an active academic term, schedule it in{" "}
            <Link to="/super-admin/offerings" className="font-bold underline text-indigo-700 hover:text-indigo-900">
              Course Offerings
            </Link>.
          </span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-2xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by course title or code..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap self-end sm:self-auto">
          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
          >
            <option value="all">All Departments</option>
            {departments.map((d) => (
              <option key={d._id} value={d._id}>
                {d.code} - {d.name}
              </option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive Only</option>
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
        data={filteredCourses}
        isLoading={isLoading}
        emptyTitle="No courses found"
        emptyMessage="No courses match your filter criteria. Create a course using the button above."
        keyField="_id"
      />

      {/* Modal: Create Course */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create Master Course"
        subtitle="Add a new academic course to the institutional master catalog."
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
                Course Title *
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Data Structures & Algorithms"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Course Code *
              </label>
              <input
                type="text"
                required
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                placeholder="CS201"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono uppercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Department *
              </label>
              <select
                required
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="">-- Choose Department --</option>
                {departments.map((d) => (
                  <option key={d._id} value={d._id}>
                    {d.code} - {d.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Credits (1-10) *
              </label>
              <input
                type="number"
                min={1}
                max={10}
                required
                value={formData.credits}
                onChange={(e) => setFormData({ ...formData, credits: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Description
            </label>
            <textarea
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Prerequisites, syllabus topics, laboratory components..."
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
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
              <span>Create Course</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Course */}
      {editCourse && (
        <Modal
          isOpen={Boolean(editCourse)}
          onClose={() => setEditCourse(null)}
          title={`Edit ${editCourse.name}`}
          subtitle="Update course specifications, credits, or status."
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
                  Course Title *
                </label>
                <input
                  type="text"
                  required
                  value={editCourse.name}
                  onChange={(e) => setEditCourse({ ...editCourse, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Course Code *
                </label>
                <input
                  type="text"
                  required
                  value={editCourse.code}
                  onChange={(e) => setEditCourse({ ...editCourse, code: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono uppercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Department *
                </label>
                <select
                  required
                  value={editCourse.department}
                  onChange={(e) => setEditCourse({ ...editCourse, department: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  {departments.map((d) => (
                    <option key={d._id} value={d._id}>
                      {d.code} - {d.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Credits (1-10) *
                </label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  required
                  value={editCourse.credits}
                  onChange={(e) => setEditCourse({ ...editCourse, credits: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Description
              </label>
              <textarea
                rows={3}
                value={editCourse.description || ""}
                onChange={(e) => setEditCourse({ ...editCourse, description: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={editCourse.isActive}
                  onChange={(e) => setEditCourse({ ...editCourse, isActive: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-xs font-semibold text-slate-700">Course is Active</span>
              </label>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditCourse(null)}
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

      {/* Confirm: Delete Course */}
      <ConfirmDialog
        isOpen={Boolean(deleteCourse)}
        onClose={() => setDeleteCourse(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Course?"
        message={`Delete "${deleteCourse?.name}" (${deleteCourse?.code}) from Master Catalog? Active course offerings based on this course may be impacted.`}
        confirmText="Delete Course"
        confirmVariant="danger"
        isLoading={isSubmitting}
      />
    </div>
  );
};

export default AdminCoursesPage;
