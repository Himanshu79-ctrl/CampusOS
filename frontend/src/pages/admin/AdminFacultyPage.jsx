import React, { useState, useEffect, useMemo } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { facultyApi, departmentApi, formatApiError } from "@/services/adminService";
import {
  GraduationCap,
  Plus,
  Search,
  Edit2,
  UserX,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Mail,
  Phone,
  Building2,
  Key,
  Copy,
  Check,
  ExternalLink,
  ShieldCheck,
  UserCheck,
} from "lucide-react";

export const AdminFacultyPage = () => {
  const [facultyList, setFacultyList] = useState([]);
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
  const [editFaculty, setEditFaculty] = useState(null);
  const [deactivateTarget, setDeactivateTarget] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Provisioning & Password Setup State
  const [provisionResult, setProvisionResult] = useState(null);
  const [provisionTarget, setProvisionTarget] = useState(null);
  const [provisionUsername, setProvisionUsername] = useState("");
  const [copiedLink, setCopiedLink] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    name: "",
    username: "",
    employeeId: "",
    email: "",
    phone: "",
    department: "",
    designation: "Assistant Professor",
  });

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [facData, deptData] = await Promise.all([
        facultyApi.getAll(),
        departmentApi.getAll().catch(() => []),
      ]);
      setFacultyList(facData || []);
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

  const filteredFaculty = useMemo(() => {
    return facultyList.filter((f) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        f.name?.toLowerCase().includes(q) ||
        f.employeeId?.toLowerCase().includes(q) ||
        f.email?.toLowerCase().includes(q) ||
        f.designation?.toLowerCase().includes(q);

      const deptId = typeof f.department === "object" ? f.department?._id : f.department;
      const matchesDept = departmentFilter === "all" || deptId === departmentFilter;

      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" && f.isActive) ||
        (statusFilter === "inactive" && !f.isActive);

      return matchesSearch && matchesDept && matchesStatus;
    });
  }, [facultyList, searchQuery, departmentFilter, statusFilter]);

  // Create Faculty
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (
      !formData.name.trim() ||
      !formData.username.trim() ||
      !formData.employeeId.trim() ||
      !formData.email.trim() ||
      !formData.department
    ) {
      setFormError("Full Name, Username, Employee ID, Email, and Department are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await facultyApi.create({
        name: formData.name.trim(),
        username: formData.username.trim().toLowerCase(),
        employeeId: formData.employeeId.trim().toUpperCase(),
        email: formData.email.trim().toLowerCase(),
        phone: formData.phone.trim(),
        department: formData.department,
        designation: formData.designation.trim(),
      });
      setIsCreateOpen(false);
      setFormData({
        name: "",
        username: "",
        employeeId: "",
        email: "",
        phone: "",
        department: "",
        designation: "Assistant Professor",
      });
      fetchData();
      if (res?.password_setup) {
        setProvisionResult(res);
      } else {
        setSuccessMessage("Faculty profile registered successfully.");
      }
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Complete Provisioning for Existing / Unlinked Faculty
  const handleProvisionSubmit = async (e) => {
    e.preventDefault();
    if (!provisionTarget) return;
    setIsSubmitting(true);
    setFormError("");
    try {
      const res = await facultyApi.provision(provisionTarget._id, {
        username: provisionUsername.trim().toLowerCase(),
      });
      setProvisionTarget(null);
      fetchData();
      if (res?.password_setup) {
        setProvisionResult(res);
      } else {
        setSuccessMessage("Faculty account provisioned successfully.");
      }
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Edit Faculty
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!editFaculty.name.trim() || !editFaculty.email.trim() || !editFaculty.department) {
      setFormError("Name, Email, and Department are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      const deptId =
        typeof editFaculty.department === "object"
          ? editFaculty.department?._id
          : editFaculty.department;

      await facultyApi.update(editFaculty._id, {
        name: editFaculty.name.trim(),
        employeeId: editFaculty.employeeId.trim().toUpperCase(),
        email: editFaculty.email.trim().toLowerCase(),
        phone: editFaculty.phone?.trim() || "",
        department: deptId,
        designation: editFaculty.designation.trim(),
      });
      setEditFaculty(null);
      setSuccessMessage("Faculty profile updated successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Deactivate Faculty
  const handleDeactivateConfirm = async () => {
    if (!deactivateTarget) return;
    setIsSubmitting(true);
    try {
      await facultyApi.deactivate(deactivateTarget._id);
      setDeactivateTarget(null);
      setSuccessMessage("Faculty member deactivated successfully.");
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      header: "Employee ID",
      accessor: (row) => (
        <span className="font-mono font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded text-xs">
          {row.employeeId}
        </span>
      ),
      className: "w-28",
    },
    {
      header: "Faculty Name",
      accessor: (row) => (
        <div>
          <span className="font-semibold text-slate-900 block">{row.name}</span>
          <span className="text-[11px] text-slate-500 block">{row.designation}</span>
        </div>
      ),
    },
    {
      header: "Contact",
      accessor: (row) => (
        <div className="space-y-0.5">
          <div className="flex items-center gap-1.5 text-xs text-slate-700">
            <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="font-mono">{row.email}</span>
          </div>
          {row.phone && (
            <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
              <Phone className="w-3 h-3 text-slate-400 shrink-0" />
              <span>{row.phone}</span>
            </div>
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
        const deptName = dept?.name || "Computer science and engineering";
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
      header: "Auth Account",
      accessor: (row) =>
        row.authUserId ? (
          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
            <ShieldCheck className="w-3 h-3 text-emerald-600 shrink-0" />
            <span>#{row.authUserId}</span>
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200">
            <span>Pending</span>
          </span>
        ),
      className: "w-28",
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
      className: "w-20",
    },
    {
      header: "Actions",
      accessor: (row) => (
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => {
              setProvisionTarget(row);
              setProvisionUsername(row.username || row.email?.split("@")[0] || "");
              setFormError("");
            }}
            title={row.authUserId ? "Generate Password Setup Link" : "Provision Auth Account"}
            className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 transition-colors cursor-pointer"
          >
            <Key className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => {
              setEditFaculty({
                ...row,
                department: typeof row.department === "object" ? row.department?._id : row.department,
              });
              setFormError("");
            }}
            title="Edit Faculty"
            className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          {row.isActive && (
            <button
              onClick={() => setDeactivateTarget(row)}
              title="Deactivate Faculty"
              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors"
            >
              <UserX className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      ),
      className: "w-24 text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Faculty Directory"
        subtitle="Institutional staff register, employee records, academic designations and departmental affiliations."
        badge={`${facultyList.length} Faculty`}
        actions={
          <button
            onClick={() => {
              setFormData({
                name: "",
                employeeId: "",
                email: "",
                phone: "",
                department: departments[0]?._id || "",
                designation: "Assistant Professor",
              });
              setFormError("");
              setIsCreateOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Add Faculty</span>
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
          title="Faculty Service Error"
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
            placeholder="Search by faculty name, ID, or email..."
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
        data={filteredFaculty}
        isLoading={isLoading}
        emptyTitle="No faculty members found"
        emptyMessage="No faculty records match your criteria. Add new faculty using the button above."
        keyField="_id"
      />

      {/* Modal: Add Faculty */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Add Faculty Member"
        subtitle="Register an academic instructor or professor in the Admin Service."
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
                Full Name *
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Dr. Alan Turing"
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
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    username: e.target.value.toLowerCase().replace(/\s+/g, ""),
                  })
                }
                placeholder="aturing or dr_turing"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono lowercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
              <p className="text-[10px] text-slate-400 mt-0.5">Required login identifier for authentication account.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Employee ID *
              </label>
              <input
                type="text"
                required
                value={formData.employeeId}
                onChange={(e) => setFormData({ ...formData, employeeId: e.target.value.toUpperCase() })}
                placeholder="FAC-CSE-001"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono uppercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Email Address *
              </label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="faculty@campusos.edu"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Phone Number
            </label>
            <input
              type="text"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              placeholder="+1 (555) 019-2834"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
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
                Designation *
              </label>
              <select
                value={formData.designation}
                onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="Professor">Professor</option>
                <option value="Associate Professor">Associate Professor</option>
                <option value="Assistant Professor">Assistant Professor</option>
                <option value="Lecturer">Lecturer</option>
                <option value="Adjunct Faculty">Adjunct Faculty</option>
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
              <span>Register Faculty</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Faculty */}
      {editFaculty && (
        <Modal
          isOpen={Boolean(editFaculty)}
          onClose={() => setEditFaculty(null)}
          title={`Edit ${editFaculty.name}`}
          subtitle="Update contact details, designation or department affiliation."
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
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={editFaculty.name}
                  onChange={(e) => setEditFaculty({ ...editFaculty, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Employee ID *
                </label>
                <input
                  type="text"
                  required
                  value={editFaculty.employeeId}
                  onChange={(e) => setEditFaculty({ ...editFaculty, employeeId: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono uppercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Address *
                </label>
                <input
                  type="email"
                  required
                  value={editFaculty.email}
                  onChange={(e) => setEditFaculty({ ...editFaculty, email: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Phone Number
                </label>
                <input
                  type="text"
                  value={editFaculty.phone || ""}
                  onChange={(e) => setEditFaculty({ ...editFaculty, phone: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
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
                  value={editFaculty.department}
                  onChange={(e) => setEditFaculty({ ...editFaculty, department: e.target.value })}
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
                  Designation *
                </label>
                <select
                  value={editFaculty.designation}
                  onChange={(e) => setEditFaculty({ ...editFaculty, designation: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  <option value="Professor">Professor</option>
                  <option value="Associate Professor">Associate Professor</option>
                  <option value="Assistant Professor">Assistant Professor</option>
                  <option value="Lecturer">Lecturer</option>
                  <option value="Adjunct Faculty">Adjunct Faculty</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditFaculty(null)}
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

      {/* Confirm: Deactivate Faculty */}
      <ConfirmDialog
        isOpen={Boolean(deactivateTarget)}
        onClose={() => setDeactivateTarget(null)}
        onConfirm={handleDeactivateConfirm}
        title="Deactivate Faculty Member?"
        message={`Deactivate ${deactivateTarget?.name} (${deactivateTarget?.employeeId})? The faculty member will remain in archives but will not be available for new course allocations.`}
        confirmText="Deactivate Faculty"
        confirmVariant="danger"
        isLoading={isSubmitting}
      />

      {/* Modal: Provision Existing Faculty Account */}
      {provisionTarget && (
        <Modal
          isOpen={Boolean(provisionTarget)}
          onClose={() => setProvisionTarget(null)}
          title={`Provision Account: ${provisionTarget.name}`}
          subtitle="Generate a one-time password setup link and link authentication credentials."
        >
          <form onSubmit={handleProvisionSubmit} className="space-y-4">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Employee ID:</span>
                <span className="font-mono font-bold text-slate-800">{provisionTarget.employeeId}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Email Address:</span>
                <span className="font-mono text-slate-800">{provisionTarget.email}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Department:</span>
                <span className="font-medium text-slate-800">
                  {typeof provisionTarget.department === "object"
                    ? provisionTarget.department?.name
                    : "Assigned Department"}
                </span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Username for Auth Account *
              </label>
              <input
                type="text"
                required
                value={provisionUsername}
                onChange={(e) => setProvisionUsername(e.target.value.toLowerCase().replace(/\s+/g, ""))}
                placeholder="e.g. dr_kalpana or kalpana"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono lowercase text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                The login username the instructor will use to sign in to CampusOS.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setProvisionTarget(null)}
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
                <span>Generate Setup Link</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: Provision Success & Password Setup Link */}
      {provisionResult && (
        <Modal
          isOpen={Boolean(provisionResult)}
          onClose={() => setProvisionResult(null)}
          title="Faculty Account Provisioned Successfully"
          subtitle="Authentication account and faculty profile are now active."
          maxWidth="max-w-xl"
        >
          <div className="space-y-4">
            {/* Account Confirmation Banner */}
            <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-950 space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <span className="font-bold text-sm">
                  {provisionResult.data?.name || provisionResult.user?.full_name || provisionResult.user?.username} ({provisionResult.data?.employeeId || "FACULTY"})
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs pt-2 border-t border-emerald-200/60 font-mono">
                <div>
                  <span className="text-[10px] text-emerald-700 font-sans block uppercase font-bold">Username</span>
                  <span>{provisionResult.user?.username || provisionResult.data?.username}</span>
                </div>
                <div>
                  <span className="text-[10px] text-emerald-700 font-sans block uppercase font-bold">Auth User ID</span>
                  <span className="font-bold text-emerald-800">#{provisionResult.user?.id || provisionResult.data?.authUserId}</span>
                </div>
                <div>
                  <span className="text-[10px] text-emerald-700 font-sans block uppercase font-bold">Email</span>
                  <span className="truncate block" title={provisionResult.user?.email || provisionResult.data?.email}>
                    {provisionResult.user?.email || provisionResult.data?.email}
                  </span>
                </div>
              </div>
            </div>

            {/* Password Setup Link Box */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-800 flex items-center gap-1.5 uppercase tracking-wider">
                  <Key className="w-3.5 h-3.5 text-indigo-600" />
                  <span>One-Time Password Setup Link</span>
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
                  "Share this one-time link with the faculty member so they can securely configure their password and access their faculty portal."}
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
    </div>
  );
};

export default AdminFacultyPage;
