import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import {
  reportsApi,
  departmentApi,
  facultyApi,
  courseApi,
  termApi,
  announcementsApi,
  formatApiError,
} from "@/services/adminService";
import {
  Users,
  GraduationCap,
  Building2,
  BookOpen,
  Layers,
  Calendar,
  Award,
  CheckCircle2,
  BarChart3,
  Megaphone,
  ArrowRight,
  Plus,
  Clock,
  RefreshCw,
  AlertCircle,
  ShieldCheck,
  Check,
} from "lucide-react";

export const SuperAdminDashboard = () => {
  const { user } = useAuth();
  const [overviewData, setOverviewData] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [facultyList, setFacultyList] = useState([]);
  const [courses, setCourses] = useState([]);
  const [terms, setTerms] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const fetchDashboardData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const [
        overviewRes,
        deptRes,
        facRes,
        courseRes,
        termRes,
        announceRes,
      ] = await Promise.all([
        reportsApi.getOverview().catch(() => null),
        departmentApi.getAll().catch(() => []),
        facultyApi.getAll().catch(() => []),
        courseApi.getAll().catch(() => []),
        termApi.getAll().catch(() => []),
        announcementsApi.getAll().catch(() => []),
      ]);

      setOverviewData(overviewRes);
      setDepartments(Array.isArray(deptRes) ? deptRes : []);
      setFacultyList(Array.isArray(facRes) ? facRes : []);
      setCourses(Array.isArray(courseRes) ? courseRes : []);
      setTerms(Array.isArray(termRes) ? termRes : []);
      setAnnouncements(Array.isArray(announceRes) ? announceRes : []);
    } catch (err) {
      setErrorMessage(formatApiError(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const displayName = user?.first_name
    ? `${user.first_name} ${user.last_name || ""}`.trim()
    : user?.username || "Super Administrator";

  const metrics = overviewData?.institution_metrics || {};
  const attendance = overviewData?.attendance_overview || {};
  const activeTerm = terms.find((t) => t.status === "ACTIVE") || null;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title={`Academic Governance Console — Welcome, ${displayName}`}
        subtitle="Institution-wide academic operations, faculty directory, student catalog, and term governance."
        badge="Super Admin"
        badgeClasses="bg-indigo-50 text-indigo-800 border-indigo-200"
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchDashboardData}
              title="Refresh Dashboard"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 shadow-2xs transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
            <Link
              to="/super-admin/reports"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-2xs transition-colors"
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Full Analytics</span>
            </Link>
          </div>
        }
      />

      {/* Error State Notice */}
      {errorMessage && (
        <ErrorState
          title="Data Synchronization Notice"
          message={errorMessage}
          onRetry={fetchDashboardData}
        />
      )}

      {/* Primary Academic KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Students"
          value={metrics.total_students ?? 0}
          subtext={`Active: ${metrics.active_students ?? 0} enrolled`}
          icon={Users}
          iconColor="text-blue-600"
          iconBg="bg-blue-50 border-blue-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Faculty Members"
          value={facultyList.length}
          subtext={`Active Instructors: ${metrics.active_faculty_count ?? 0}`}
          icon={GraduationCap}
          iconColor="text-emerald-600"
          iconBg="bg-emerald-50 border-emerald-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Academic Departments"
          value={departments.length}
          subtext="Institutional disciplines"
          icon={Building2}
          iconColor="text-purple-600"
          iconBg="bg-purple-50 border-purple-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Master Course Catalog"
          value={courses.length}
          subtext="Accredited catalog courses"
          icon={BookOpen}
          iconColor="text-amber-600"
          iconBg="bg-amber-50 border-amber-100"
          isLoading={isLoading}
        />
      </div>

      {/* Secondary Term & Academic Performance Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Course Offerings"
          value={metrics.published_course_offerings ?? 0}
          subtext={`Total Scheduled: ${metrics.total_course_offerings ?? 0}`}
          icon={Layers}
          iconColor="text-indigo-600"
          iconBg="bg-indigo-50 border-indigo-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Current Academic Term"
          value={activeTerm ? activeTerm.name : "None Active"}
          subtext={
            activeTerm
              ? `${activeTerm.academic_year} • Term ${activeTerm.term_number}`
              : "Set term status to Active in Terms"
          }
          icon={Calendar}
          iconColor="text-sky-600"
          iconBg="bg-sky-50 border-sky-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Course Enrollments"
          value={metrics.active_enrollments ?? 0}
          subtext={`Total: ${metrics.total_enrollments ?? 0} (Dropped: ${metrics.dropped_enrollments ?? 0})`}
          icon={Award}
          iconColor="text-violet-600"
          iconBg="bg-violet-50 border-violet-100"
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
              ? `Present: ${attendance.present_count ?? 0} / ${attendance.total_records} records`
              : "No attendance sessions recorded"
          }
          icon={CheckCircle2}
          iconColor="text-teal-600"
          iconBg="bg-teal-50 border-teal-100"
          isLoading={isLoading}
        />
      </div>

      {/* Quick Actions Bar */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
            <Plus className="w-4 h-4 text-indigo-600" />
            Quick Academic Actions
          </h2>
          <span className="text-[11px] text-slate-500 font-medium">
            Administrative Shortcuts
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <Link
            to="/super-admin/students"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100 transition-all flex flex-col items-start gap-2 group"
          >
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100 group-hover:scale-105 transition-transform">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-slate-800 block group-hover:text-indigo-600 transition-colors">
                Students
              </span>
              <span className="text-[10px] text-slate-500">Provision profiles</span>
            </div>
          </Link>

          <Link
            to="/super-admin/faculty"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100 transition-all flex flex-col items-start gap-2 group"
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 border border-emerald-100 group-hover:scale-105 transition-transform">
              <GraduationCap className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-slate-800 block group-hover:text-indigo-600 transition-colors">
                Faculty
              </span>
              <span className="text-[10px] text-slate-500">Staff directory</span>
            </div>
          </Link>

          <Link
            to="/super-admin/departments"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100 transition-all flex flex-col items-start gap-2 group"
          >
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center shrink-0 border border-purple-100 group-hover:scale-105 transition-transform">
              <Building2 className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-slate-800 block group-hover:text-indigo-600 transition-colors">
                Departments
              </span>
              <span className="text-[10px] text-slate-500">Disciplines & HODs</span>
            </div>
          </Link>

          <Link
            to="/super-admin/courses"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100 transition-all flex flex-col items-start gap-2 group"
          >
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center shrink-0 border border-amber-100 group-hover:scale-105 transition-transform">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-slate-800 block group-hover:text-indigo-600 transition-colors">
                Courses
              </span>
              <span className="text-[10px] text-slate-500">Catalog curriculum</span>
            </div>
          </Link>

          <Link
            to="/super-admin/offerings"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100 transition-all flex flex-col items-start gap-2 group"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-100 group-hover:scale-105 transition-transform">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-slate-800 block group-hover:text-indigo-600 transition-colors">
                Offerings
              </span>
              <span className="text-[10px] text-slate-500">Schedule classes</span>
            </div>
          </Link>

          <Link
            to="/super-admin/terms"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100 transition-all flex flex-col items-start gap-2 group"
          >
            <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center shrink-0 border border-sky-100 group-hover:scale-105 transition-transform">
              <Calendar className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-slate-800 block group-hover:text-indigo-600 transition-colors">
                Terms
              </span>
              <span className="text-[10px] text-slate-500">Academic calendar</span>
            </div>
          </Link>
        </div>
      </div>

      {/* Two-Column Layout: Term Calendar Governance & Recent Announcements */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Academic Term Operations */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-600" />
              Academic Term Lifecycle
            </h2>
            <Link
              to="/super-admin/terms"
              className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
            >
              <span>Manage Terms</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {activeTerm ? (
            <div className="space-y-3">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold text-slate-900">
                    {activeTerm.name}
                  </span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 uppercase">
                    {activeTerm.status}
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs text-slate-600 mt-3 pt-3 border-t border-slate-200/60">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">
                      Academic Year
                    </span>
                    <span className="font-semibold text-slate-800 font-mono">
                      {activeTerm.academic_year}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">
                      Term Number
                    </span>
                    <span className="font-semibold text-slate-800">
                      Term {activeTerm.term_number}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">
                      Enrollment Window
                    </span>
                    <span
                      className={`font-semibold inline-flex items-center gap-1 ${
                        activeTerm.is_enrollment_open
                          ? "text-emerald-700"
                          : "text-slate-500"
                      }`}
                    >
                      {activeTerm.is_enrollment_open ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-600" /> Open
                        </>
                      ) : (
                        "Closed"
                      )}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">
                      Start Date
                    </span>
                    <span className="font-mono text-slate-700">
                      {activeTerm.start_date}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">
                      End Date
                    </span>
                    <span className="font-mono text-slate-700">
                      {activeTerm.end_date}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">
                      Term Offerings
                    </span>
                    <span className="font-semibold text-indigo-700">
                      {metrics.published_course_offerings ?? 0} published
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500 px-1">
                <span>Total institutional terms configured: {terms.length}</span>
                <Link
                  to="/super-admin/terms"
                  className="text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  Activate or create term &rarr;
                </Link>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={Calendar}
              title="No active academic term"
              description="Activate an academic term in the Academic Terms module to open class scheduling and enrollment."
              className="border-none shadow-none my-2 p-6"
            />
          )}
        </div>

        {/* Institutional Announcements Feed */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Megaphone className="w-4 h-4 text-purple-600" />
              University Announcements
            </h2>
            <Link
              to="/super-admin/announcements"
              className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
            >
              <span>Manage Notices</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {announcements.length > 0 ? (
            <div className="space-y-3">
              {announcements.slice(0, 3).map((item) => (
                <div
                  key={item.id}
                  className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/70 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-bold text-slate-900 truncate">
                      {item.title}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase shrink-0 border ${
                        item.is_published
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : "bg-slate-100 text-slate-600 border-slate-200"
                      }`}
                    >
                      {item.is_published ? "Published" : "Draft"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 line-clamp-2">
                    {item.content}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-400 font-mono">
                    <span>Audience: {item.target_audience || "ALL"}</span>
                    {item.created_at && (
                      <span>
                        Posted: {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Megaphone}
              title="No recent announcements"
              description="Publish notices and circulars for faculty and students using the Announcements module."
              className="border-none shadow-none my-2 p-6"
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default SuperAdminDashboard;
