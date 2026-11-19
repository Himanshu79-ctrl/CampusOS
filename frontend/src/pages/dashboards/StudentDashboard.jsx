import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { lmsClient } from "@/services/api";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState } from "@/components/common/EmptyState";
import { studentAttendanceApi } from "@/services/studentService";
import {
  GraduationCap,
  BookOpen,
  Calendar,
  Clock,
  Award,
  Bell,
  CheckSquare,
  FileText,
  AlertCircle,
} from "lucide-react";

export const StudentDashboard = () => {
  const { user } = useAuth();
  const [profileData, setProfileData] = useState(null);
  const [enrollmentsCount, setEnrollmentsCount] = useState(null);
  const [attendanceData, setAttendanceData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchStudentData = async () => {
      try {
        const [profRes, enrRes, attRes] = await Promise.all([
          lmsClient.get("/api/students/profile/me/").catch(() => null),
          lmsClient.get("/api/students/profile/me/enrollments/").catch(() => null),
          studentAttendanceApi.getMySummary().catch(() => []),
        ]);
        if (isMounted) {
          if (profRes) setProfileData(profRes.data);
          if (enrRes && Array.isArray(enrRes.data)) {
            setEnrollmentsCount(enrRes.data.length);
          }
          if (attRes) setAttendanceData(Array.isArray(attRes) ? attRes : []);
        }
      } catch (err) {
        console.warn("Student data fetch notice:", err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchStudentData();
    return () => {
      isMounted = false;
    };
  }, []);

  const displayName = user?.first_name
    ? `${user.first_name} ${user.last_name || ""}`.trim()
    : user?.username || "Student";

  const attList = Array.isArray(attendanceData) ? attendanceData : [];
  const totalSessions = attList.reduce((acc, c) => acc + (c.total_sessions || 0), 0);
  const totalAttended = attList.reduce((acc, c) => acc + (c.attended_count || 0), 0);
  const attRate = totalSessions > 0 ? Math.round((totalAttended / totalSessions) * 100) : null;
  const attendanceDisplay =
    attRate !== null ? `${attRate}% Attendance` : "No Records Yet";
  const attendanceSubtext =
    attRate !== null
      ? (attRate >= 75 ? "Good Standing (≥75%)" : "Attendance Warning (<75%)")
      : "No sessions recorded";

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title={`Welcome back, ${displayName}`}
        subtitle="Access your academic courses, submissions, attendance standing and schedule."
        badge="Student Portal"
        badgeClasses="bg-emerald-50 text-emerald-800 border-emerald-200"
      />

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Enrolled Courses"
          value={enrollmentsCount !== null ? `${enrollmentsCount} Active` : "—"}
          subtext={
            enrollmentsCount !== null
              ? `${enrollmentsCount} verified classes`
              : "Enrollment verification active"
          }
          icon={BookOpen}
          iconColor="text-emerald-600"
          iconBg="bg-emerald-50 border-emerald-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Attendance Standing"
          value={attendanceDisplay}
          subtext={attendanceSubtext}
          icon={Calendar}
          iconColor={attRate === null ? "text-slate-400" : attRate >= 75 ? "text-emerald-600" : "text-rose-600"}
          iconBg={attRate === null ? "bg-slate-50 border-slate-100" : attRate >= 75 ? "bg-emerald-50 border-emerald-100" : "bg-rose-50 border-rose-100"}
          isLoading={isLoading}
        />

        <StatCard
          title="Upcoming Deadlines"
          value="Check Items"
          subtext="Assignments & course activities"
          icon={CheckSquare}
          iconColor="text-indigo-600"
          iconBg="bg-indigo-50 border-indigo-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Academic Standing"
          value={profileData?.current_semester ? `Semester ${profileData.current_semester}` : "Active"}
          subtext={profileData?.registration_number ? `Reg: ${profileData.registration_number}` : "Current semester status"}
          icon={GraduationCap}
          iconColor="text-purple-600"
          iconBg="bg-purple-50 border-purple-100"
          isLoading={isLoading}
        />
      </div>

      {/* Quick Action Shortcuts */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-3">
        <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
          Student Academic Shortcuts
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Link
            to="/student/courses"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 border border-emerald-100">
              <BookOpen className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                My Courses
              </span>
              <span className="text-[10px] text-slate-500">Classes</span>
            </div>
          </Link>

          <Link
            to="/student/assignments"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-100">
              <CheckSquare className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                Assignments
              </span>
              <span className="text-[10px] text-slate-500">Submissions</span>
            </div>
          </Link>

          <Link
            to="/student/timetable"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100">
              <Clock className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                Timetable
              </span>
              <span className="text-[10px] text-slate-500">Schedule</span>
            </div>
          </Link>

          <Link
            to="/student/grades"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center shrink-0 border border-amber-100">
              <Award className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                My Grades
              </span>
              <span className="text-[10px] text-slate-500">Scorecard</span>
            </div>
          </Link>
        </div>
      </div>

      {/* Two-Column Grid: Deadlines & Today's Classes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upcoming Deadlines */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-indigo-600" />
              Pending Homework & Quizzes
            </h2>
            <span className="text-[11px] text-slate-400 font-medium">Deadlines</span>
          </div>

          <EmptyState
            icon={CheckSquare}
            title="No upcoming assignments due"
            description="Your pending assignment deadlines and quiz submissions will appear here."
            className="border-none shadow-none my-2 p-6"
          />
        </div>

        {/* Today's Lectures */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Clock className="w-4 h-4 text-emerald-600" />
              Today's Lecture Schedule
            </h2>
            <span className="text-[11px] text-slate-400 font-medium">Timetable</span>
          </div>

          <EmptyState
            icon={Clock}
            title="No classes scheduled today"
            description="Your lecture times, room allocations and faculty details will show here."
            className="border-none shadow-none my-2 p-6"
          />
        </div>
      </div>
    </div>
  );
};

export default StudentDashboard;
