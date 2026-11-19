import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { lmsClient } from "@/services/api";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import {
  Users,
  Layers,
  GraduationCap,
  Calendar,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  Building2,
  BookOpen,
  BarChart3,
  Activity,
} from "lucide-react";

export const AdminDashboard = () => {
  const { user } = useAuth();
  const [overviewData, setOverviewData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const fetchOverview = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const response = await lmsClient.get("/api/admin/reports/overview/");
      setOverviewData(response.data);
    } catch (err) {
      console.warn("LMS overview endpoint not yet populated or unreachable:", err);
      setErrorMessage(
        err.response?.data?.detail ||
          "Unable to fetch live institutional overview from LMS service. Backend reports endpoint returned an error or is offline."
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const displayName = user?.first_name
    ? `${user.first_name} ${user.last_name || ""}`.trim()
    : user?.username || "Administrator";

  const metrics = overviewData?.institution_metrics || {};
  const attendance = overviewData?.attendance_overview || {};
  const termInfo = overviewData?.filters_applied || {};

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title={`Welcome back, ${displayName}`}
        subtitle="Institutional administration and academic governance overview."
        badge="Admin Portal"
        badgeClasses="bg-amber-50 text-amber-800 border-amber-200"
        actions={
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium hidden sm:inline">Active Role:</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-slate-700 font-semibold">
              {user?.role}
            </span>
          </div>
        }
      />

      {/* Error state if API call failed */}
      {errorMessage && (
        <ErrorState
          title="Institutional KPI Sync Notice"
          message={errorMessage}
          onRetry={fetchOverview}
        />
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Students"
          value={metrics.active_students ?? (overviewData ? overviewData.students?.active : null)}
          subtext={
            metrics.total_students !== undefined
              ? `Total enrolled: ${metrics.total_students}`
              : "Live count from Student Profile catalog"
          }
          icon={Users}
          iconColor="text-blue-600"
          iconBg="bg-blue-50 border-blue-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Course Offerings"
          value={metrics.published_course_offerings ?? (overviewData ? overviewData.offerings?.published : null)}
          subtext={
            metrics.total_course_offerings !== undefined
              ? `Total offerings: ${metrics.total_course_offerings}`
              : "Published courses this term"
          }
          icon={Layers}
          iconColor="text-indigo-600"
          iconBg="bg-indigo-50 border-indigo-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Active Term"
          value={termInfo.term_name || overviewData?.academic_term?.name || "Active Term"}
          subtext={
            termInfo.term_id
              ? `Term ID #${termInfo.term_id} (Active)`
              : "Academic term schedule"
          }
          icon={Calendar}
          iconColor="text-emerald-600"
          iconBg="bg-emerald-50 border-emerald-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Overall Attendance"
          value={
            attendance.overall_attendance_rate !== undefined
              ? `${attendance.overall_attendance_rate}%`
              : (overviewData?.attendance?.overall_percentage !== undefined
                  ? `${overviewData.attendance.overall_percentage}%`
                  : null)
          }
          subtext={
            attendance.total_records !== undefined
              ? `${attendance.total_records} attendance records`
              : "Attendance compliance rate"
          }
          icon={CheckCircle2}
          iconColor="text-amber-600"
          iconBg="bg-amber-50 border-amber-100"
          isLoading={isLoading}
        />
      </div>

      {/* Quick Actions Shortcuts */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-3">
        <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
          Quick Management Shortcuts
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Link
            to="/admin/students"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100">
              <Users className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                Students
              </span>
              <span className="text-[10px] text-slate-500">Directory</span>
            </div>
          </Link>

          <Link
            to="/admin/offerings"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-100">
              <Layers className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                Offerings
              </span>
              <span className="text-[10px] text-slate-500">Term Classes</span>
            </div>
          </Link>

          <Link
            to="/admin/terms"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 border border-emerald-100">
              <Calendar className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                Academic Terms
              </span>
              <span className="text-[10px] text-slate-500">Calendars</span>
            </div>
          </Link>

          <Link
            to="/admin/reports"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center shrink-0 border border-amber-100">
              <BarChart3 className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                Reports
              </span>
              <span className="text-[10px] text-slate-500">Analytics</span>
            </div>
          </Link>
        </div>
      </div>

      {/* Two-Column Grid: Recent Activity & Upcoming Events */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-600" />
                Recent System Activity
              </h2>
              <span className="text-[11px] text-slate-400 font-medium">Audit Trail</span>
            </div>

            <EmptyState
              icon={Activity}
              title="No recent admin audit logs"
              description="Administrative actions, role updates, and term activations will be logged here."
              className="border-none shadow-none my-2 p-6"
            />
          </div>
        </div>

        {/* Upcoming Institutional Events */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-emerald-600" />
                Upcoming Academic Events
              </h2>
              <span className="text-[11px] text-slate-400 font-medium">Schedule</span>
            </div>

            <EmptyState
              icon={Clock}
              title="No upcoming calendar deadlines"
              description="Enrollment windows, term completion dates, and exam schedules will appear here."
              className="border-none shadow-none my-2 p-6"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
