import React, { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import {
  facultyCourseApi,
  facultyAnnouncementApi,
  formatApiError,
} from "@/services/facultyService";
import {
  Megaphone,
  Plus,
  Edit2,
  Trash2,
  BookOpen,
  Calendar,
  CheckCircle,
  XCircle,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

export const FacultyAnnouncementsPage = () => {
  const { user } = useAuth();
  const [offerings, setOfferings] = useState([]);
  const [selectedOfferingId, setSelectedOfferingId] = useState("");
  const [announcements, setAnnouncements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Create Form State
  const [formData, setFormData] = useState({
    title: "",
    content: "",
    audience_type: "ALL",
    is_published: true,
  });

  // Fetch Offerings
  const fetchOfferings = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await facultyCourseApi.getMyOfferings(user?.id || user?.user_id);
      setOfferings(data || []);
      if (data?.length > 0 && !selectedOfferingId) {
        const activeOff = data.find(
          (o) => o.academic_term_status === "ACTIVE" || o.academic_term?.status === "ACTIVE"
        );
        setSelectedOfferingId(String(activeOff ? activeOff.id : data[0].id));
      }
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOfferings();
  }, [user]);

  // Fetch Announcements
  const fetchAnnouncements = async () => {
    if (!selectedOfferingId) {
      setAnnouncements([]);
      return;
    }
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await facultyAnnouncementApi.getCourseAnnouncements(selectedOfferingId);
      setAnnouncements(data || []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnnouncements();
  }, [selectedOfferingId]);

  // Handle Create
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.title.trim() || !formData.content.trim()) {
      setFormError("Title and message content are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyAnnouncementApi.createAnnouncement({
        title: formData.title.trim(),
        content: formData.content.trim(),
        scope: "COURSE",
        course_offering: Number(selectedOfferingId),
        audience_type: formData.audience_type,
        is_published: formData.is_published,
      });
      setIsCreateOpen(false);
      setFormData({
        title: "",
        content: "",
        audience_type: "ALL",
        is_published: true,
      });
      setSuccessMessage("Course announcement published successfully.");
      fetchAnnouncements();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Edit
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!editTarget.title.trim() || !editTarget.content.trim()) {
      setFormError("Title and message content are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyAnnouncementApi.updateAnnouncement(editTarget.id, {
        title: editTarget.title.trim(),
        content: editTarget.content.trim(),
        audience_type: editTarget.audience_type,
        is_published: editTarget.is_published,
      });
      setEditTarget(null);
      setSuccessMessage("Announcement updated successfully.");
      fetchAnnouncements();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Delete
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsSubmitting(true);
    try {
      await facultyAnnouncementApi.deleteAnnouncement(deleteTarget.id);
      setDeleteTarget(null);
      setSuccessMessage("Announcement deleted successfully.");
      fetchAnnouncements();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Toggle Publish
  const handleTogglePublish = async (item) => {
    setIsSubmitting(true);
    try {
      await facultyAnnouncementApi.togglePublish(item.id, !item.is_published);
      setSuccessMessage(`Announcement ${!item.is_published ? "published" : "unpublished"}.`);
      fetchAnnouncements();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      header: "Announcement Title & Message",
      accessor: (row) => (
        <div>
          <span className="font-bold text-slate-900 block text-xs">{row.title}</span>
          <p className="text-[11px] text-slate-500 line-clamp-2 mt-0.5">{row.content}</p>
        </div>
      ),
    },
    {
      header: "Target Audience",
      accessor: (row) => (
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700">
          {row.audience_type}
        </span>
      ),
      className: "w-32",
    },
    {
      header: "Published Date",
      accessor: (row) => (
        <div className="text-xs text-slate-500 font-mono">
          {row.published_at ? new Date(row.published_at).toLocaleString() : (row.created_at ? new Date(row.created_at).toLocaleDateString() : "—")}
        </div>
      ),
      className: "w-40",
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
      header: "Actions",
      accessor: (row) => (
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => {
              setEditTarget(row);
              setFormError("");
            }}
            title="Edit Announcement"
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setDeleteTarget(row)}
            title="Delete Announcement"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 border border-slate-200 transition-colors"
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
        title="Class Announcements"
        subtitle="Broadcast syllabus updates, examination alerts, and lecture notes directly to enrolled students."
        badge={`${announcements.length} Announcements`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchAnnouncements}
              title="Refresh"
              className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setFormData({
                  title: "",
                  content: "",
                  audience_type: "ALL",
                  is_published: true,
                });
                setFormError("");
                setIsCreateOpen(true);
              }}
              disabled={!selectedOfferingId}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>Post Announcement</span>
            </button>
          </div>
        }
      />

      {/* Course Offering Selector */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
          <BookOpen className="w-4 h-4 text-indigo-600" />
          <span>Active Course Offering:</span>
        </div>
        <div className="w-full sm:w-80">
          <select
            value={selectedOfferingId}
            onChange={(e) => setSelectedOfferingId(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-slate-50"
          >
            {offerings.length === 0 ? (
              <option value="">No assigned course offerings</option>
            ) : (
              offerings.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.course_id} (Sec {o.section}) &bull; {o.academic_term_name || `Term #${o.academic_term}`}
                  {o.academic_term_status ? ` • ${o.academic_term_status}` : ""}
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Alert Notices */}
      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage("")} className="font-bold">
            &times;
          </button>
        </div>
      )}

      {errorMessage && (
        <ErrorState
          title="Announcements Error"
          message={errorMessage}
          onRetry={fetchAnnouncements}
        />
      )}

      {/* Announcements Table */}
      <DataTable
        columns={columns}
        data={announcements}
        isLoading={isLoading}
        keyExtractor={(item) => item.id}
        emptyMessage="No announcements posted yet for this course offering."
      />

      {/* Modal: Create Announcement */}
      {isCreateOpen && (
        <Modal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          title="Post Course Announcement"
          subtitle={`Publish an official course update for ${
            offerings.find((o) => String(o.id) === selectedOfferingId)?.course_id || "Course"
          }`}
        >
          <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Title / Subject *</label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="e.g. Schedule Update: Lab 3 Rescheduled"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Message Content *</label>
              <textarea
                rows={4}
                required
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                placeholder="Detailed announcement text..."
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Audience</label>
                <select
                  value={formData.audience_type}
                  onChange={(e) => setFormData({ ...formData, audience_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  <option value="ALL">All Enrolled</option>
                  <option value="STUDENTS">Students Only</option>
                </select>
              </div>
              <div className="flex items-center pt-5">
                <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={formData.is_published}
                    onChange={(e) => setFormData({ ...formData, is_published: e.target.checked })}
                    className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Publish Immediately</span>
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsCreateOpen(false)}
                className="px-4 py-2 rounded-xl font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Publish</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: Edit Announcement */}
      {editTarget && (
        <Modal
          isOpen={Boolean(editTarget)}
          onClose={() => setEditTarget(null)}
          title="Edit Announcement"
          subtitle={`Editing: ${editTarget.title}`}
        >
          <form onSubmit={handleEditSubmit} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Title *</label>
              <input
                type="text"
                required
                value={editTarget.title}
                onChange={(e) => setEditTarget({ ...editTarget, title: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Content *</label>
              <textarea
                rows={4}
                required
                value={editTarget.content}
                onChange={(e) => setEditTarget({ ...editTarget, content: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Audience</label>
                <select
                  value={editTarget.audience_type}
                  onChange={(e) => setEditTarget({ ...editTarget, audience_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  <option value="ALL">All Enrolled</option>
                  <option value="STUDENTS">Students Only</option>
                </select>
              </div>
              <div className="flex items-center pt-5">
                <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={editTarget.is_published}
                    onChange={(e) => setEditTarget({ ...editTarget, is_published: e.target.checked })}
                    className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Published</span>
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditTarget(null)}
                className="px-4 py-2 rounded-xl font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors disabled:opacity-50"
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
        title="Delete Announcement"
        message={`Are you sure you want to delete announcement "${deleteTarget?.title}"?`}
        confirmText="Delete"
        isLoading={isSubmitting}
        variant="danger"
      />
    </div>
  );
};

export default FacultyAnnouncementsPage;
