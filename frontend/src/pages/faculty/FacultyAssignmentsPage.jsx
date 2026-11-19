import React, { useState, useEffect, useMemo } from "react";
import { useAuth } from "@/hooks/useAuth";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import {
  facultyCourseApi,
  facultyAssignmentApi,
  formatApiError,
} from "@/services/facultyService";
import {
  CheckSquare,
  Plus,
  Search,
  Edit2,
  Trash2,
  Eye,
  CheckCircle,
  XCircle,
  Clock,
  BookOpen,
  Calendar,
  Award,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  FileCheck,
} from "lucide-react";

export const FacultyAssignmentsPage = () => {
  const { user } = useAuth();
  const [offerings, setOfferings] = useState([]);
  const [selectedOfferingId, setSelectedOfferingId] = useState("");
  const [assignments, setAssignments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  // Submissions modal state
  const [viewSubmissionsAssignment, setViewSubmissionsAssignment] = useState(null);
  const [submissionsList, setSubmissionsList] = useState([]);
  const [isSubmissionsLoading, setIsSubmissionsLoading] = useState(false);
  const [submissionsError, setSubmissionsError] = useState("");

  // Grade submission modal
  const [gradingSubmission, setGradingSubmission] = useState(null);
  const [gradeFormData, setGradeFormData] = useState({ marks_obtained: "", feedback: "" });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Create Form State
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    due_date: "",
    max_marks: 100,
    weightage: 10,
    allow_late_submission: true,
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

  // Fetch Assignments for active offering
  const fetchAssignments = async () => {
    if (!selectedOfferingId) {
      setAssignments([]);
      return;
    }
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await facultyAssignmentApi.getAssignments(selectedOfferingId);
      setAssignments(data || []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAssignments();
  }, [selectedOfferingId]);

  // Submissions loader
  const handleOpenSubmissions = async (assignment) => {
    setViewSubmissionsAssignment(assignment);
    setIsSubmissionsLoading(true);
    setSubmissionsError("");
    try {
      const data = await facultyAssignmentApi.getSubmissions(assignment.id);
      setSubmissionsList(data || []);
    } catch (err) {
      setSubmissionsError(formatApiError(err));
    } finally {
      setIsSubmissionsLoading(false);
    }
  };

  // Filtered Assignments
  const filteredAssignments = useMemo(() => {
    return assignments.filter((a) => {
      const q = searchQuery.toLowerCase();
      return !q || a.title?.toLowerCase().includes(q) || a.description?.toLowerCase().includes(q);
    });
  }, [assignments, searchQuery]);

  // Create Assignment
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.title.trim() || !formData.due_date) {
      setFormError("Title and Due Date are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyAssignmentApi.createAssignment(selectedOfferingId, {
        title: formData.title.trim(),
        description: formData.description.trim(),
        due_date: formData.due_date,
        max_marks: Number(formData.max_marks) || 100,
        weightage: Number(formData.weightage) || 10,
        allow_late_submission: formData.allow_late_submission,
        is_published: formData.is_published,
      });
      setIsCreateOpen(false);
      setFormData({
        title: "",
        description: "",
        due_date: "",
        max_marks: 100,
        weightage: 10,
        allow_late_submission: true,
        is_published: true,
      });
      setSuccessMessage("Assignment created successfully.");
      fetchAssignments();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Edit Assignment
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!editTarget.title.trim() || !editTarget.due_date) {
      setFormError("Title and Due Date are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyAssignmentApi.updateAssignment(editTarget.id, {
        title: editTarget.title.trim(),
        description: editTarget.description?.trim() || "",
        due_date: editTarget.due_date,
        max_marks: Number(editTarget.max_marks) || 100,
        weightage: Number(editTarget.weightage) || 10,
        allow_late_submission: editTarget.allow_late_submission,
        is_published: editTarget.is_published,
      });
      setEditTarget(null);
      setSuccessMessage("Assignment updated successfully.");
      fetchAssignments();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Assignment
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsSubmitting(true);
    try {
      await facultyAssignmentApi.deleteAssignment(deleteTarget.id);
      setDeleteTarget(null);
      setSuccessMessage("Assignment deleted successfully.");
      fetchAssignments();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Toggle Publish
  const handleTogglePublish = async (assignment) => {
    setIsSubmitting(true);
    try {
      await facultyAssignmentApi.togglePublish(assignment.id, !assignment.is_published);
      setSuccessMessage(`Assignment ${!assignment.is_published ? "published" : "unpublished"}.`);
      fetchAssignments();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit Grade
  const handleGradeSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (gradeFormData.marks_obtained === "") {
      setFormError("Marks obtained is required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyAssignmentApi.gradeSubmission(gradingSubmission.id, {
        marks_obtained: Number(gradeFormData.marks_obtained),
        feedback: gradeFormData.feedback.trim(),
      });
      setGradingSubmission(null);
      setSuccessMessage("Submission graded successfully.");
      // Refresh submissions
      if (viewSubmissionsAssignment) {
        handleOpenSubmissions(viewSubmissionsAssignment);
      }
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      header: "Assignment Title",
      accessor: (row) => (
        <div>
          <span className="font-bold text-slate-900 block text-xs">{row.title}</span>
          <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">{row.description || "No description provided."}</p>
        </div>
      ),
    },
    {
      header: "Due Date",
      accessor: (row) => (
        <div className="text-xs text-slate-700 flex items-center gap-1 font-mono">
          <Calendar className="w-3.5 h-3.5 text-slate-400" />
          <span>{row.due_date ? new Date(row.due_date).toLocaleString() : "—"}</span>
        </div>
      ),
    },
    {
      header: "Marks & Weight",
      accessor: (row) => (
        <div className="text-xs text-slate-700 font-mono">
          <span className="font-bold">{row.max_marks ?? 100} pts</span>
          <span className="text-[11px] text-slate-400 block font-sans">Weight: {row.weightage ?? 10}%</span>
        </div>
      ),
      className: "w-28",
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
      header: "Submissions",
      accessor: (row) => (
        <button
          onClick={() => handleOpenSubmissions(row)}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer"
        >
          <FileCheck className="w-3.5 h-3.5" />
          <span>Submissions</span>
        </button>
      ),
      className: "w-32",
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
            title="Edit Assignment"
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setDeleteTarget(row)}
            title="Delete Assignment"
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
        title="Assignments & Evaluations"
        subtitle="Schedule assignments, inspect submissions, and record marks and student evaluations."
        badge={`${assignments.length} Assignments`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchAssignments}
              title="Refresh"
              className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setFormData({
                  title: "",
                  description: "",
                  due_date: "",
                  max_marks: 100,
                  weightage: 10,
                  allow_late_submission: true,
                  is_published: true,
                });
                setFormError("");
                setIsCreateOpen(true);
              }}
              disabled={!selectedOfferingId}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>Create Assignment</span>
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
          title="Assignments Load Error"
          message={errorMessage}
          onRetry={fetchAssignments}
        />
      )}

      {/* Assignments Table */}
      <DataTable
        columns={columns}
        data={filteredAssignments}
        isLoading={isLoading}
        keyExtractor={(item) => item.id}
        emptyMessage="No assignments created yet for this course offering."
      />

      {/* Modal: Create Assignment */}
      {isCreateOpen && (
        <Modal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          title="Create Course Assignment"
          subtitle="Publish a new homework, project, or assessment requirement."
        >
          <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Assignment Title *</label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="e.g. Assignment 1: Dynamic Programming"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Instructions / Description</label>
              <textarea
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Provide task instructions, guidelines, and rubric notes..."
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Due Date & Time *</label>
                <input
                  type="datetime-local"
                  required
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Max Marks (pts)</label>
                <input
                  type="number"
                  min="1"
                  value={formData.max_marks}
                  onChange={(e) => setFormData({ ...formData, max_marks: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 font-mono"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Weightage (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={formData.weightage}
                  onChange={(e) => setFormData({ ...formData, weightage: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 font-mono"
                />
              </div>
            </div>
            <div className="flex items-center gap-6 pt-2">
              <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={formData.allow_late_submission}
                  onChange={(e) =>
                    setFormData({ ...formData, allow_late_submission: e.target.checked })
                  }
                  className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <span>Allow Late Submissions</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={formData.is_published}
                  onChange={(e) =>
                    setFormData({ ...formData, is_published: e.target.checked })
                  }
                  className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <span>Publish Immediately</span>
              </label>
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
                <span>Create Assignment</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: View Submissions */}
      {viewSubmissionsAssignment && (
        <Modal
          isOpen={Boolean(viewSubmissionsAssignment)}
          onClose={() => setViewSubmissionsAssignment(null)}
          title={`Submissions: ${viewSubmissionsAssignment.title}`}
          subtitle={`Max Marks: ${viewSubmissionsAssignment.max_marks} pts • Due: ${
            viewSubmissionsAssignment.due_date
              ? new Date(viewSubmissionsAssignment.due_date).toLocaleDateString()
              : "—"
          }`}
        >
          <div className="space-y-4 text-xs">
            {submissionsError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700">
                {submissionsError}
              </div>
            )}

            {isSubmissionsLoading ? (
              <div className="py-12 text-center text-slate-400">Loading student submissions...</div>
            ) : submissionsList.length === 0 ? (
              <div className="p-8 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-slate-500">
                No student submissions received for this assignment yet.
              </div>
            ) : (
              <div className="divide-y divide-slate-100 border border-slate-200 rounded-2xl overflow-hidden max-h-96 overflow-y-auto">
                {submissionsList.map((sub) => (
                  <div key={sub.id} className="p-3.5 bg-white flex items-center justify-between gap-3 hover:bg-slate-50 transition-colors">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 font-mono">
                          {sub.student_registration_number || `Student #${sub.student_id || sub.student}`}
                        </span>
                        {sub.is_late && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200 font-bold">
                            LATE
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500 font-mono">
                        Submitted: {sub.submitted_at ? new Date(sub.submitted_at).toLocaleString() : "—"}
                      </p>
                      {sub.submission_text && (
                        <p className="text-[11px] text-slate-700 italic bg-slate-50 p-1.5 rounded-lg border border-slate-100 line-clamp-2">
                          &ldquo;{sub.submission_text}&rdquo;
                        </p>
                      )}
                    </div>

                    <div className="text-right shrink-0">
                      <div className="mb-1">
                        {sub.marks_obtained != null ? (
                          <span className="font-bold font-mono text-emerald-600 text-sm">
                            {sub.marks_obtained} / {viewSubmissionsAssignment.max_marks}
                          </span>
                        ) : (
                          <span className="text-[11px] text-amber-600 font-semibold bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                            Ungraded
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => {
                          setGradingSubmission(sub);
                          setGradeFormData({
                            marks_obtained: sub.marks_obtained != null ? String(sub.marks_obtained) : "",
                            feedback: sub.feedback || "",
                          });
                          setFormError("");
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer"
                      >
                        <Award className="w-3 h-3" />
                        <span>{sub.marks_obtained != null ? "Regrade" : "Grade"}</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setViewSubmissionsAssignment(null)}
                className="px-4 py-2 rounded-xl font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal: Grade Submission */}
      {gradingSubmission && (
        <Modal
          isOpen={Boolean(gradingSubmission)}
          onClose={() => setGradingSubmission(null)}
          title="Grade Student Submission"
          subtitle={`Student: ${
            gradingSubmission.student_registration_number || `Student #${gradingSubmission.student_id || gradingSubmission.student}`
          }`}
        >
          <form onSubmit={handleGradeSubmit} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-slate-700 font-semibold mb-1">
                Marks Obtained (Max: {viewSubmissionsAssignment?.max_marks} pts) *
              </label>
              <input
                type="number"
                step="0.5"
                min="0"
                max={viewSubmissionsAssignment?.max_marks || 100}
                required
                value={gradeFormData.marks_obtained}
                onChange={(e) => setGradeFormData({ ...gradeFormData, marks_obtained: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 font-mono"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Feedback / Evaluation Notes</label>
              <textarea
                rows={3}
                value={gradeFormData.feedback}
                onChange={(e) => setGradeFormData({ ...gradeFormData, feedback: e.target.value })}
                placeholder="Constructive feedback for the student..."
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setGradingSubmission(null)}
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
                <span>Save Grade</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Confirm: Delete Assignment */}
      <ConfirmDialog
        isOpen={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Assignment"
        message={`Are you sure you want to permanently delete assignment "${deleteTarget?.title}"? All existing submissions will be permanently removed.`}
        confirmText="Delete Assignment"
        isLoading={isSubmitting}
        variant="danger"
      />
    </div>
  );
};

export default FacultyAssignmentsPage;
