import React, { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import {
  facultyCourseApi,
  facultyGradebookApi,
  formatApiError,
} from "@/services/facultyService";
import {
  Award,
  Plus,
  Edit2,
  Trash2,
  BookOpen,
  CheckCircle,
  XCircle,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Layers,
  FileSpreadsheet,
  Users,
} from "lucide-react";

export const FacultyGradebookPage = () => {
  const { user } = useAuth();
  const [offerings, setOfferings] = useState([]);
  const [selectedOfferingId, setSelectedOfferingId] = useState("");
  const [gradeItems, setGradeItems] = useState([]);
  const [matrixData, setMatrixData] = useState(null);
  const [activeTab, setActiveTab] = useState("matrix"); // "matrix" | "items"
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Modals state
  const [isCreateItemOpen, setIsCreateItemOpen] = useState(false);
  const [markingItem, setMarkingItem] = useState(null);
  const [studentMarksSheet, setStudentMarksSheet] = useState([]);
  const [isMarkingLoading, setIsMarkingLoading] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Create Grade Item Form State
  const [itemFormData, setItemFormData] = useState({
    name: "",
    item_type: "ASSIGNMENT",
    max_marks: 100,
    weightage_percentage: 20,
    is_published: false,
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

  // Fetch Grade Items and Gradebook Matrix
  const fetchGradebookData = async () => {
    if (!selectedOfferingId) {
      setGradeItems([]);
      setMatrixData(null);
      return;
    }
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [items, matrix] = await Promise.all([
        facultyGradebookApi.getGradeItems(selectedOfferingId),
        facultyGradebookApi.getGradebookMatrix(selectedOfferingId).catch(() => null),
      ]);
      setGradeItems(items || []);
      setMatrixData(matrix);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGradebookData();
  }, [selectedOfferingId]);

  // Create Grade Item
  const handleCreateGradeItem = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!itemFormData.name.trim()) {
      setFormError("Assessment item name is required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyGradebookApi.createGradeItem(selectedOfferingId, {
        name: itemFormData.name.trim(),
        item_type: itemFormData.item_type,
        max_marks: Number(itemFormData.max_marks) || 100,
        weightage_percentage: Number(itemFormData.weightage_percentage) || 0,
        is_published: itemFormData.is_published,
      });
      setIsCreateItemOpen(false);
      setItemFormData({
        name: "",
        item_type: "ASSIGNMENT",
        max_marks: 100,
        weightage_percentage: 20,
        is_published: false,
      });
      setSuccessMessage("Assessment component added to gradebook.");
      fetchGradebookData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Toggle Publish Item
  const handleTogglePublishItem = async (item) => {
    setIsSubmitting(true);
    try {
      await facultyGradebookApi.togglePublishItem(item.id, !item.is_published);
      setSuccessMessage(`Assessment item ${!item.is_published ? "published" : "unpublished"}.`);
      fetchGradebookData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open Enter Marks Sheet for an Item
  const handleOpenEnterMarks = async (item) => {
    setMarkingItem(item);
    setIsMarkingLoading(true);
    setFormError("");
    try {
      const rosterRes = await facultyCourseApi.getRoster(selectedOfferingId);
      const students = rosterRes?.students || [];

      // Look up existing scores from matrix data if available
      const existingMap = {};
      if (matrixData?.records) {
        matrixData.records
          .filter((r) => r.grade_item === item.id)
          .forEach((r) => {
            existingMap[r.student] = r.marks_obtained;
          });
      }

      const sheet = students.map((st) => ({
        student_id: st.student_id,
        registration_number: st.registration_number || `Student #${st.student_id}`,
        marks_obtained: existingMap[st.student_id] != null ? String(existingMap[st.student_id]) : "",
        letter_grade: "",
        feedback: "",
      }));
      setStudentMarksSheet(sheet);
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsMarkingLoading(false);
    }
  };

  // Save Bulk Marks
  const handleSaveMarks = async () => {
    setIsSubmitting(true);
    setFormError("");
    try {
      const recordsToSave = studentMarksSheet
        .filter((row) => row.marks_obtained !== "")
        .map((row) => ({
          student_id: row.student_id,
          marks_obtained: Number(row.marks_obtained),
          letter_grade: row.letter_grade.trim(),
          feedback: row.feedback.trim(),
        }));

      await facultyGradebookApi.bulkEnterMarks(markingItem.id, recordsToSave);
      setMarkingItem(null);
      setSuccessMessage("Assessment marks updated successfully.");
      fetchGradebookData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Sync Assignment Grades
  const handleSyncAssignment = async (item) => {
    setIsSubmitting(true);
    try {
      const res = await facultyGradebookApi.syncAssignmentGrades(item.id);
      setSuccessMessage(res.message || "Assignment marks synced into grade records.");
      fetchGradebookData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Gradebook & Final Grades"
        subtitle="Manage course assessment components, score criteria, grading matrices, and student performance."
        badge={`${gradeItems.length} Components`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchGradebookData}
              title="Refresh"
              className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setFormError("");
                setIsCreateItemOpen(true);
              }}
              disabled={!selectedOfferingId}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>Add Assessment Component</span>
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

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200">
        <button
          onClick={() => setActiveTab("matrix")}
          className={`pb-2.5 px-3 text-xs font-bold transition-colors cursor-pointer flex items-center gap-1.5 ${
            activeTab === "matrix"
              ? "text-indigo-600 border-b-2 border-indigo-600"
              : "text-slate-500 hover:text-slate-800"
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          <span>Gradebook Matrix</span>
        </button>
        <button
          onClick={() => setActiveTab("items")}
          className={`pb-2.5 px-3 text-xs font-bold transition-colors cursor-pointer flex items-center gap-1.5 ${
            activeTab === "items"
              ? "text-indigo-600 border-b-2 border-indigo-600"
              : "text-slate-500 hover:text-slate-800"
          }`}
        >
          <Award className="w-4 h-4" />
          <span>Assessment Components ({gradeItems.length})</span>
        </button>
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
          title="Gradebook Error"
          message={errorMessage}
          onRetry={fetchGradebookData}
        />
      )}

      {/* TAB 1: Gradebook Matrix */}
      {activeTab === "matrix" && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-xs text-slate-400">Loading gradebook matrix...</div>
          ) : !matrixData?.students || matrixData.students.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-500">
              No students enrolled or no assessment components configured for this offering.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                    <th className="p-3.5 pl-4 sticky left-0 bg-slate-50 z-10">Student</th>
                    {matrixData.grade_items?.map((item) => (
                      <th key={item.id} className="p-3.5 text-center min-w-28">
                        <span className="block text-slate-800 font-bold">{item.name}</span>
                        <span className="text-[10px] text-slate-400 font-normal">
                          Max: {item.max_marks} pts ({item.weightage_percentage}%)
                        </span>
                      </th>
                    ))}
                    <th className="p-3.5 pr-4 text-center min-w-24 font-bold text-indigo-700">
                      Total %
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {matrixData.students.map((st) => {
                    const studentRecords = matrixData.records?.filter((r) => r.student === st.id) || [];
                    const recordByItem = {};
                    studentRecords.forEach((r) => {
                      recordByItem[r.grade_item] = r.marks_obtained;
                    });

                    return (
                      <tr key={st.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="p-3.5 pl-4 sticky left-0 bg-white z-10 border-r border-slate-100">
                          <span className="font-bold text-slate-900 font-mono text-xs block">
                            {st.registration_number || `Student #${st.id}`}
                          </span>
                        </td>
                        {matrixData.grade_items?.map((item) => {
                          const marks = recordByItem[item.id];
                          return (
                            <td key={item.id} className="p-3.5 text-center font-mono">
                              {marks != null ? (
                                <span className="font-semibold text-slate-800">{marks}</span>
                              ) : (
                                <span className="text-slate-300">—</span>
                              )}
                            </td>
                          );
                        })}
                        <td className="p-3.5 pr-4 text-center font-mono font-bold text-indigo-600">
                          {st.total_weighted_percentage != null
                            ? `${st.total_weighted_percentage}%`
                            : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Assessment Components List */}
      {activeTab === "items" && (
        <div className="space-y-3">
          {isLoading ? (
            <div className="p-12 text-center text-xs text-slate-400">Loading components...</div>
          ) : gradeItems.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-2xl border border-dashed border-slate-200 text-xs text-slate-500">
              No assessment components created yet. Click &ldquo;Add Assessment Component&rdquo; to start.
            </div>
          ) : (
            gradeItems.map((item) => (
              <div
                key={item.id}
                className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs flex items-center justify-between gap-4"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm">{item.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded font-mono font-semibold bg-slate-100 text-slate-700">
                      {item.item_type}
                    </span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider border ${
                        item.is_published
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : "bg-slate-100 text-slate-500 border-slate-200"
                      }`}
                    >
                      {item.is_published ? "Published" : "Draft"}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-500 font-mono mt-1">
                    <span>Max Marks: <strong className="text-slate-800">{item.max_marks} pts</strong></span>
                    <span>&bull;</span>
                    <span>Weightage: <strong className="text-slate-800">{item.weightage_percentage}%</strong></span>
                    {item.assignment && (
                      <>
                        <span>&bull;</span>
                        <span className="text-indigo-600">Linked to LMS Assignment</span>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {item.assignment && (
                    <button
                      onClick={() => handleSyncAssignment(item)}
                      title="Sync submission grades from Assignment"
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Sync Assignment</span>
                    </button>
                  )}

                  <button
                    onClick={() => handleOpenEnterMarks(item)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                    <span>Enter Marks</span>
                  </button>

                  <button
                    onClick={() => handleTogglePublishItem(item)}
                    title={item.is_published ? "Unpublish Marks" : "Publish Marks to Students"}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
                  >
                    {item.is_published ? (
                      <CheckCircle className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-slate-400" />
                    )}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Modal: Create Assessment Item */}
      {isCreateItemOpen && (
        <Modal
          isOpen={isCreateItemOpen}
          onClose={() => setIsCreateItemOpen(false)}
          title="Add Assessment Component"
          subtitle="Define a grade item (Quiz, Midterm, Project, Final Exam) for this course offering."
        >
          <form onSubmit={handleCreateGradeItem} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Component Name *</label>
              <input
                type="text"
                required
                value={itemFormData.name}
                onChange={(e) => setItemFormData({ ...itemFormData, name: e.target.value })}
                placeholder="e.g. Midterm Examination / Quiz 1"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Type</label>
                <select
                  value={itemFormData.item_type}
                  onChange={(e) => setItemFormData({ ...itemFormData, item_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  <option value="ASSIGNMENT">Assignment</option>
                  <option value="QUIZ">Quiz / Test</option>
                  <option value="MIDTERM">Midterm Exam</option>
                  <option value="FINAL">Final Exam</option>
                  <option value="PROJECT">Project / Lab</option>
                  <option value="PARTICIPATION">Class Participation</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Max Marks (pts) *</label>
                <input
                  type="number"
                  min="1"
                  required
                  value={itemFormData.max_marks}
                  onChange={(e) => setItemFormData({ ...itemFormData, max_marks: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 font-mono"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Weightage (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={itemFormData.weightage_percentage}
                  onChange={(e) =>
                    setItemFormData({ ...itemFormData, weightage_percentage: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 font-mono"
                />
              </div>
            </div>
            <div>
              <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700 pt-2">
                <input
                  type="checkbox"
                  checked={itemFormData.is_published}
                  onChange={(e) =>
                    setItemFormData({ ...itemFormData, is_published: e.target.checked })
                  }
                  className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <span>Publish marks to enrolled students immediately</span>
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsCreateItemOpen(false)}
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
                <span>Add Component</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: Enter Marks Sheet */}
      {markingItem && (
        <Modal
          isOpen={Boolean(markingItem)}
          onClose={() => setMarkingItem(null)}
          title={`Enter Marks: ${markingItem.name}`}
          subtitle={`Max Marks: ${markingItem.max_marks} pts • Weightage: ${markingItem.weightage_percentage}%`}
        >
          <div className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            {isMarkingLoading ? (
              <div className="py-12 text-center text-slate-400">Loading student grading sheet...</div>
            ) : studentMarksSheet.length === 0 ? (
              <div className="p-8 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-slate-500">
                No students enrolled in this course offering.
              </div>
            ) : (
              <div className="border border-slate-200 rounded-2xl overflow-hidden max-h-96 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[11px]">
                    <tr>
                      <th className="p-3 pl-4">Student</th>
                      <th className="p-3 w-32">Marks (/{markingItem.max_marks})</th>
                      <th className="p-3 w-24">Letter</th>
                      <th className="p-3 pr-4">Feedback</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {studentMarksSheet.map((row, idx) => (
                      <tr key={row.student_id} className="hover:bg-slate-50/60">
                        <td className="p-3 pl-4 font-mono font-bold text-slate-800">
                          {row.registration_number}
                        </td>
                        <td className="p-3">
                          <input
                            type="number"
                            step="0.5"
                            min="0"
                            max={markingItem.max_marks}
                            value={row.marks_obtained}
                            onChange={(e) => {
                              const val = e.target.value;
                              const updated = [...studentMarksSheet];
                              updated[idx].marks_obtained = val;
                              setStudentMarksSheet(updated);
                            }}
                            placeholder="0.0"
                            className="w-24 px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-900 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-indigo-600"
                          />
                        </td>
                        <td className="p-3">
                          <input
                            type="text"
                            maxLength="3"
                            value={row.letter_grade}
                            onChange={(e) => {
                              const val = e.target.value.toUpperCase();
                              const updated = [...studentMarksSheet];
                              updated[idx].letter_grade = val;
                              setStudentMarksSheet(updated);
                            }}
                            placeholder="A"
                            className="w-16 px-2 py-1.5 rounded-lg border border-slate-200 text-slate-900 font-mono text-xs uppercase focus:outline-none focus:ring-2 focus:ring-indigo-600 text-center"
                          />
                        </td>
                        <td className="p-3 pr-4">
                          <input
                            type="text"
                            value={row.feedback}
                            onChange={(e) => {
                              const val = e.target.value;
                              const updated = [...studentMarksSheet];
                              updated[idx].feedback = val;
                              setStudentMarksSheet(updated);
                            }}
                            placeholder="Remarks..."
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-900 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-600"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setMarkingItem(null)}
                className="px-4 py-2 rounded-xl font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveMarks}
                disabled={isSubmitting || studentMarksSheet.length === 0}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Save Marks</span>
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default FacultyGradebookPage;
