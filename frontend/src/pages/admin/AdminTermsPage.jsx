import React, { useState, useEffect, useMemo } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { termApi, formatApiError } from "@/services/adminService";
import {
  Calendar,
  Plus,
  Search,
  Edit2,
  CheckCircle,
  XCircle,
  Play,
  CheckCheck,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Clock,
} from "lucide-react";

export const AdminTermsPage = () => {
  const [terms, setTerms] = useState([]);
  const [currentTerm, setCurrentTerm] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Modals & Dialogs
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editTerm, setEditTerm] = useState(null);
  const [activateTarget, setActivateTarget] = useState(null);
  const [completeTarget, setCompleteTarget] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Form State
  const [formData, setFormData] = useState({
    name: "",
    academic_year: "2026-2027",
    term_number: 1,
    start_date: "",
    end_date: "",
    status: "UPCOMING",
    is_enrollment_open: false,
  });

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [termList, active] = await Promise.all([
        termApi.getAll(),
        termApi.getCurrent(),
      ]);
      setTerms(termList || []);
      setCurrentTerm(active || null);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredTerms = useMemo(() => {
    return terms.filter((t) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        t.name?.toLowerCase().includes(q) ||
        t.academic_year?.toLowerCase().includes(q);

      const matchesStatus =
        statusFilter === "all" || t.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [terms, searchQuery, statusFilter]);

  // Create Term
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.name.trim() || !formData.start_date || !formData.end_date) {
      setFormError("Term name, start date and end date are required.");
      return;
    }
    if (new Date(formData.end_date) <= new Date(formData.start_date)) {
      setFormError("End date must be strictly after start date.");
      return;
    }

    setIsSubmitting(true);
    try {
      await termApi.create({
        ...formData,
        term_number: Number(formData.term_number),
      });
      setIsCreateOpen(false);
      setFormData({
        name: "",
        academic_year: "2026-2027",
        term_number: 1,
        start_date: "",
        end_date: "",
        status: "UPCOMING",
        is_enrollment_open: false,
      });
      setSuccessMessage("Academic term created successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Edit Term
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!editTerm.name.trim() || !editTerm.start_date || !editTerm.end_date) {
      setFormError("Term name, start date and end date are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      await termApi.update(editTerm.id, {
        name: editTerm.name.trim(),
        academic_year: editTerm.academic_year,
        term_number: Number(editTerm.term_number),
        start_date: editTerm.start_date,
        end_date: editTerm.end_date,
        is_enrollment_open: editTerm.is_enrollment_open,
      });
      setEditTerm(null);
      setSuccessMessage("Academic term updated successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Activate Term Action
  const handleActivateConfirm = async () => {
    if (!activateTarget) return;
    setIsSubmitting(true);
    try {
      await termApi.activate(activateTarget.id);
      setActivateTarget(null);
      setSuccessMessage(`Academic Term "${activateTarget.name}" activated. Previous term marked as completed.`);
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Complete Term Action
  const handleCompleteConfirm = async () => {
    if (!completeTarget) return;
    setIsSubmitting(true);
    try {
      await termApi.complete(completeTarget.id);
      setCompleteTarget(null);
      setSuccessMessage(`Academic Term "${completeTarget.name}" marked as completed.`);
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Toggle Enrollment Window Action
  const handleToggleEnrollment = async (term) => {
    setIsSubmitting(true);
    try {
      await termApi.setEnrollmentWindow(term.id, !term.is_enrollment_open);
      setSuccessMessage(
        `Enrollment window ${!term.is_enrollment_open ? "opened" : "closed"} for ${term.name}.`
      );
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      header: "Term Name",
      accessor: (row) => (
        <div>
          <span className="font-semibold text-slate-900 block">{row.name}</span>
          <span className="text-[11px] text-slate-500 font-mono mt-0.5">
            Year: {row.academic_year} &bull; Term #{row.term_number}
          </span>
        </div>
      ),
    },
    {
      header: "Dates",
      accessor: (row) => (
        <div className="text-xs text-slate-700">
          <div className="flex items-center gap-1 font-mono">
            <span>{row.start_date}</span>
            <span className="text-slate-400">&rarr;</span>
            <span>{row.end_date}</span>
          </div>
        </div>
      ),
    },
    {
      header: "Enrollment Window",
      accessor: (row) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleToggleEnrollment(row)}
            title={row.is_enrollment_open ? "Click to Close" : "Click to Open"}
            className={`inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full font-semibold border transition-colors cursor-pointer ${
              row.is_enrollment_open
                ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                : "bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200"
            }`}
          >
            {row.is_enrollment_open ? (
              <>
                <CheckCircle className="w-3 h-3 text-emerald-600" />
                <span>Open</span>
              </>
            ) : (
              <>
                <XCircle className="w-3 h-3 text-slate-400" />
                <span>Closed</span>
              </>
            )}
          </button>
        </div>
      ),
      className: "w-36",
    },
    {
      header: "Status",
      accessor: (row) => {
        const colors = {
          ACTIVE: "bg-emerald-50 text-emerald-700 border-emerald-300 font-bold",
          UPCOMING: "bg-blue-50 text-blue-700 border-blue-200",
          DRAFT: "bg-amber-50 text-amber-700 border-amber-200",
          COMPLETED: "bg-slate-100 text-slate-600 border-slate-200",
          ARCHIVED: "bg-slate-100 text-slate-400 border-slate-200",
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
            onClick={() => {
              setEditTerm({ ...row });
              setFormError("");
            }}
            title="Edit Term Details"
            className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>

          {row.status !== "ACTIVE" && row.status !== "COMPLETED" && (
            <button
              onClick={() => setActivateTarget(row)}
              title="Activate Term"
              className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
            >
              <Play className="w-3.5 h-3.5" />
            </button>
          )}

          {row.status === "ACTIVE" && (
            <button
              onClick={() => setCompleteTarget(row)}
              title="Mark as Completed"
              className="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-blue-50 transition-colors"
            >
              <CheckCheck className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      ),
      className: "w-28 text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Academic Terms Management"
        subtitle="Manage semester definitions, active academic calendars, enrollment windows and term completions."
        badge={`${terms.length} Terms`}
        actions={
          <button
            onClick={() => {
              setFormData({
                name: "",
                academic_year: "2026-2027",
                term_number: 1,
                start_date: "",
                end_date: "",
                status: "UPCOMING",
                is_enrollment_open: false,
              });
              setFormError("");
              setIsCreateOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Academic Term</span>
          </button>
        }
      />

      {/* Active Term Highlight Banner */}
      {currentTerm && (
        <div className="bg-gradient-to-r from-emerald-600 to-teal-700 rounded-2xl p-5 text-white shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-white/10 backdrop-blur-md flex items-center justify-center shrink-0 border border-white/20">
              <Calendar className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded-full bg-white/20 text-white font-bold tracking-wider uppercase text-[10px]">
                  Currently Active Term
                </span>
                <span className="text-xs text-emerald-100 font-mono">
                  {currentTerm.academic_year}
                </span>
              </div>
              <h2 className="text-lg font-extrabold mt-0.5">{currentTerm.name}</h2>
              <p className="text-xs text-emerald-100">
                Duration: {currentTerm.start_date} to {currentTerm.end_date} &bull; Enrollment:{" "}
                <strong className="underline">
                  {currentTerm.is_enrollment_open ? "OPEN" : "CLOSED"}
                </strong>
              </p>
            </div>
          </div>

          <button
            onClick={() => handleToggleEnrollment(currentTerm)}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white text-emerald-800 hover:bg-emerald-50 shadow-xs transition-colors cursor-pointer"
          >
            {currentTerm.is_enrollment_open ? "Close Enrollment" : "Open Enrollment"}
          </button>
        </div>
      )}

      {/* Alert Notices */}
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
          title="Academic Term Error"
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
            placeholder="Search by term name or academic year..."
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
            <option value="ACTIVE">ACTIVE</option>
            <option value="UPCOMING">UPCOMING</option>
            <option value="COMPLETED">COMPLETED</option>
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
        data={filteredTerms}
        isLoading={isLoading}
        emptyTitle="No academic terms found"
        emptyMessage="Create an academic term to schedule semester offerings and student enrollments."
        keyField="id"
      />

      {/* Modal: Create Term */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create Academic Term"
        subtitle="Establish a new semester or academic session."
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
              Term Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Fall 2026 Semester"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Academic Year *
              </label>
              <input
                type="text"
                required
                value={formData.academic_year}
                onChange={(e) => setFormData({ ...formData, academic_year: e.target.value })}
                placeholder="2026-2027"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Term Number *
              </label>
              <input
                type="number"
                min={1}
                max={12}
                required
                value={formData.term_number}
                onChange={(e) => setFormData({ ...formData, term_number: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Start Date *
              </label>
              <input
                type="date"
                required
                value={formData.start_date}
                onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                End Date *
              </label>
              <input
                type="date"
                required
                value={formData.end_date}
                onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={formData.is_enrollment_open}
                onChange={(e) => setFormData({ ...formData, is_enrollment_open: e.target.checked })}
                className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-xs font-semibold text-slate-700">Open Course Enrollment Immediately</span>
            </label>
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
              <span>Create Term</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Term */}
      {editTerm && (
        <Modal
          isOpen={Boolean(editTerm)}
          onClose={() => setEditTerm(null)}
          title={`Edit ${editTerm.name}`}
          subtitle="Update term dates or calendar schedules."
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
                Term Name *
              </label>
              <input
                type="text"
                required
                value={editTerm.name}
                onChange={(e) => setEditTerm({ ...editTerm, name: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Start Date *
                </label>
                <input
                  type="date"
                  required
                  value={editTerm.start_date}
                  onChange={(e) => setEditTerm({ ...editTerm, start_date: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  End Date *
                </label>
                <input
                  type="date"
                  required
                  value={editTerm.end_date}
                  onChange={(e) => setEditTerm({ ...editTerm, end_date: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditTerm(null)}
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

      {/* Confirm: Activate Term */}
      <ConfirmDialog
        isOpen={Boolean(activateTarget)}
        onClose={() => setActivateTarget(null)}
        onConfirm={handleActivateConfirm}
        title="Activate Academic Term?"
        message={`Activate "${activateTarget?.name}"? The currently active term will be automatically closed and marked as COMPLETED.`}
        confirmText="Activate Term"
        confirmVariant="primary"
        isLoading={isSubmitting}
      />

      {/* Confirm: Complete Term */}
      <ConfirmDialog
        isOpen={Boolean(completeTarget)}
        onClose={() => setCompleteTarget(null)}
        onConfirm={handleCompleteConfirm}
        title="Complete Academic Term?"
        message={`Mark "${completeTarget?.name}" as COMPLETED? Enrollment will be closed and student grades will be archived.`}
        confirmText="Complete Term"
        confirmVariant="danger"
        isLoading={isSubmitting}
      />
    </div>
  );
};

export default AdminTermsPage;
