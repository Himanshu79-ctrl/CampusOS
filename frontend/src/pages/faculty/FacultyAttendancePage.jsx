import React, { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { Modal } from "@/components/common/Modal";
import {
  facultyCourseApi,
  facultyAttendanceApi,
  formatApiError,
} from "@/services/facultyService";
import {
  Calendar,
  Plus,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  BookOpen,
  Users,
  Check,
  UserCheck,
  UserX,
  RefreshCw,
  Loader2,
  AlertCircle,
  BarChart3,
  Percent,
} from "lucide-react";

export const FacultyAttendancePage = () => {
  const { user } = useAuth();
  const [offerings, setOfferings] = useState([]);
  const [selectedOfferingId, setSelectedOfferingId] = useState("");
  const [sessions, setSessions] = useState([]);
  const [courseReport, setCourseReport] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [markingSession, setMarkingSession] = useState(null);
  const [rosterList, setRosterList] = useState([]);
  const [attendanceSheet, setAttendanceSheet] = useState({});
  const [isMarkingLoading, setIsMarkingLoading] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Create Session Form State
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split("T")[0],
    start_time: "09:00",
    end_time: "10:00",
    session_type: "REGULAR",
    topic: "",
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

  // Fetch Sessions and Report
  const fetchSessionsAndReport = async () => {
    if (!selectedOfferingId) {
      setSessions([]);
      setCourseReport(null);
      return;
    }
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [sessionList, report] = await Promise.all([
        facultyAttendanceApi.getSessions(selectedOfferingId),
        facultyAttendanceApi.getCourseReport(selectedOfferingId).catch(() => null),
      ]);
      setSessions(sessionList || []);
      setCourseReport(report);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessionsAndReport();
  }, [selectedOfferingId]);

  // Create Session
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.date || !formData.start_time || !formData.end_time) {
      setFormError("Date, Start Time, and End Time are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await facultyAttendanceApi.createSession(selectedOfferingId, {
        session_date: formData.date,
        date: formData.date,
        start_time: formData.start_time,
        end_time: formData.end_time,
        session_type: formData.session_type,
        title: formData.topic.trim() || "Regular Classroom Lecture",
        topic: formData.topic.trim(),
      });
      setIsCreateOpen(false);
      setFormData({
        date: new Date().toISOString().split("T")[0],
        start_time: "09:00",
        end_time: "10:00",
        session_type: "REGULAR",
        topic: "",
      });
      setSuccessMessage("Attendance session created successfully.");
      fetchSessionsAndReport();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open Marking Sheet
  const handleOpenMarking = async (session) => {
    setMarkingSession(session);
    setIsMarkingLoading(true);
    setFormError("");
    try {
      const [rosterRes, sessionDetail] = await Promise.all([
        facultyCourseApi.getRoster(selectedOfferingId),
        facultyAttendanceApi.getSessionDetail(session.id).catch(() => null),
      ]);

      const students = rosterRes?.students || [];
      setRosterList(students);

      // Pre-populate existing records
      const initialSheet = {};
      const existingRecords = sessionDetail?.records || [];
      const recordMap = {};
      existingRecords.forEach((r) => {
        recordMap[r.student] = r.status;
      });

      students.forEach((st) => {
        initialSheet[st.student_id] = recordMap[st.student_id] || "PRESENT";
      });
      setAttendanceSheet(initialSheet);
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsMarkingLoading(false);
    }
  };

  // Mark all present helper
  const handleMarkAll = (status) => {
    const updated = { ...attendanceSheet };
    rosterList.forEach((st) => {
      updated[st.student_id] = status;
    });
    setAttendanceSheet(updated);
  };

  // Save Attendance Records
  const handleSaveAttendance = async () => {
    setIsSubmitting(true);
    setFormError("");
    try {
      const records = Object.entries(attendanceSheet).map(([studentId, status]) => ({
        student_id: Number(studentId),
        status,
      }));
      await facultyAttendanceApi.markAttendance(markingSession.id, records);
      setMarkingSession(null);
      setSuccessMessage("Attendance sheet saved and synced successfully.");
      fetchSessionsAndReport();
    } catch (err) {
      setFormError(formatApiError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      header: "Session Date",
      accessor: (row) => (
        <div>
          <span className="font-bold text-slate-900 block font-mono text-xs">{row.session_date || row.date}</span>
          <span className="text-[11px] text-slate-500 font-mono">
            {row.start_time} - {row.end_time}
          </span>
        </div>
      ),
    },
    {
      header: "Topic / Type",
      accessor: (row) => (
        <div>
          <span className="font-semibold text-slate-800 text-xs block">
            {row.title || row.topic || "Regular Classroom Lecture"}
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono mt-0.5 inline-block">
            {row.session_type || "REGULAR"}
          </span>
        </div>
      ),
    },
    {
      header: "Marked Count",
      accessor: (row) => (
        <div className="text-xs font-mono">
          <span className="font-semibold text-slate-800">
            {row.records_count ?? (row.records?.length ?? "—")}
          </span>
          <span className="text-slate-400 text-[11px]"> students</span>
        </div>
      ),
      className: "w-32",
    },
    {
      header: "Actions",
      accessor: (row) => (
        <button
          onClick={() => handleOpenMarking(row)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer"
        >
          <UserCheck className="w-3.5 h-3.5" />
          <span>Mark Attendance</span>
        </button>
      ),
      className: "w-40 text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attendance Roster"
        subtitle="Schedule classroom sessions, mark student presence, and monitor attendance compliance."
        badge={`${sessions.length} Sessions`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchSessionsAndReport}
              title="Refresh"
              className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setFormData({
                  date: new Date().toISOString().split("T")[0],
                  start_time: "09:00",
                  end_time: "10:00",
                  session_type: "REGULAR",
                  topic: "",
                });
                setFormError("");
                setIsCreateOpen(true);
              }}
              disabled={!selectedOfferingId}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>Create Session</span>
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

      {/* Course Summary Stat Banner */}
      {courseReport && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-2xl bg-white border border-slate-200/80 shadow-xs">
            <span className="text-[11px] font-medium text-slate-500 block">Total Sessions</span>
            <span className="text-xl font-extrabold text-slate-900 font-mono mt-0.5 block">
              {courseReport.total_sessions ?? sessions.length}
            </span>
          </div>
          <div className="p-3.5 rounded-2xl bg-white border border-slate-200/80 shadow-xs">
            <span className="text-[11px] font-medium text-slate-500 block">Average Attendance</span>
            <span className="text-xl font-extrabold text-emerald-600 font-mono mt-0.5 block">
              {courseReport.average_attendance_rate != null
                ? `${courseReport.average_attendance_rate}%`
                : "—"}
            </span>
          </div>
          <div className="p-3.5 rounded-2xl bg-white border border-slate-200/80 shadow-xs">
            <span className="text-[11px] font-medium text-slate-500 block">Active Students</span>
            <span className="text-xl font-extrabold text-indigo-600 font-mono mt-0.5 block">
              {courseReport.enrolled_students ?? "—"}
            </span>
          </div>
          <div className="p-3.5 rounded-2xl bg-white border border-slate-200/80 shadow-xs">
            <span className="text-[11px] font-medium text-slate-500 block">Below 75% Threshold</span>
            <span className="text-xl font-extrabold text-amber-600 font-mono mt-0.5 block">
              {courseReport.low_attendance_students_count ?? 0}
            </span>
          </div>
        </div>
      )}

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
          title="Attendance Sessions Error"
          message={errorMessage}
          onRetry={fetchSessionsAndReport}
        />
      )}

      {/* Sessions Data Table */}
      <DataTable
        columns={columns}
        data={sessions}
        isLoading={isLoading}
        keyExtractor={(item) => item.id}
        emptyMessage="No attendance sessions created yet for this course offering."
      />

      {/* Modal: Create Session */}
      {isCreateOpen && (
        <Modal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          title="Create Attendance Session"
          subtitle="Initialize a lecture or lab session to mark student attendance."
        >
          <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Date *</label>
                <input
                  type="date"
                  required
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
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
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Session Type</label>
                <select
                  value={formData.session_type}
                  onChange={(e) => setFormData({ ...formData, session_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
                >
                  <option value="REGULAR">Regular Lecture</option>
                  <option value="LAB">Laboratory Session</option>
                  <option value="TUTORIAL">Tutorial / Review</option>
                  <option value="EXTRA">Extra / Makeup Class</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Lecture Topic / Notes</label>
                <input
                  type="text"
                  value={formData.topic}
                  onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
                  placeholder="e.g. Graph Algorithms & DFS"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                />
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
                <span>Create Session</span>
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: Mark Attendance Sheet */}
      {markingSession && (
        <Modal
          isOpen={Boolean(markingSession)}
          onClose={() => setMarkingSession(null)}
          title={`Attendance Sheet: ${markingSession.date}`}
          subtitle={`Time: ${markingSession.start_time} - ${markingSession.end_time} • ${markingSession.topic || markingSession.session_type}`}
        >
          <div className="space-y-4 text-xs">
            {formError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            {/* Quick Actions */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="font-semibold text-slate-700">
                Enrolled Students: <strong className="font-bold text-indigo-600">{rosterList.length}</strong>
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => handleMarkAll("PRESENT")}
                  className="px-2.5 py-1 rounded-lg text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 font-semibold cursor-pointer"
                >
                  All Present
                </button>
                <button
                  type="button"
                  onClick={() => handleMarkAll("ABSENT")}
                  className="px-2.5 py-1 rounded-lg text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 font-semibold cursor-pointer"
                >
                  All Absent
                </button>
              </div>
            </div>

            {/* Attendance Roster Checklist */}
            {isMarkingLoading ? (
              <div className="py-12 text-center text-slate-400">Loading roster sheet...</div>
            ) : rosterList.length === 0 ? (
              <div className="p-8 text-center text-slate-500 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
                No students enrolled in this course offering.
              </div>
            ) : (
              <div className="divide-y divide-slate-100 border border-slate-200 rounded-2xl overflow-hidden max-h-96 overflow-y-auto">
                {rosterList.map((st) => {
                  const currentStatus = attendanceSheet[st.student_id] || "PRESENT";
                  return (
                    <div
                      key={st.student_id}
                      className="p-3 bg-white flex items-center justify-between hover:bg-slate-50 transition-colors"
                    >
                      <div>
                        <span className="font-bold text-slate-900 font-mono text-sm block">
                          {st.registration_number || `Student #${st.student_id}`}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          Sem {st.current_semester || "—"} &bull; Adm {st.admission_year || "—"}
                        </span>
                      </div>

                      <div className="flex items-center gap-1">
                        {["PRESENT", "LATE", "ABSENT", "EXCUSED"].map((stat) => {
                          const isSelected = currentStatus === stat;
                          const styles = {
                            PRESENT: isSelected
                              ? "bg-emerald-600 text-white font-bold"
                              : "bg-slate-100 text-slate-600 hover:bg-emerald-50 hover:text-emerald-700",
                            LATE: isSelected
                              ? "bg-amber-600 text-white font-bold"
                              : "bg-slate-100 text-slate-600 hover:bg-amber-50 hover:text-amber-700",
                            ABSENT: isSelected
                              ? "bg-rose-600 text-white font-bold"
                              : "bg-slate-100 text-slate-600 hover:bg-rose-50 hover:text-rose-700",
                            EXCUSED: isSelected
                              ? "bg-indigo-600 text-white font-bold"
                              : "bg-slate-100 text-slate-600 hover:bg-indigo-50 hover:text-indigo-700",
                          };
                          return (
                            <button
                              key={stat}
                              type="button"
                              onClick={() =>
                                setAttendanceSheet({ ...attendanceSheet, [st.student_id]: stat })
                              }
                              className={`text-[10px] px-2 py-1 rounded-lg transition-colors cursor-pointer ${
                                styles[stat]
                              }`}
                            >
                              {stat}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setMarkingSession(null)}
                className="px-4 py-2 rounded-xl font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveAttendance}
                disabled={isSubmitting || rosterList.length === 0}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Save Attendance Sheet</span>
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default FacultyAttendancePage;
