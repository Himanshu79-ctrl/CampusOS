import React, { useState, useEffect, useMemo } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { departmentApi, facultyApi, formatApiError } from "@/services/adminService";
import {
  Building2,
  Plus,
  Search,
  Edit2,
  Trash2,
  UserCheck,
  UserX,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

export const AdminDepartmentsPage = () => {
  const [departments, setDepartments] = useState([]);
  const [facultyList, setFacultyList] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editDept, setEditDept] = useState(null);
  const [assignHodDept, setAssignHodDept] = useState(null);
  const [deleteDept, setDeleteDept] = useState(null);
  const [removeHodDept, setRemoveHodDept] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Form states
  const [formData, setFormData] = useState({ name: "", code: "", description: "" });
  const [selectedFacultyId, setSelectedFacultyId] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [deptData, facData] = await Promise.all([
        departmentApi.getAll(),
        facultyApi.getAll().catch(() => []),
      ]);
      setDepartments(deptData || []);
      setFacultyList(facData || []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Filtered list
  const filteredDepartments = useMemo(() => {
    return departments.filter((d) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        d.name?.toLowerCase().includes(q) ||
        d.code?.toLowerCase().includes(q) ||
        d.description?.toLowerCase().includes(q);

      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" && d.isActive) ||
        (statusFilter === "inactive" && !d.isActive);

      return matchesSearch && matchesStatus;
    });
  }, [departments, searchQuery, statusFilter]);

  // Handle Create Department
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.name.trim() || !formData.code.trim()) {
      setFormError("Department name and code are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      await departmentApi.create({
        name: formData.name.trim(),
        code: formData.code.trim().toUpperCase(),
        description: formData.description.trim(),
      });
      setIsCreateOpen(false);
      setFormData({ name: "", code: "", description: "" });
      setSuccessMessage("Department created successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Update Department
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!editDept.name.trim() || !editDept.code.trim()) {
      setFormError("Department name and code are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      await departmentApi.update(editDept._id, {
        name: editDept.name.trim(),
        code: editDept.code.trim().toUpperCase(),
        description: editDept.description?.trim() || "",
        isActive: editDept.isActive,
      });
      setEditDept(null);
      setSuccessMessage("Department updated successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Delete Department
  const handleDeleteConfirm = async () => {
    if (!deleteDept) return;
    setIsSubmitting(true);
    try {
      await departmentApi.delete(deleteDept._id);
      setDeleteDept(null);
      setSuccessMessage("Department deleted successfully.");
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Assign HOD
  const handleAssignHodSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!selectedFacultyId) {
      setFormError("Please select a faculty member to appoint as HOD.");
      return;
    }

    setIsSubmitting(true);
    try {
      await departmentApi.assignHOD(assignHodDept._id, selectedFacultyId);
      setAssignHodDept(null);
      setSelectedFacultyId("");
      setSuccessMessage("HOD appointed successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Remove HOD
  const handleRemoveHodConfirm = async () => {
    if (!removeHodDept) return;
    setIsSubmitting(true);
    try {
      await departmentApi.removeHOD(removeHodDept._id);
      setRemoveHodDept(null);
      setSuccessMessage("HOD assignment removed successfully.");
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Table Columns
  const columns = [
    {
      header: "Code",
      accessor: (row) => (
        <span className="font-mono font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded text-xs">
          {row.code}
        </span>
      ),
      className: "w-24",
    },
    {
      header: "Department Name",
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
      header: "HOD Leadership",
      accessor: (row) => {
        if (!row.hod) {
          return (
            <span className="text-slate-400 italic text-xs">No HOD Assigned</span>
          );
        }
        return (
          <div>
            <span className="font-medium text-slate-800 block text-xs">
              {row.hod.name || "Assigned"}
            </span>
            <span className="text-[10px] text-slate-500 font-mono">
              {row.hod.email || row.hod._id}
            </span>
          </div>
        );
      },
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
              setEditDept({ ...row });
              setFormError("");
            }}
            title="Edit Department"
            className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => {
              setAssignHodDept(row);
              setSelectedFacultyId(row.hod?._id || "");
              setFormError("");
            }}
            title="Assign HOD"
            className="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-blue-50 transition-colors"
          >
            <UserCheck className="w-3.5 h-3.5" />
          </button>
          {row.hod && (
            <button
              onClick={() => setRemoveHodDept(row)}
              title="Remove HOD Assignment"
              className="p-1.5 rounded-lg text-slate-500 hover:text-amber-600 hover:bg-amber-50 transition-colors"
            >
              <UserX className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={() => setDeleteDept(row)}
            title="Delete Department"
            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ),
      className: "w-32 text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Department Management"
        subtitle="Master catalog of academic departments, department codes, and authoritative HOD mappings."
        badge={`${departments.length} Departments`}
        actions={
          <button
            onClick={() => {
              setFormData({ name: "", code: "", description: "" });
              setFormError("");
              setIsCreateOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Department</span>
          </button>
        }
      />

      {/* Alert Notices */}
      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{successMessage}</span>
          </div>
          <button
            onClick={() => setSuccessMessage("")}
            className="text-emerald-700 hover:text-emerald-900 font-bold ml-4"
          >
            &times;
          </button>
        </div>
      )}

      {errorMessage && (
        <ErrorState
          title="Department Service Error"
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
            placeholder="Search by department name or code..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
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

      {/* Department Data Table */}
      <DataTable
        columns={columns}
        data={filteredDepartments}
        isLoading={isLoading}
        emptyTitle="No departments found"
        emptyMessage="No departments match your filter criteria. Create a new department using the button above."
        keyField="_id"
      />

      {/* Modal: Create Department */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create New Department"
        subtitle="Establish an academic department in the Admin Service."
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Department Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. Computer Science and Engineering"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Department Code *
            </label>
            <input
              type="text"
              required
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              placeholder="e.g. CSE"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono uppercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Description
            </label>
            <textarea
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Academic disciplines, research focus, or division info..."
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
              <span>Create Department</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Department */}
      {editDept && (
        <Modal
          isOpen={Boolean(editDept)}
          onClose={() => setEditDept(null)}
          title={`Edit ${editDept.name}`}
          subtitle="Update department code, title or active state."
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
                Department Name *
              </label>
              <input
                type="text"
                required
                value={editDept.name}
                onChange={(e) => setEditDept({ ...editDept, name: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Department Code *
              </label>
              <input
                type="text"
                required
                value={editDept.code}
                onChange={(e) => setEditDept({ ...editDept, code: e.target.value.toUpperCase() })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono uppercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Description
              </label>
              <textarea
                rows={3}
                value={editDept.description || ""}
                onChange={(e) => setEditDept({ ...editDept, description: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={editDept.isActive}
                  onChange={(e) => setEditDept({ ...editDept, isActive: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-xs font-semibold text-slate-700">Department is Active</span>
              </label>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditDept(null)}
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

      {/* Modal: Assign HOD */}
      {assignHodDept && (
        <Modal
          isOpen={Boolean(assignHodDept)}
          onClose={() => setAssignHodDept(null)}
          title={`Assign HOD for ${assignHodDept.name}`}
          subtitle="Select an authoritative Head of Department."
        >
          <form onSubmit={handleAssignHodSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Select Faculty Member *
              </label>
              <select
                required
                value={selectedFacultyId}
                onChange={(e) => setSelectedFacultyId(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="">-- Choose faculty member --</option>
                {facultyList.map((f) => (
                  <option key={f._id} value={f._id}>
                    {f.name} ({f.employeeId}) &bull; {f.email}
                  </option>
                ))}
              </select>
            </div>

            <p className="text-[11px] text-slate-500 leading-relaxed">
              Note: The assigned HOD will be granted authoritative access to the department's academic reports in the LMS Service.
            </p>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setAssignHodDept(null)}
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
                <span>Appoint HOD</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Confirm: Delete Department */}
      <ConfirmDialog
        isOpen={Boolean(deleteDept)}
        onClose={() => setDeleteDept(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Department?"
        message={`Are you sure you want to permanently delete "${deleteDept?.name}" (${deleteDept?.code})? Courses and faculty associated with this department may be impacted.`}
        confirmText="Delete Department"
        confirmVariant="danger"
        isLoading={isSubmitting}
      />

      {/* Confirm: Remove HOD */}
      <ConfirmDialog
        isOpen={Boolean(removeHodDept)}
        onClose={() => setRemoveHodDept(null)}
        onConfirm={handleRemoveHodConfirm}
        title="Remove HOD Assignment?"
        message={`Remove the current HOD (${removeHodDept?.hod?.name || "faculty"}) from ${removeHodDept?.name}?`}
        confirmText="Remove HOD"
        confirmVariant="danger"
        isLoading={isSubmitting}
      />
    </div>
  );
};

export default AdminDepartmentsPage;
