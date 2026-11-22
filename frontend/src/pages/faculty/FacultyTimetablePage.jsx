import React, { useState, useEffect, useMemo } from "react";
import { useAuth } from "@/hooks/useAuth";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import {
  facultyCourseApi,
  facultyTimetableApi,
  formatApiError,
} from "@/services/facultyService";
import {
  Clock,
  Plus,
  Edit2,
  Trash2,
  MapPin,
  Building2,
  BookOpen,
  Calendar,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

const DAYS_OF_WEEK = [
  "MONDAY",
  "TUESDAY",
  "WEDNESDAY",
  "THURSDAY",
  "FRIDAY",
  "SATURDAY",
];

export const FacultyTimetablePage = () => {
  const { user } = useAuth();
  const [offerings, setOfferings] = useState([]);
  const [timetableEntries, setTimetableEntries] = useState([]);
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
    course_offering_id: "",
    day_of_week: "MONDAY",
    start_time: "09:00",
    end_time: "10:00",
    room: "",
    building: "Academic Block 1",
    entry_type: "LECTURE",
  });

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [offeringsList, entries] = await Promise.all([
        facultyCourseApi.getMyOfferings(user?.id || user?.user_id),
        facultyTimetableApi.getMyTimetable(),
      ]);
      setOfferings(offeringsList || []);
      setTimetableEntries(entries || []);
      if (offeringsList?.length > 0 && !formData.course_offering_id) {
        const activeOff = offeringsList.find(
          (o) => o.academic_term_status === "ACTIVE" || o.academic_term?.status === "ACTIVE"
        );
        setFormData((prev) => ({
          ...prev,
          course_offering_id: String(activeOff ? activeOff.id : offeringsList[0].id),
        }));
      }
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [user]);

  // Group timetable entries by day of week
  const entriesByDay = useMemo(() => {
    const map = {};
    DAYS_OF_WEEK.forEach((d) => (map[d] = []));
    timetableEntries.forEach((entry) => {
      const day = entry.day_of_week?.toUpperCase();
      if (map[day]) {
        map[day].push(entry);
      }
    });
    // Sort each day's entries by start time
    Object.keys(map).forEach((d) => {
      map[d].sort((a, b) => (a.start_time || "").localeCompare(b.start_time || ""));
    });
    return map;
  }, [timetableEntries]);

  // Handle Create Timetable Slot
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.course_offering_id || !formData.room.trim() || !formData.start_time || !formData.end_time) {
      setFormError("Course, room number, start time and end time are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyTimetableApi.createEntry(formData.course_offering_id, {
        day_of_week: formData.day_of_week,
        start_time: formData.start_time,
        end_time: formData.end_time,
        room: formData.room.trim(),
        building: formData.building.trim(),
        entry_type: formData.entry_type,
      });
      setIsCreateOpen(false);
      setFormData({
        course_offering_id: offerings[0]?.id ? String(offerings[0].id) : "",
        day_of_week: "MONDAY",
        start_time: "09:00",
        end_time: "10:00",
        room: "",
        building: "Academic Block 1",
        entry_type: "LECTURE",
      });
      setSuccessMessage("Timetable class slot scheduled successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Edit Slot
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!editTarget.room.trim() || !editTarget.start_time || !editTarget.end_time) {
      setFormError("Room, start time and end time are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyTimetableApi.updateEntry(editTarget.id, {
        day_of_week: editTarget.day_of_week,
        start_time: editTarget.start_time,
        end_time: editTarget.end_time,
        room: editTarget.room.trim(),
        building: editTarget.building?.trim() || "",
        entry_type: editTarget.entry_type,
      });
      setEditTarget(null);
      setSuccessMessage("Timetable class slot updated successfully.");
      fetchData();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Delete Slot
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsSubmitting(true);
    try {
      await facultyTimetableApi.deleteEntry(deleteTarget.id);
      setDeleteTarget(null);
      setSuccessMessage("Timetable class slot removed.");
      fetchData();
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Teaching Timetable"
        subtitle="Manage your weekly lecture schedule, assigned classrooms, and laboratory hours."
        badge={`${timetableEntries.length} Scheduled Slots`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchData}
              title="Refresh"
              className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setFormError("");
                setIsCreateOpen(true);
              }}
              disabled={offerings.length === 0}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>Schedule Class Slot</span>
            </button>
          </div>
        }
      />

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
          title="Timetable Error"
          message={errorMessage}
          onRetry={fetchData}
        />
      )}

      {/* Weekly Schedule Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading teaching timetable...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {DAYS_OF_WEEK.map((day) => {
            const slots = entriesByDay[day] || [];
            return (
              <div
                key={day}
                className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden flex flex-col"
              >
                {/* Day Header */}
                <div className="p-3.5 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                  <span className="font-bold text-slate-800 text-xs uppercase tracking-wider">
                    {day}
                  </span>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-600">
                    {slots.length} {slots.length === 1 ? "Class" : "Classes"}
                  </span>
                </div>

                {/* Day Slots */}
                <div className="p-3.5 space-y-2.5 flex-1">
                  {slots.length === 0 ? (
                    <p className="text-xs text-slate-400 italic py-6 text-center">No classes scheduled</p>
                  ) : (
                    slots.map((slot) => (
                      <div
                        key={slot.id}
                        className="p-3 rounded-xl border border-slate-200/70 bg-slate-50/50 hover:bg-slate-50 hover:border-indigo-200 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="font-bold text-slate-900 text-xs font-mono">
                              {slot.course_code || slot.course_id || `Offering #${slot.course_offering}`}
                            </span>
                            {slot.section && (
                              <span className="text-[10px] ml-1.5 px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 font-semibold">
                                Sec {slot.section}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => {
                                setEditTarget(slot);
                                setFormError("");
                              }}
                              className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded"
                            >
                              <Edit2 className="w-3 h-3" />
                            </button>
                            <button
                              onClick={() => setDeleteTarget(slot)}
                              className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>

                        <div className="flex items-center gap-1 text-[11px] text-indigo-700 font-mono mt-1">
                          <Clock className="w-3 h-3 text-indigo-500" />
                          <span>
                            {slot.start_time} &rarr; {slot.end_time}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-200/50">
                          <div className="flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-slate-400" />
                            <span>Room: {slot.room}</span>
                          </div>
                          <span className="text-[10px] uppercase font-bold text-slate-400">
                            {slot.entry_type}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Create Class Slot */}
      {isCreateOpen && (
        <Modal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          title="Schedule Class Slot"
          subtitle="Add a lecture, lab, or tutorial slot to your weekly schedule."
        >
          <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <div>
              <label className="block text-slate-700 font-semibold mb-1">Course Offering *</label>
              <select
                required
                value={formData.course_offering_id}
                onChange={(e) =>
                  setFormData({ ...formData, course_offering_id: e.target.value })
                }
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
              >
                {offerings.map((o) => {
                  const courseTitle = o.course_name && (o.course_code || o.course_id)
                    ? `${o.course_code || o.course_id} — ${o.course_name}`
                    : (o.course_code || o.course_id);
                  return (
                    <option key={o.id} value={o.id}>
                      {courseTitle} (Sec {o.section}) &bull; {o.academic_term_name || `Term #${o.academic_term}`}
                      {o.academic_term_status ? ` • ${o.academic_term_status}` : ""}
                    </option>
                  );
                })}
              </select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Day of Week *</label>
                <select
                  value={formData.day_of_week}
                  onChange={(e) => setFormData({ ...formData, day_of_week: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  {DAYS_OF_WEEK.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Start Time *</label>
                <input
                  type="time"
                  required
                  value={formData.start_time}
                  onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">End Time *</label>
                <input
                  type="time"
                  required
                  value={formData.end_time}
                  onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Room / Venue *</label>
                <input
                  type="text"
                  required
                  value={formData.room}
                  onChange={(e) => setFormData({ ...formData, room: e.target.value })}
                  placeholder="e.g. Room 402 / Lab B"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Building</label>
                <input
                  type="text"
                  value={formData.building}
                  onChange={(e) => setFormData({ ...formData, building: e.target.value })}
                  placeholder="e.g. Academic Block 1"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Session Type</label>
                <select
                  value={formData.entry_type}
                  onChange={(e) => setFormData({ ...formData, entry_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  <option value="LECTURE">Lecture</option>
                  <option value="LAB">Lab Practical</option>
                  <option value="TUTORIAL">Tutorial</option>
                  <option value="SEMINAR">Seminar</option>
                </select>
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
                <span>Save Class Slot</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: Edit Class Slot */}
      {editTarget && (
        <Modal
          isOpen={Boolean(editTarget)}
          onClose={() => setEditTarget(null)}
          title="Edit Class Slot"
          subtitle={`Editing: ${editTarget.course_code || editTarget.course_id || "Class Slot"}`}
        >
          <form onSubmit={handleEditSubmit} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Day of Week</label>
                <select
                  value={editTarget.day_of_week}
                  onChange={(e) => setEditTarget({ ...editTarget, day_of_week: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  {DAYS_OF_WEEK.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Start Time</label>
                <input
                  type="time"
                  required
                  value={editTarget.start_time}
                  onChange={(e) => setEditTarget({ ...editTarget, start_time: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">End Time</label>
                <input
                  type="time"
                  required
                  value={editTarget.end_time}
                  onChange={(e) => setEditTarget({ ...editTarget, end_time: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Room / Venue</label>
                <input
                  type="text"
                  required
                  value={editTarget.room}
                  onChange={(e) => setEditTarget({ ...editTarget, room: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Building</label>
                <input
                  type="text"
                  value={editTarget.building || ""}
                  onChange={(e) => setEditTarget({ ...editTarget, building: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Session Type</label>
                <select
                  value={editTarget.entry_type}
                  onChange={(e) => setEditTarget({ ...editTarget, entry_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  <option value="LECTURE">Lecture</option>
                  <option value="LAB">Lab Practical</option>
                  <option value="TUTORIAL">Tutorial</option>
                  <option value="SEMINAR">Seminar</option>
                </select>
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

      {/* Confirm: Delete Slot */}
      <ConfirmDialog
        isOpen={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteConfirm}
        title="Remove Class Slot"
        message={`Are you sure you want to remove the ${deleteTarget?.day_of_week} class slot (${deleteTarget?.start_time} - ${deleteTarget?.end_time})?`}
        confirmText="Remove Slot"
        isLoading={isSubmitting}
        variant="danger"
      />
    </div>
  );
};

export default FacultyTimetablePage;
