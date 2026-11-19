import React, { useState, useEffect } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import {
  studentAttendanceApi,
  studentCourseApi,
  formatApiError,
} from "@/services/studentService";
import {
  Calendar,
  CheckCircle2,
  XCircle,
  Clock,
  BookOpen,
  Percent,
  RefreshCw,
  AlertTriangle,
  UserCheck,
} from "lucide-react";

export const StudentAttendancePage = () => {
  const [enrollments, setEnrollments] = useState([]);
  const [selectedOfferingFilter, setSelectedOfferingFilter] = useState("all");
  const [summaryData, setSummaryData] = useState(null);
  const [historyRecords, setHistoryRecords] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [enrollmentList, summary, history] = await Promise.all([
        studentCourseApi.getMyEnrollments().catch(() => []),
        studentAttendanceApi.getMySummary(),
        studentAttendanceApi.getMyHistory(
          selectedOfferingFilter !== "all" ? { offering_id: selectedOfferingFilter } : {}
        ),
      ]);
      setEnrollments(enrollmentList || []);
      setSummaryData(summary);
      setHistoryRecords(history || []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedOfferingFilter]);

  const summaries = Array.isArray(summaryData) ? summaryData : (summaryData ? [summaryData] : []);
  const totalSessionsCount = summaries.reduce((acc, curr) => acc + (curr.total_sessions || 0), 0) || historyRecords.length;
  const totalAttendedCount = summaries.reduce((acc, curr) => acc + (curr.attended_count ?? ((curr.present_count || 0) + (curr.late_count || 0))), 0) || historyRecords.filter(r => r.status === "PRESENT" || r.status === "LATE").length;
  const totalPresentCount = summaries.reduce((acc, curr) => acc + (curr.present_count || 0), 0) || historyRecords.filter(r => r.status === "PRESENT").length;
  const totalAbsentCount = summaries.reduce((acc, curr) => acc + (curr.absent_count || 0), 0) || historyRecords.filter(r => r.status === "ABSENT").length;

  const hasSessions = totalSessionsCount > 0;
  const overallPercentage = hasSessions ? Math.round((totalAttendedCount / totalSessionsCount) * 100) : null;
  const isBelowThreshold = hasSessions && overallPercentage < 75;

  const columns = [
    {
      header: "Session Date",
      accessor: (row) => (
        <div>
          <span className="font-bold text-slate-900 font-mono text-xs block">
            {row.session_date || row.date || (row.session?.date ?? "—")}
          </span>
          <span className="text-[11px] text-slate-400 font-mono">
            {row.start_time && row.end_time ? `${row.start_time} - ${row.end_time}` : (row.session?.start_time ? `${row.session.start_time} - ${row.session.end_time}` : "")}
          </span>
        </div>
      ),
      className: "w-36",
    },
    {
      header: "Course & Topic",
      accessor: (row) => {
        const enr = enrollments.find(e => (e.course_offering_id || e.id) === (row.course_offering_id || row.course_offering) || (e.course_offering && e.course_offering.id === (row.course_offering_id || row.course_offering)));
        const courseTitle = enr?.course_name || enr?.course_offering?.course_name || enr?.course_id || row.course_code || row.course_offering_code || `Course Offering #${row.course_offering_id || row.course_offering || ""}`;
        return (
          <div>
            <span className="font-semibold text-slate-800 text-xs block">
              {courseTitle}
            </span>
            <span className="text-[11px] text-slate-500 line-clamp-1">
              {row.session_title || row.title || row.session?.topic || row.topic || "Regular Classroom Lecture"}
            </span>
          </div>
        );
      },
    },
    {
      header: "Attendance Status",
      accessor: (row) => {
        const colors = {
          PRESENT: "bg-emerald-50 text-emerald-700 border-emerald-200",
          LATE: "bg-amber-50 text-amber-700 border-amber-200",
          ABSENT: "bg-rose-50 text-rose-700 border-rose-200",
          EXCUSED: "bg-indigo-50 text-indigo-700 border-indigo-200",
        };
        return (
          <span
            className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider border ${
              colors[row.status] || "bg-slate-100 text-slate-600 border-slate-200"
            }`}
          >
            {row.status}
          </span>
        );
      },
      className: "w-32",
    },
    {
      header: "Instructor Remarks",
      accessor: (row) => (
        <span className="text-xs text-slate-500 italic">
          {row.remarks || "—"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attendance Record"
        subtitle="Track classroom presence, session history, and minimum 75% university eligibility compliance."
        badge={hasSessions ? `${overallPercentage}% Overall Presence` : "No Sessions Recorded"}
        actions={
          <button
            onClick={fetchData}
            title="Refresh"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 shadow-xs transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        }
      />

      {/* High-level Attendance Status Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
              Overall Rate
            </span>
            <span
              className={`text-2xl font-extrabold font-mono mt-0.5 block ${
                !hasSessions ? "text-slate-400" : isBelowThreshold ? "text-rose-600" : "text-emerald-600"
              }`}
            >
              {hasSessions ? `${overallPercentage}%` : "No Records"}
            </span>
          </div>
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              !hasSessions ? "bg-slate-100 text-slate-400" : isBelowThreshold ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-600"
            }`}
          >
            <Percent className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
              Total Sessions
            </span>
            <span className="text-2xl font-extrabold font-mono text-slate-900 mt-0.5 block">
              {totalSessionsCount}
            </span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-600">
            <Calendar className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
              Present Count
            </span>
            <span className="text-2xl font-extrabold font-mono text-emerald-600 mt-0.5 block">
              {totalPresentCount}
            </span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
            <UserCheck className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
              Absences
            </span>
            <span className="text-2xl font-extrabold font-mono text-rose-600 mt-0.5 block">
              {totalAbsentCount}
            </span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-rose-50 flex items-center justify-center text-rose-600">
            <XCircle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Threshold Warning Banner if < 75% */}
      {isBelowThreshold && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block text-rose-800">
              Attendance Alert: Minimum 75% Requirement Not Met
            </span>
            <p className="text-rose-700 mt-0.5">
              Your overall attendance is currently {overallPercentage}%. University examination guidelines require a minimum of 75% attendance to qualify for final course evaluations.
            </p>
          </div>
        </div>
      )}

      {/* Filter by Course Offering */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
          <BookOpen className="w-4 h-4 text-indigo-600" />
          <span>Filter Session History by Course:</span>
        </div>
        <div className="w-full sm:w-80">
          <select
            value={selectedOfferingFilter}
            onChange={(e) => setSelectedOfferingFilter(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-slate-50"
          >
            <option value="all">All Enrolled Courses</option>
            {enrollments.map((enr) => {
              const off = enr.course_offering || {
                id: enr.course_offering_id || enr.id,
                course_id: enr.course_id,
                section: enr.section,
              };
              return (
                <option key={enr.id} value={off.id}>
                  {off.course_id} (Sec {off.section})
                </option>
              );
            })}
          </select>
        </div>
      </div>

      {errorMessage && (
        <ErrorState
          title="Attendance History Error"
          message={errorMessage}
          onRetry={fetchData}
        />
      )}

      {/* Detailed Session History Table */}
      <DataTable
        columns={columns}
        data={historyRecords}
        isLoading={isLoading}
        keyExtractor={(item) => item.id}
        emptyMessage="No attendance records found for your student profile."
      />
    </div>
  );
};

export default StudentAttendancePage;
