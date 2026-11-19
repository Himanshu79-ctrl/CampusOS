import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { ErrorState } from "@/components/common/ErrorState";
import {
  reportsApi,
  termApi,
  departmentApi,
  courseApi,
  formatApiError,
} from "@/services/adminService";
import {
  BarChart3,
  Download,
  Users,
  Layers,
  CheckCircle2,
  Calendar,
  Building2,
  BookOpen,
  FileSpreadsheet,
  CheckSquare,
  Award,
  RefreshCw,
  Loader2,
  AlertCircle,
} from "lucide-react";

export const AdminReportsPage = () => {
  const [overview, setOverview] = useState(null);
  const [terms, setTerms] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [catalogCourses, setCatalogCourses] = useState([]);
  const [isExporting, setIsExporting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [exportMessage, setExportMessage] = useState("");

  // Filters
  const [selectedTermId, setSelectedTermId] = useState("");
  const [selectedDeptId, setSelectedDeptId] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [termList, deptList, courseList] = await Promise.all([
        termApi.getAll().catch(() => []),
        departmentApi.getAll().catch(() => []),
        courseApi.getAll().catch(() => []),
      ]);
      setTerms(termList || []);
      setDepartments(deptList || []);
      setCatalogCourses(courseList || []);

      const params = {};
      if (selectedTermId) params.term_id = selectedTermId;
      if (selectedDeptId) {
        const selectedDept = (deptList || []).find((d) => d._id === selectedDeptId || d.code === selectedDeptId);
        if (selectedDept) {
          params.department_id = `${selectedDept._id},${selectedDept.code}`;
        } else {
          params.department_id = selectedDeptId;
        }
      }

      const overviewData = await reportsApi.getOverview(params);
      setOverview(overviewData);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedTermId, selectedDeptId]);

  // Export Trigger
  const handleExport = async (type, format = "csv") => {
    setIsExporting(true);
    setExportMessage("");
    try {
      const filterParams = {};
      if (selectedTermId) filterParams.term_id = selectedTermId;
      if (selectedDeptId) {
        const selectedDept = departments.find((d) => d._id === selectedDeptId || d.code === selectedDeptId);
        if (selectedDept) {
          filterParams.department_id = `${selectedDept._id},${selectedDept.code}`;
        } else {
          filterParams.department_id = selectedDeptId;
        }
      }

      await reportsApi.exportData(type, format, filterParams);
      setExportMessage(`Export ${type} (${format.toUpperCase()}) downloaded successfully.`);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsExporting(false);
    }
  };

  const metrics = overview?.institution_metrics || {};
  const attendance = overview?.attendance_overview || {};
  const assignments = overview?.assignments_overview || {};
  const grades = overview?.grades_overview || {};

  return (
    <div className="space-y-6">
      <PageHeader
        title="Institutional Reports & Analytics"
        subtitle="Aggregate metrics, attendance compliance, student enrollments, and university-wide data exports."
        badge="LMS Reports & Analytics (SRS 3.16)"
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport("admin_overview", "csv")}
              disabled={isExporting}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
            >
              {isExporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              <span>Export CSV</span>
            </button>
            <button
              onClick={() => handleExport("admin_overview", "json")}
              disabled={isExporting}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Export JSON</span>
            </button>
          </div>
        }
      />

      {exportMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
          <span>{exportMessage}</span>
          <button onClick={() => setExportMessage("")} className="font-bold ml-4">
            &times;
          </button>
        </div>
      )}

      {errorMessage && (
        <ErrorState
          title="Reports Generation Notice"
          message={errorMessage}
          onRetry={fetchData}
        />
      )}

      {/* Filter Toolbar */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-2xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-slate-400" />
            <select
              value={selectedTermId}
              onChange={(e) => setSelectedTermId(e.target.value)}
              className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
            >
              <option value="">All Academic Terms (Active Default)</option>
              {terms.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.status})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-slate-400" />
            <select
              value={selectedDeptId}
              onChange={(e) => setSelectedDeptId(e.target.value)}
              className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 bg-white"
            >
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d._id} value={d._id}>
                  {d.code} - {d.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={fetchData}
          title="Refresh Reports"
          className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors self-end sm:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* High-Level Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="Active Students"
          value={metrics.active_students ?? 0}
          subtext={`Total enrolled: ${metrics.total_students ?? 0} students`}
          icon={Users}
          iconColor="text-blue-600"
          iconBg="bg-blue-50 border-blue-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Catalog Courses"
          value={catalogCourses.length}
          subtext="Master curriculum catalog"
          icon={BookOpen}
          iconColor="text-amber-600"
          iconBg="bg-amber-50 border-amber-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Course Offerings"
          value={metrics.published_course_offerings ?? 0}
          subtext={`Total offerings: ${metrics.total_course_offerings ?? 0}`}
          icon={Layers}
          iconColor="text-indigo-600"
          iconBg="bg-indigo-50 border-indigo-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Course Enrollments"
          value={metrics.active_enrollments ?? 0}
          subtext={`Total: ${metrics.total_enrollments ?? 0} (Dropped: ${metrics.dropped_enrollments ?? 0})`}
          icon={Award}
          iconColor="text-purple-600"
          iconBg="bg-purple-50 border-purple-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Attendance Compliance"
          value={
            attendance.total_records > 0
              ? `${attendance.overall_attendance_rate}%`
              : "No records"
          }
          subtext={
            attendance.total_records > 0
              ? `Present: ${attendance.present_count ?? 0} / ${attendance.total_records} sessions`
              : "No scheduled sessions recorded"
          }
          icon={CheckCircle2}
          iconColor="text-emerald-600"
          iconBg="bg-emerald-50 border-emerald-100"
          isLoading={isLoading}
        />
      </div>

      {catalogCourses.length > (metrics.total_course_offerings || 0) && (
        <div className="p-3.5 rounded-2xl bg-indigo-50/70 border border-indigo-100 flex items-start gap-3">
          <BookOpen className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <div className="text-xs text-indigo-950">
            <span className="font-semibold">Academic Architecture Note:</span> You have {catalogCourses.length} course(s) defined in the Master Catalog and {metrics.total_course_offerings || 0} scheduled Course Offering(s) for the current term filter. In CampusOS, courses created in the catalog must be scheduled as <Link to="/super-admin/offerings" className="font-bold underline text-indigo-700 hover:text-indigo-900">Course Offerings</Link> for a specific Academic Term to run live classes with student enrollments.
          </div>
        </div>
      )}

      {/* Two-Column Detail Grids: Attendance & Assignments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Attendance Breakdown */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Attendance Analytics
            </h3>
            <button
              onClick={() => handleExport("attendance", "csv")}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Export Attendance CSV
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Records</span>
              <span className="text-lg font-bold text-slate-800">{attendance.total_records ?? 0}</span>
            </div>
            <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-100">
              <span className="text-[10px] uppercase font-bold text-emerald-600 block">Present</span>
              <span className="text-lg font-bold text-emerald-800">{attendance.present_count ?? 0}</span>
            </div>
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-100">
              <span className="text-[10px] uppercase font-bold text-amber-600 block">Late</span>
              <span className="text-lg font-bold text-amber-800">{attendance.late_count ?? 0}</span>
            </div>
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-100">
              <span className="text-[10px] uppercase font-bold text-rose-600 block">Absent</span>
              <span className="text-lg font-bold text-rose-800">{attendance.absent_count ?? 0}</span>
            </div>
          </div>
        </div>

        {/* Assignments & Grading Analytics */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-indigo-600" />
              Assignments & Evaluations
            </h3>
            <span className="text-xs text-slate-400 font-mono">
              Finalized: {grades.finalized_course_grades ?? 0}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Assignments</span>
              <span className="text-lg font-bold text-slate-800">{assignments.total_assignments ?? 0}</span>
            </div>
            <div className="p-3 rounded-xl bg-blue-50 border border-blue-100">
              <span className="text-[10px] uppercase font-bold text-blue-600 block">Submissions</span>
              <span className="text-lg font-bold text-blue-800">{assignments.total_submissions ?? 0}</span>
            </div>
            <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-100">
              <span className="text-[10px] uppercase font-bold text-emerald-600 block">Graded</span>
              <span className="text-lg font-bold text-emerald-800">{assignments.graded_submissions ?? 0}</span>
            </div>
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-100">
              <span className="text-[10px] uppercase font-bold text-amber-600 block">Late</span>
              <span className="text-lg font-bold text-amber-800">{assignments.late_submissions ?? 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Available Export Catalog Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-3">
        <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
          <Download className="w-4 h-4 text-indigo-600" />
          University Data Export Registry
        </h3>
        <p className="text-xs text-slate-500">
          Export verified university reports in CSV or JSON format for administrative records, accreditation compliance, or institutional archives.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/70 flex items-center justify-between">
            <div>
              <span className="font-bold text-xs text-slate-800 block">Student Progress Summary</span>
              <span className="text-[11px] text-slate-500">Attendance, GPA & Demographics</span>
            </div>
            <button
              onClick={() => handleExport("admin_students", "csv")}
              className="p-1.5 rounded-lg text-slate-600 hover:text-indigo-600 hover:bg-slate-200 transition-colors"
              title="Download Student Progress CSV"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>

          <div className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/70 flex items-center justify-between">
            <div>
              <span className="font-bold text-xs text-slate-800 block">Institutional KPI Overview</span>
              <span className="text-[11px] text-slate-500">Term metrics & faculty capacity</span>
            </div>
            <button
              onClick={() => handleExport("admin_overview", "csv")}
              className="p-1.5 rounded-lg text-slate-600 hover:text-indigo-600 hover:bg-slate-200 transition-colors"
              title="Download Institutional KPI CSV"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>

          <div className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/70 flex items-center justify-between">
            <div>
              <span className="font-bold text-xs text-slate-800 block">Classroom Attendance Logs</span>
              <span className="text-[11px] text-slate-500">Detailed session-by-session records</span>
            </div>
            <button
              onClick={() => handleExport("attendance", "csv")}
              className="p-1.5 rounded-lg text-slate-600 hover:text-indigo-600 hover:bg-slate-200 transition-colors"
              title="Download Attendance CSV"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminReportsPage;
