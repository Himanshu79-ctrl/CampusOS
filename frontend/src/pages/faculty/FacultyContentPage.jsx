import React, { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import {
  facultyCourseApi,
  facultyContentApi,
  formatApiError,
} from "@/services/facultyService";
import {
  FileText,
  Plus,
  Edit2,
  Trash2,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronRight,
  Video,
  FileCode,
  Link,
  BookOpen,
  Clock,
  Layers,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

export const FacultyContentPage = () => {
  const { user } = useAuth();
  const [offerings, setOfferings] = useState([]);
  const [selectedOfferingId, setSelectedOfferingId] = useState("");
  const [modules, setModules] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Expanded modules state
  const [expandedModules, setExpandedModules] = useState({});

  // Modals state
  const [isCreateModuleOpen, setIsCreateModuleOpen] = useState(false);
  const [editModule, setEditModule] = useState(null);
  const [deleteModuleTarget, setDeleteModuleTarget] = useState(null);

  // Lesson modal state
  const [activeModuleForLesson, setActiveModuleForLesson] = useState(null);
  const [editLesson, setEditLesson] = useState(null);
  const [deleteLessonTarget, setDeleteLessonTarget] = useState(null);

  // Resource modal state
  const [activeModuleForResource, setActiveModuleForResource] = useState(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Form states
  const [moduleFormData, setModuleFormData] = useState({
    title: "",
    description: "",
    order: 1,
    is_published: true,
  });

  const [lessonFormData, setLessonFormData] = useState({
    title: "",
    lesson_type: "ARTICLE",
    content_text: "",
    duration_minutes: 30,
    order: 1,
    is_published: true,
  });

  const [resourceFormData, setResourceFormData] = useState({
    title: "",
    resource_type: "URL",
    url_or_path: "",
  });

  // Fetch offerings
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

  // Fetch modules for selected offering
  const fetchModules = async () => {
    if (!selectedOfferingId) {
      setModules([]);
      return;
    }
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await facultyContentApi.getModules(selectedOfferingId);
      setModules(data || []);
      // Auto-expand first module
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

  const toggleExpand = (moduleId) => {
    setExpandedModules((prev) => ({
      ...prev,
      [moduleId]: !prev[moduleId],
    }));
  };

  // Module Actions
  const handleCreateModule = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!moduleFormData.title.trim()) {
      setFormError("Module title is required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyContentApi.createModule(selectedOfferingId, {
        title: moduleFormData.title.trim(),
        description: moduleFormData.description.trim(),
        order: Number(moduleFormData.order) || 1,
        is_published: moduleFormData.is_published,
      });
      setIsCreateModuleOpen(false);
      setModuleFormData({ title: "", description: "", order: 1, is_published: true });
      setSuccessMessage("Learning module created successfully.");
      fetchModules();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditModule = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!editModule.title.trim()) {
      setFormError("Module title is required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyContentApi.updateModule(editModule.id, {
        title: editModule.title.trim(),
        description: editModule.description?.trim() || "",
        order: Number(editModule.order) || 1,
        is_published: editModule.is_published,
      });
      setEditModule(null);
      setSuccessMessage("Learning module updated successfully.");
      fetchModules();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteModule = async () => {
    if (!deleteModuleTarget) return;
    setIsSubmitting(true);
    try {
      await facultyContentApi.deleteModule(deleteModuleTarget.id);
      setDeleteModuleTarget(null);
      setSuccessMessage("Learning module deleted successfully.");
      fetchModules();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleModulePublish = async (module) => {
    setIsSubmitting(true);
    try {
      await facultyContentApi.toggleModulePublish(module.id, !module.is_published);
      setSuccessMessage(`Module ${!module.is_published ? "published" : "unpublished"} successfully.`);
      fetchModules();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Lesson Actions
  const handleCreateLesson = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!lessonFormData.title.trim()) {
      setFormError("Lesson title is required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyContentApi.createLesson(activeModuleForLesson.id, {
        title: lessonFormData.title.trim(),
        content: lessonFormData.content_text.trim(),
        estimated_duration_minutes: Number(lessonFormData.duration_minutes) || 30,
        order: Number(lessonFormData.order) || 1,
        is_published: lessonFormData.is_published,
      });
      setActiveModuleForLesson(null);
      setLessonFormData({
        title: "",
        lesson_type: "ARTICLE",
        content_text: "",
        duration_minutes: 30,
        order: 1,
        is_published: true,
      });
      setSuccessMessage("Lesson added to module.");
      fetchModules();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteLesson = async () => {
    if (!deleteLessonTarget) return;
    setIsSubmitting(true);
    try {
      await facultyContentApi.deleteLesson(deleteLessonTarget.id);
      setDeleteLessonTarget(null);
      setSuccessMessage("Lesson deleted successfully.");
      fetchModules();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleLessonPublish = async (lesson) => {
    setIsSubmitting(true);
    try {
      await facultyContentApi.toggleLessonPublish(lesson.id, !lesson.is_published);
      setSuccessMessage(`Lesson ${!lesson.is_published ? "published" : "unpublished"}.`);
      fetchModules();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Resource Actions
  const handleCreateResource = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!resourceFormData.title.trim() || !resourceFormData.url_or_path.trim()) {
      setFormError("Resource title and URL or link are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyContentApi.createModuleResource(activeModuleForResource.id, {
        title: resourceFormData.title.trim(),
        resource_type: "LINK",
        external_url: resourceFormData.url_or_path.trim(),
      });
      setActiveModuleForResource(null);
      setResourceFormData({ title: "", resource_type: "URL", url_or_path: "" });
      setSuccessMessage("Resource added to module.");
      fetchModules();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Course Learning Content"
        subtitle="Organize course curricula, publish weekly modules, reading lessons, and educational resources."
        badge={`${modules.length} Modules`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchModules}
              title="Refresh"
              className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setModuleFormData({
                  title: "",
                  description: "",
                  order: modules.length + 1,
                  is_published: true,
                });
                setFormError("");
                setIsCreateModuleOpen(true);
              }}
              disabled={!selectedOfferingId}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>Create Module</span>
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
          title="Content Loading Error"
          message={errorMessage}
          onRetry={fetchModules}
        />
      )}

      {/* Modules List View */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading learning modules...</div>
      ) : modules.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-2xl border border-dashed border-slate-200 text-slate-500 text-xs">
          No learning modules published yet for this course offering. Click &ldquo;Create Module&rdquo; to start.
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
                className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden transition-all"
              >
                {/* Module Header Bar */}
                <div className="p-4 flex items-center justify-between gap-3 bg-slate-50/50 border-b border-slate-100">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => toggleExpand(mod.id)}
                      className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </button>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-400">
                          #{mod.order ?? idx + 1}
                        </span>
                        <h3 className="font-bold text-slate-900 text-sm">{mod.title}</h3>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider border ${
                            mod.is_published
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : "bg-slate-100 text-slate-500 border-slate-200"
                          }`}
                        >
                          {mod.is_published ? "Published" : "Draft"}
                        </span>
                      </div>
                      {mod.description && (
                        <p className="text-xs text-slate-500 mt-0.5">{mod.description}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggleModulePublish(mod)}
                      title={mod.is_published ? "Unpublish Module" : "Publish Module"}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
                    >
                      {mod.is_published ? (
                        <CheckCircle className="w-4 h-4 text-emerald-600" />
                      ) : (
                        <XCircle className="w-4 h-4 text-slate-400" />
                      )}
                    </button>
                    <button
                      onClick={() => {
                        setActiveModuleForLesson(mod);
                        setLessonFormData({
                          title: "",
                          lesson_type: "ARTICLE",
                          content_text: "",
                          duration_minutes: 30,
                          order: lessons.length + 1,
                          is_published: true,
                        });
                        setFormError("");
                      }}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Lesson</span>
                    </button>
                    <button
                      onClick={() => {
                        setActiveModuleForResource(mod);
                        setResourceFormData({ title: "", resource_type: "URL", url_or_path: "" });
                        setFormError("");
                      }}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Resource</span>
                    </button>
                    <button
                      onClick={() => {
                        setEditModule(mod);
                        setFormError("");
                      }}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setDeleteModuleTarget(mod)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Expanded Content: Lessons and Resources */}
                {isExpanded && (
                  <div className="p-4 space-y-4">
                    {/* Lessons list */}
                    <div>
                      <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                        Lessons ({lessons.length})
                      </h4>
                      {lessons.length === 0 ? (
                        <p className="text-xs text-slate-400 italic">No lessons added to this module yet.</p>
                      ) : (
                        <div className="divide-y divide-slate-100 border border-slate-100 rounded-xl overflow-hidden">
                          {lessons.map((les) => (
                            <div
                              key={les.id}
                              className="p-3 bg-white flex items-center justify-between text-xs hover:bg-slate-50 transition-colors"
                            >
                              <div className="flex items-center gap-2.5">
                                <FileText className="w-4 h-4 text-slate-400" />
                                <div>
                                  <span className="font-semibold text-slate-800">{les.title}</span>
                                  <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5 font-mono">
                                    <span>Type: {les.lesson_type}</span>
                                    <span>&bull;</span>
                                    <span>{les.duration_minutes || 30} mins</span>
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => handleToggleLessonPublish(les)}
                                  className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase border ${
                                    les.is_published
                                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                      : "bg-slate-100 text-slate-500 border-slate-200"
                                  }`}
                                >
                                  {les.is_published ? "Published" : "Draft"}
                                </button>
                                <button
                                  onClick={() => setDeleteLessonTarget(les)}
                                  className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Resources list */}
                    {resources.length > 0 && (
                      <div>
                        <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                          Resources & Links ({resources.length})
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

      {/* Modal: Create Module */}
      {isCreateModuleOpen && (
        <Modal
          isOpen={isCreateModuleOpen}
          onClose={() => setIsCreateModuleOpen(false)}
          title="Create Learning Module"
          subtitle="Add a new chapter or week-based curriculum module."
        >
          <form onSubmit={handleCreateModule} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Module Title *</label>
              <input
                type="text"
                required
                value={moduleFormData.title}
                onChange={(e) => setModuleFormData({ ...moduleFormData, title: e.target.value })}
                placeholder="e.g. Module 1: Introduction to Algorithms"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Description / Syllabus</label>
              <textarea
                rows={3}
                value={moduleFormData.description}
                onChange={(e) => setModuleFormData({ ...moduleFormData, description: e.target.value })}
                placeholder="Overview of topics and learning objectives covered in this module..."
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Sequence Order</label>
                <input
                  type="number"
                  min="1"
                  value={moduleFormData.order}
                  onChange={(e) => setModuleFormData({ ...moduleFormData, order: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
              <div className="flex items-center pt-5">
                <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={moduleFormData.is_published}
                    onChange={(e) =>
                      setModuleFormData({ ...moduleFormData, is_published: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Publish to Students</span>
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsCreateModuleOpen(false)}
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
                <span>Create Module</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: Edit Module */}
      {editModule && (
        <Modal
          isOpen={Boolean(editModule)}
          onClose={() => setEditModule(null)}
          title="Edit Learning Module"
          subtitle={`Editing: ${editModule.title}`}
        >
          <form onSubmit={handleEditModule} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Module Title *</label>
              <input
                type="text"
                required
                value={editModule.title}
                onChange={(e) => setEditModule({ ...editModule, title: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Description</label>
              <textarea
                rows={3}
                value={editModule.description || ""}
                onChange={(e) => setEditModule({ ...editModule, description: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Order</label>
                <input
                  type="number"
                  min="1"
                  value={editModule.order || 1}
                  onChange={(e) => setEditModule({ ...editModule, order: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
              <div className="flex items-center pt-5">
                <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={editModule.is_published}
                    onChange={(e) => setEditModule({ ...editModule, is_published: e.target.checked })}
                    className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Published</span>
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditModule(null)}
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

      {/* Modal: Create Lesson */}
      {activeModuleForLesson && (
        <Modal
          isOpen={Boolean(activeModuleForLesson)}
          onClose={() => setActiveModuleForLesson(null)}
          title="Add Lesson to Module"
          subtitle={`Adding to: ${activeModuleForLesson.title}`}
        >
          <form onSubmit={handleCreateLesson} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Lesson Title *</label>
              <input
                type="text"
                required
                value={lessonFormData.title}
                onChange={(e) => setLessonFormData({ ...lessonFormData, title: e.target.value })}
                placeholder="e.g. Asymptotic Notation & Big-O"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Lesson Type</label>
                <select
                  value={lessonFormData.lesson_type}
                  onChange={(e) => setLessonFormData({ ...lessonFormData, lesson_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  <option value="ARTICLE">Article / Notes</option>
                  <option value="VIDEO">Video Lecture</option>
                  <option value="DOCUMENT">Document / PDF</option>
                  <option value="QUIZ">Interactive Quiz</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Duration (mins)</label>
                <input
                  type="number"
                  min="5"
                  value={lessonFormData.duration_minutes}
                  onChange={(e) =>
                    setLessonFormData({ ...lessonFormData, duration_minutes: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Lesson Content / Notes</label>
              <textarea
                rows={4}
                value={lessonFormData.content_text}
                onChange={(e) => setLessonFormData({ ...lessonFormData, content_text: e.target.value })}
                placeholder="Markdown text, lecture notes, key takeaways..."
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setActiveModuleForLesson(null)}
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
                <span>Add Lesson</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: Add Resource */}
      {activeModuleForResource && (
        <Modal
          isOpen={Boolean(activeModuleForResource)}
          onClose={() => setActiveModuleForResource(null)}
          title="Add Learning Resource Link"
          subtitle={`Attaching to: ${activeModuleForResource.title}`}
        >
          <form onSubmit={handleCreateResource} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Resource Title *</label>
              <input
                type="text"
                required
                value={resourceFormData.title}
                onChange={(e) =>
                  setResourceFormData({ ...resourceFormData, title: e.target.value })
                }
                placeholder="e.g. Slides PDF / Reference Link"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">URL / Link *</label>
              <input
                type="url"
                required
                value={resourceFormData.url_or_path}
                onChange={(e) =>
                  setResourceFormData({ ...resourceFormData, url_or_path: e.target.value })
                }
                placeholder="https://..."
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 font-mono"
              />
            </div>
            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setActiveModuleForResource(null)}
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
                <span>Add Resource</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Confirm: Delete Module */}
      <ConfirmDialog
        isOpen={Boolean(deleteModuleTarget)}
        onClose={() => setDeleteModuleTarget(null)}
        onConfirm={handleDeleteModule}
        title="Delete Learning Module"
        message={`Are you sure you want to permanently delete module "${deleteModuleTarget?.title}"? All nested lessons and resources will be deleted.`}
        confirmText="Delete Module"
        isLoading={isSubmitting}
        variant="danger"
      />

      {/* Confirm: Delete Lesson */}
      <ConfirmDialog
        isOpen={Boolean(deleteLessonTarget)}
        onClose={() => setDeleteLessonTarget(null)}
        onConfirm={handleDeleteLesson}
        title="Delete Lesson"
        message={`Are you sure you want to delete lesson "${deleteLessonTarget?.title}"?`}
        confirmText="Delete Lesson"
        isLoading={isSubmitting}
        variant="danger"
      />
    </div>
  );
};

export default FacultyContentPage;
