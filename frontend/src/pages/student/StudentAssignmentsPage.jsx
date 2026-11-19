import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import {
  studentCourseApi,
  studentAssignmentApi,
  formatApiError,
} from "@/services/studentService";
import {
  CheckSquare,
  BookOpen,
  Calendar,
  Clock,
  Award,
  Upload,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  FileCheck,
} from "lucide-react";

export const StudentAssignmentsPage = () => {
  const [enrollments, setEnrollments] = useState([]);
  const [selectedOfferingId, setSelectedOfferingId] = useState("");
  const [assignments, setAssignments] = useState([]);
  const [submissionsMap, setSubmissionsMap] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Modals
  const [submittingTarget, setSubmittingTarget] = useState(null);
  const [submissionText, setSubmissionText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const [viewingSubmission, setViewingSubmission] = useState(null);

  // Fetch Enrollments
  const fetchEnrollments = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await studentCourseApi.getMyEnrollments();
      setEnrollments(data || []);
      if (data?.length > 0 && !selectedOfferingId) {
        setSelectedOfferingId(String(data[0].course_offering_id || data[0].course_offering?.id || data[0].id));
      }
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEnrollments();
  }, []);

  // Fetch Assignments and Personal Submissions
  const fetchAssignments = async () => {
    if (!selectedOfferingId) {
      setAssignments([]);
      return;
    }
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await studentAssignmentApi.getAssignments(selectedOfferingId);
      const assignmentList = data || [];
      setAssignments(assignmentList);

      // Fetch personal submissions for each assignment
      const map = {};
      await Promise.all(
        assignmentList.map(async (a) => {
          try {
            const sub = await studentAssignmentApi.getMySubmission(a.id);
            if (sub) map[a.id] = sub;
          } catch {
            // No submission
          }
        })
      );
      setSubmissionsMap(map);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAssignments();
  }, [selectedOfferingId]);

  // Submit Assignment
  const handleSubmitWork = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!submissionText.trim()) {
      setFormError("Submission text or answer is required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await studentAssignmentApi.submitAssignment(submittingTarget.id, {
        submission_text: submissionText.trim(),
      });
      setSubmittingTarget(null);
      setSubmissionText("");
      setSuccessMessage(`Assignment "${submittingTarget.title}" submitted successfully.`);
      fetchAssignments();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      header: "Assignment Title & Instructions",
      accessor: (row) => (
        <div>
          <span className="font-bold text-slate-900 block text-xs">{row.title}</span>
          <p className="text-[11px] text-slate-500 line-clamp-2 mt-0.5">{row.description || "No specific instructions."}</p>
        </div>
      ),
    },
    {
      header: "Deadline",
      accessor: (row) => {
        const isPast = row.due_date && new Date(row.due_date) < new Date();
        return (
          <div className="text-xs font-mono">
            <span className={`block font-semibold ${isPast ? "text-rose-600" : "text-slate-800"}`}>
              {row.due_date ? new Date(row.due_date).toLocaleDateString() : "—"}
            </span>
            <span className="text-[10px] text-slate-400">
              {row.due_date ? new Date(row.due_date).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}
            </span>
          </div>
        );
      },
      className: "w-36",
    },
    {
      header: "Max Marks",
      accessor: (row) => (
        <div className="text-xs font-mono">
          <span className="font-bold text-slate-800">{row.max_marks ?? 100} pts</span>
          <span className="text-[10px] text-slate-400 block font-sans">Weight: {row.weightage ?? 10}%</span>
        </div>
      ),
      className: "w-28",
    },
    {
      header: "My Submission",
      accessor: (row) => {
        const sub = submissionsMap[row.id];
        if (!sub) {
          return (
            <span className="text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase bg-amber-50 text-amber-700 border border-amber-200">
              Not Submitted
            </span>
          );
        }
        if (sub.marks_obtained != null) {
          return (
            <div className="space-y-0.5">
              <span className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200 block w-max">
                Graded
              </span>
              <span className="text-xs font-mono font-bold text-emerald-600">
                {sub.marks_obtained} / {row.max_marks} pts
              </span>
            </div>
          );
        }
        return (
          <span className="text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase bg-indigo-50 text-indigo-700 border border-indigo-200">
            Submitted &bull; Pending
          </span>
        );
      },
      className: "w-36",
    },
    {
      header: "Action",
      accessor: (row) => {
        const sub = submissionsMap[row.id];
        if (sub) {
          return (
            <button
              onClick={() => setViewingSubmission({ assignment: row, submission: sub })}
              className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200 transition-colors cursor-pointer"
            >
              <FileCheck className="w-3.5 h-3.5" />
              <span>View</span>
            </button>
          );
        }
        return (
          <button
            onClick={() => {
              setSubmittingTarget(row);
              setSubmissionText("");
              setFormError("");
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Submit</span>
          </button>
        );
      },
      className: "w-28 text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Assignments & Quizzes"
        subtitle="View continuous assessment tasks, submit assignments, and inspect evaluation feedback."
        badge={`${assignments.length} Assignments`}
        actions={
          <button
            onClick={fetchAssignments}
            title="Refresh"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 shadow-xs transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        }
      />

      {/* Course Offering Selector */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
          <BookOpen className="w-4 h-4 text-indigo-600" />
          <span>Select Course Offering:</span>
        </div>
        <div className="w-full sm:w-80">
          <select
            value={selectedOfferingId}
            onChange={(e) => setSelectedOfferingId(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-slate-50"
          >
            {enrollments.length === 0 ? (
              <option value="">No enrolled courses</option>
            ) : (
              enrollments.map((enr) => {
                const off = enr.course_offering || {
                  id: enr.course_offering_id || enr.id,
                  course_id: enr.course_id,
                  section: enr.section,
                  academic_term_name: enr.term_name,
                };
                return (
                  <option key={enr.id} value={off.id}>
                    {off.course_id} (Sec {off.section}) &bull; {off.academic_term_name || "Current Term"}
                  </option>
                );
              })
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
        data={assignments}
        isLoading={isLoading}
        keyExtractor={(item) => item.id}
        emptyMessage="No active assignments for this course offering."
      />

      {/* Modal: Submit Assignment */}
      {submittingTarget && (
        <Modal
          isOpen={Boolean(submittingTarget)}
          onClose={() => setSubmittingTarget(null)}
          title={`Submit Assignment: ${submittingTarget.title}`}
          subtitle={`Max Marks: ${submittingTarget.max_marks} pts • Deadline: ${
            submittingTarget.due_date ? new Date(submittingTarget.due_date).toLocaleString() : "—"
          }`}
        >
          <form onSubmit={handleSubmitWork} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <div>
              <label className="block text-slate-700 font-semibold mb-1">
                Your Answer / Solution / Repository URL *
              </label>
              <textarea
                rows={6}
                required
                value={submissionText}
                onChange={(e) => setSubmissionText(e.target.value)}
                placeholder="Type your answer, solution code, or paste submission link here..."
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 font-mono text-xs"
              />
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setSubmittingTarget(null)}
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
                <span>Confirm & Submit</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: View Submission & Feedback */}
      {viewingSubmission && (
        <Modal
          isOpen={Boolean(viewingSubmission)}
          onClose={() => setViewingSubmission(null)}
          title={`My Submission: ${viewingSubmission.assignment.title}`}
          subtitle={`Submitted on: ${
            viewingSubmission.submission.submitted_at
              ? new Date(viewingSubmission.submission.submitted_at).toLocaleString()
              : "—"
          }`}
        >
          <div className="space-y-4 text-xs">
            {/* Grade summary banner if evaluated */}
            {viewingSubmission.submission.marks_obtained != null ? (
              <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold">Evaluation Score</span>
                  <span className="font-mono font-extrabold text-base text-emerald-700">
                    {viewingSubmission.submission.marks_obtained} / {viewingSubmission.assignment.max_marks} pts
                  </span>
                </div>
                {viewingSubmission.submission.feedback && (
                  <p className="text-xs text-emerald-800 italic pt-1 border-t border-emerald-200/50">
                    &ldquo;{viewingSubmission.submission.feedback}&rdquo;
                  </p>
                )}
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 flex items-center justify-between">
                <span>Evaluation Status</span>
                <span className="font-semibold text-amber-600">Pending Evaluation</span>
              </div>
            )}

            <div>
              <span className="font-bold text-slate-800 block mb-1">Submitted Response</span>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 whitespace-pre-wrap max-h-60 overflow-y-auto">
                {viewingSubmission.submission.submission_text || "No submission text available."}
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setViewingSubmission(null)}
                className="px-4 py-2 rounded-xl font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default StudentAssignmentsPage;
