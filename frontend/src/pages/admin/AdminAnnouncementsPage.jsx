import React, { useState, useEffect, useMemo } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import {
  announcementsApi,
  departmentApi,
  offeringApi,
  formatApiError,
} from "@/services/adminService";
import {
  Megaphone,
  Plus,
  Search,
  Edit2,
  Trash2,
  CheckCircle,
  XCircle,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Globe,
  Building2,
  BookOpen,
} from "lucide-react";

export const AdminAnnouncementsPage = () => {
  const [announcements, setAnnouncements] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [offerings, setOfferings] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [scopeFilter, setScopeFilter] = useState("all");

  // Modals & Dialogs
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editAnnounce, setEditAnnounce] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Form State
  const [formData, setFormData] = useState({
    title: "",
    content: "",
    scope: "INSTITUTION",
    audience_type: "ALL",
    department_id: "",
    course_offering: "",
    is_published: true,
  });

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [list, deptList, offeringList] = await Promise.all([
        announcementsApi.getAll(),
        departmentApi.getAll().catch(() => []),
        offeringApi.getAll().catch(() => []),
      ]);
      setAnnouncements(list || []);
      setDepartments(deptList || []);
      setOfferings(offeringList || []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredAnnouncements = useMemo(() => {
    return announcements.filter((a) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        a.title?.toLowerCase().includes(q) ||
        a.content?.toLowerCase().includes(q);

      const matchesScope =
        scopeFilter === "all" || a.scope === scopeFilter;

      return matchesSearch && matchesScope;
    });
  }, [announcements, searchQuery, scopeFilter]);

  // Handle Create Announcement
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.title.trim() || !formData.content.trim()) {
      setFormError("Title and content are required.");
      return;
    }

    const payload = {
      title: formData.title.trim(),
      content: formData.content.trim(),
      scope: formData.scope,
      audience_type: formData.audience_type,
      is_published: formData.is_published,
    };

    if (formData.scope === "DEPARTMENT") {
      if (!formData.department_id) {
        setFormError("Please select a target department.");
        return;
      }
      payload.department_id = formData.department_id;
    } else if (formData.scope === "COURSE") {
      if (!formData.course_offering) {
        setFormError("Please select a target course offering.");
        return;
      }
      payload.course_offering = Number(formData.course_offering);
    }

    setIsSubmitting(true);
    try {
      await announcementsApi.create(payload);
      setIsCreateOpen(false);
      setFormData({
        title: "",
        content: "",
        scope: "INSTITUTION",
        audience_type: "ALL",
        department_id: "",
        course_offering: "",
        is_published: true,
      });
      setSuccessMessage("Announcement created and published successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Edit Announcement
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!editAnnounce.title.trim() || !editAnnounce.content.trim()) {
      setFormError("Title and content are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      await announcementsApi.update(editAnnounce.id, {
        title: editAnnounce.title.trim(),
        content: editAnnounce.content.trim(),
        audience_type: editAnnounce.audience_type,
        is_published: editAnnounce.is_published,
      });
      setEditAnnounce(null);
      setSuccessMessage("Announcement updated successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Toggle Publish
  const handleTogglePublish = async (announce) => {
    setIsSubmitting(true);
    try {
      await announcementsApi.togglePublish(announce.id, !announce.is_published);
      setSuccessMessage(
        `Announcement ${!announce.is_published ? "published" : "unpublished"} successfully.`
      );
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Announcement
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsSubmitting(true);
    try {
      await announcementsApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      setSuccessMessage("Announcement removed successfully.");
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      header: "Title & Preview",
      accessor: (row) => (
        <div>
          <span className="font-semibold text-slate-900 block">{row.title}</span>
          <span className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
            {row.content}
          </span>
        </div>
      ),
    },
    {
      header: "Scope & Target",
      accessor: (row) => {
        const scopeIcons = {
          INSTITUTION: <Globe className="w-3.5 h-3.5 text-blue-600" />,
          DEPARTMENT: <Building2 className="w-3.5 h-3.5 text-purple-600" />,
          COURSE: <BookOpen className="w-3.5 h-3.5 text-indigo-600" />,
        };
        return (
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
              {scopeIcons[row.scope] || <Globe className="w-3.5 h-3.5 text-slate-400" />}
              <span>{row.scope}</span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">
              Audience: {row.audience_type}
            </span>
          </div>
        );
      },
      className: "w-36",
    },
    {
      header: "Status",
      accessor: (row) => (
        <button
          onClick={() => handleTogglePublish(row)}
          title={row.is_published ? "Click to Unpublish" : "Click to Publish"}
          className={`inline-flex items-center gap-1 text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider border transition-colors cursor-pointer ${
            row.is_published
              ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
              : "bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-200"
          }`}
        >
          {row.is_published ? "Published" : "Draft"}
        </button>
      ),
      className: "w-28",
    },
    {
      header: "Created / Published",
      accessor: (row) => (
        <span className="text-xs text-slate-600 font-mono">
          {row.published_at ? new Date(row.published_at).toLocaleDateString() : new Date(row.created_at).toLocaleDateString()}
        </span>
      ),
      className: "w-28",
    },
    {
      header: "Actions",
      accessor: (row) => (
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => {
              setEditAnnounce({ ...row });
              setFormError("");
            }}
            title="Edit Announcement"
            className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setDeleteTarget(row)}
            title="Delete Announcement"
            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ),
      className: "w-20 text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Announcements & Broadcasts"
        subtitle="Publish campus-wide announcements, departmental notices and targeted academic broadcasts."
        badge={`${announcements.length} Notices`}
        actions={
          <button
            onClick={() => {
              setFormData({
                title: "",
                content: "",
                scope: "INSTITUTION",
                audience_type: "ALL",
                department_id: departments[0]?._id || "",
                course_offering: offerings[0]?.id || "",
                is_published: true,
              });
              setFormError("");
              setIsCreateOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Announcement</span>
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
          title="Announcement Service Error"
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
            placeholder="Search announcements..."
            className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <select
            value={scopeFilter}
            onChange={(e) => setScopeFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
          >
            <option value="all">All Scopes</option>
            <option value="INSTITUTION">INSTITUTION</option>
            <option value="DEPARTMENT">DEPARTMENT</option>
            <option value="COURSE">COURSE</option>
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
        data={filteredAnnouncements}
        isLoading={isLoading}
        emptyTitle="No announcements found"
        emptyMessage="Publish an announcement to notify students or faculty members across the campus."
        keyField="id"
      />

      {/* Modal: Create Announcement */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create Announcement"
        subtitle="Broadcast an official message or notice to students and faculty."
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
              Announcement Title *
            </label>
            <input
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="e.g. Fall Term Final Exam Schedule Published"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Scope *
              </label>
              <select
                value={formData.scope}
                onChange={(e) => setFormData({ ...formData, scope: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="INSTITUTION">INSTITUTION (Campus-wide)</option>
                <option value="DEPARTMENT">DEPARTMENT (Specific Dept)</option>
                <option value="COURSE">COURSE (Enrolled Offering)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Audience *
              </label>
              <select
                value={formData.audience_type}
                onChange={(e) => setFormData({ ...formData, audience_type: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="ALL">All (Students & Faculty)</option>
                <option value="STUDENTS">Students Only</option>
                <option value="FACULTY">Faculty Only</option>
              </select>
            </div>
          </div>

          {formData.scope === "DEPARTMENT" && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Target Department *
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
                    {d.code} - {d.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {formData.scope === "COURSE" && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Target Course Offering *
              </label>
              <select
                required
                value={formData.course_offering}
                onChange={(e) => setFormData({ ...formData, course_offering: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="">-- Choose Course Offering --</option>
                {offerings.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.course_id} (Sec {o.section}) - Term #{o.academic_term}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Content / Notice Body *
            </label>
            <textarea
              rows={4}
              required
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              placeholder="Write the complete announcement details here..."
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={formData.is_published}
                onChange={(e) => setFormData({ ...formData, is_published: e.target.checked })}
                className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-xs font-semibold text-slate-700">Publish Immediately</span>
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
              <span>Post Announcement</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Announcement */}
      {editAnnounce && (
        <Modal
          isOpen={Boolean(editAnnounce)}
          onClose={() => setEditAnnounce(null)}
          title={`Edit Announcement`}
          subtitle="Update notice body, target audience or published status."
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
                Announcement Title *
              </label>
              <input
                type="text"
                required
                value={editAnnounce.title}
                onChange={(e) => setEditAnnounce({ ...editAnnounce, title: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Audience *
              </label>
              <select
                value={editAnnounce.audience_type}
                onChange={(e) => setEditAnnounce({ ...editAnnounce, audience_type: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                <option value="ALL">All (Students & Faculty)</option>
                <option value="STUDENTS">Students Only</option>
                <option value="FACULTY">Faculty Only</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Content / Notice Body *
              </label>
              <textarea
                rows={4}
                required
                value={editAnnounce.content}
                onChange={(e) => setEditAnnounce({ ...editAnnounce, content: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={editAnnounce.is_published}
                  onChange={(e) => setEditAnnounce({ ...editAnnounce, is_published: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-xs font-semibold text-slate-700">Published and Visible</span>
              </label>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditAnnounce(null)}
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

      {/* Confirm: Delete Announcement */}
      <ConfirmDialog
        isOpen={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Announcement?"
        message={`Delete "${deleteTarget?.title}"? This announcement will be permanently removed.`}
        confirmText="Delete Announcement"
        confirmVariant="danger"
        isLoading={isSubmitting}
      />
    </div>
  );
};

export default AdminAnnouncementsPage;
