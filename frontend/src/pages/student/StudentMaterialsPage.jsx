import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import {
  studentCourseApi,
  studentMaterialsApi,
  formatApiError,
} from "@/services/studentService";
import {
  FileText,
  BookOpen,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Clock,
  Link,
  RefreshCw,
  Video,
  FileCode,
  Check,
  Loader2,
} from "lucide-react";

export const StudentMaterialsPage = () => {
  const [enrollments, setEnrollments] = useState([]);
  const [selectedOfferingId, setSelectedOfferingId] = useState("");
  const [modules, setModules] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [expandedModules, setExpandedModules] = useState({});
  const [readingLesson, setReadingLesson] = useState(null);
  const [isMarkingProgress, setIsMarkingProgress] = useState(false);

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

  // Fetch Modules for selected course
  const fetchModules = async () => {
    if (!selectedOfferingId) {
      setModules([]);
      return;
    }
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await studentMaterialsApi.getModules(selectedOfferingId);
      setModules(data || []);
      if (data?.length > 0) {
        setExpandedModules((prev) => ({ ...prev, [data[0].id]: true }));
      }
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchModules();
  }, [selectedOfferingId]);

  const toggleExpand = (modId) => {
    setExpandedModules((prev) => ({ ...prev, [modId]: !prev[modId] }));
  };

  // Open Lesson Reader
  const handleOpenLesson = async (lesson) => {
    setReadingLesson(lesson);
    try {
      const detail = await studentMaterialsApi.getLessonDetail(lesson.id);
      setReadingLesson(detail);
    } catch {
      // Keep basic data if detail fails
    }
  };

  // Mark Lesson Progress
  const handleMarkCompleted = async () => {
    if (!readingLesson) return;
    setIsMarkingProgress(true);
    try {
      await studentMaterialsApi.markLessonProgress(readingLesson.id, "COMPLETED");
      setSuccessMessage(`Marked "${readingLesson.title}" as completed.`);
      fetchModules();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsMarkingProgress(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Course Materials & Content"
        subtitle="Access learning modules, study guides, interactive lessons, and lecture resources."
        badge={`${modules.length} Modules Available`}
        actions={
          <button
            onClick={fetchModules}
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
                const courseTitle =
                  enr.course_name ||
                  off.course_name ||
                  (off.course_id === "CS101"
                    ? "Introduction to Computer Science"
                    : off.course_id === "CS355"
                      ? "Operating Systems"
                      : off.course_id);
                return (
                  <option key={enr.id} value={off.id}>
                    {off.course_id} - {courseTitle} (Sec {off.section}) &bull; {off.academic_term_name || "Current Term"}
                  </option>
                );
              })
            )}
          </select>
        </div>
      </div>

      {/* Success Notice */}
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
          title="Materials Load Error"
          message={errorMessage}
          onRetry={fetchModules}
        />
      )}

      {/* Modules List View */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading course materials...</div>
      ) : modules.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-dashed border-slate-200 text-slate-500 text-xs">
          No learning materials published yet for this course.
        </div>
      ) : (
        <div className="space-y-4">
          {modules.map((mod, idx) => {
            const isExpanded = Boolean(expandedModules[mod.id]);
            const lessons = mod.lessons || [];
            const resources = mod.resources || [];
            return (
              <div
                key={mod.id}
                className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden"
              >
                {/* Module Bar */}
                <div
                  onClick={() => toggleExpand(mod.id)}
                  className="p-4 flex items-center justify-between gap-3 bg-slate-50/50 border-b border-slate-100 cursor-pointer hover:bg-slate-100/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="p-1 rounded-lg text-slate-400">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-indigo-600" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-400">
                          #{mod.order ?? idx + 1}
                        </span>
                        <h3 className="font-bold text-slate-900 text-sm">{mod.title}</h3>
                      </div>
                      {mod.description && (
                        <p className="text-xs text-slate-500 mt-0.5">{mod.description}</p>
                      )}
                    </div>
                  </div>

                  <span className="text-[11px] font-mono text-slate-500">
                    {lessons.length} Lessons &bull; {resources.length} Resources
                  </span>
                </div>

                {/* Expanded Lessons & Resources */}
                {isExpanded && (
                  <div className="p-4 space-y-4">
                    {/* Lessons */}
                    <div>
                      <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                        Lessons
                      </h4>
                      {lessons.length === 0 ? (
                        <p className="text-xs text-slate-400 italic">No published lessons in this module.</p>
                      ) : (
                        <div className="divide-y divide-slate-100 border border-slate-100 rounded-xl overflow-hidden">
                          {lessons.map((les) => (
                            <div
                              key={les.id}
                              onClick={() => handleOpenLesson(les)}
                              className="p-3.5 bg-white flex items-center justify-between gap-3 hover:bg-indigo-50/40 cursor-pointer transition-colors"
                            >
                              <div className="flex items-center gap-2.5">
                                <FileText className="w-4 h-4 text-indigo-500 shrink-0" />
                                <div>
                                  <span className="font-semibold text-slate-900 text-xs block">
                                    {les.title}
                                  </span>
                                  <span className="text-[10px] text-slate-400 font-mono">
                                    {les.lesson_type} &bull; {les.duration_minutes || 30} mins
                                  </span>
                                </div>
                              </div>
                              <span className="text-xs font-semibold text-indigo-600 hover:underline">
                                Read Lesson &rarr;
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Resources */}
                    {resources.length > 0 && (
                      <div>
                        <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                          Resources & Links
                        </h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {resources.map((res) => (
                            <div
                              key={res.id}
                              className="p-2.5 rounded-xl border border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs"
                            >
                              <div className="flex items-center gap-2 truncate">
                                <Link className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                                <span className="font-medium text-slate-700 truncate">{res.title}</span>
                              </div>
                              <a
                                href={res.url_or_path}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[10px] text-indigo-600 hover:underline shrink-0 ml-2"
                              >
                                Open &rarr;
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Lesson Reader */}
      {readingLesson && (
        <Modal
          isOpen={Boolean(readingLesson)}
          onClose={() => setReadingLesson(null)}
          title={readingLesson.title}
          subtitle={`Duration: ${readingLesson.duration_minutes || 30} mins • Type: ${readingLesson.lesson_type}`}
        >
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 max-h-96 overflow-y-auto">
              <h4 className="font-bold text-slate-800 text-sm border-b border-slate-200 pb-2">
                Lesson Content & Lecture Notes
              </h4>
              <div className="text-slate-700 whitespace-pre-wrap leading-relaxed text-xs">
                {readingLesson.content_text || (
                  <span className="text-slate-400 italic">No text content provided for this lesson.</span>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={handleMarkCompleted}
                disabled={isMarkingProgress}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors cursor-pointer"
              >
                {isMarkingProgress ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                )}
                <span>Mark as Completed</span>
              </button>
              <button
                type="button"
                onClick={() => setReadingLesson(null)}
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

export default StudentMaterialsPage;
