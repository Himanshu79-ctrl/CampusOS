import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { lmsClient } from "@/services/api";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState } from "@/components/common/EmptyState";
import {
  BookOpen,
  CheckSquare,
  Calendar,
  Clock,
  Award,
  Users,
  FileText,
  Activity,
  ArrowRight,
} from "lucide-react";

export const FacultyDashboard = () => {
  const { user } = useAuth();
  const [coursesCount, setCoursesCount] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchFacultyData = async () => {
      try {
        const response = await lmsClient.get("/api/academics/offerings/");
        if (isMounted) {
          const list = response.data?.results || response.data || [];
          setCoursesCount(Array.isArray(list) ? list.length : 0);
        }
      } catch (err) {
        console.warn("Offerings endpoint returned error or pending:", err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchFacultyData();
    return () => {
      isMounted = false;
    };
  }, []);

  const displayName = user?.first_name
    ? `${user.first_name} ${user.last_name || ""}`.trim()
    : user?.username || "Faculty Member";

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title={`Welcome back, ${displayName}`}
        subtitle="Manage your courses, lectures, student attendance and grading."
        badge="Faculty Portal"
        badgeClasses="bg-blue-50 text-blue-800 border-blue-200"
      />

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="My Courses"
          value={coursesCount !== null ? coursesCount : null}
          subtext={
            coursesCount !== null
              ? `${coursesCount} course offerings assigned`
              : "Assigned course offerings this term"
          }
          icon={BookOpen}
          iconColor="text-blue-600"
          iconBg="bg-blue-50 border-blue-100"
          isLoading={isLoading}
        />

        <StatCard
          title="Active Assignments"
          value="—"
          subtext="Data integration pending"
          icon={CheckSquare}
          iconColor="text-indigo-600"
          iconBg="bg-indigo-50 border-indigo-100"
          isLoading={false}
        />

        <StatCard
          title="Attendance Sessions"
          value="—"
          subtext="Data integration pending"
          icon={Calendar}
          iconColor="text-emerald-600"
          iconBg="bg-emerald-50 border-emerald-100"
          isLoading={false}
        />

        <StatCard
          title="Pending Submissions"
          value="—"
          subtext="Data integration pending"
          icon={Award}
          iconColor="text-amber-600"
          iconBg="bg-amber-50 border-amber-100"
          isLoading={false}
        />
      </div>

      {/* Quick Action Shortcuts */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-3">
        <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
          Faculty Teaching Shortcuts
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Link
            to="/faculty/courses"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100">
              <BookOpen className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                My Courses
              </span>
              <span className="text-[10px] text-slate-500">Syllabus</span>
            </div>
          </Link>

          <Link
            to="/faculty/attendance"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 border border-emerald-100">
              <Calendar className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                Attendance
              </span>
              <span className="text-[10px] text-slate-500">Daily Roster</span>
            </div>
          </Link>

          <Link
            to="/faculty/assignments"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-100">
              <CheckSquare className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                Assignments
              </span>
              <span className="text-[10px] text-slate-500">Manage Tasks</span>
            </div>
          </Link>

          <Link
            to="/faculty/gradebook"
            className="p-3 rounded-xl border border-slate-100 bg-slate-50/70 hover:bg-slate-100/80 transition-all flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center shrink-0 border border-amber-100">
              <Award className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-xs font-bold text-slate-800 block truncate group-hover:text-indigo-600 transition-colors">
                Gradebook
              </span>
              <span className="text-[10px] text-slate-500">Scores & GPA</span>
            </div>
          </Link>
        </div>
      </div>

      {/* Two-Column Grid: Submissions & Timetable */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Submissions */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-indigo-600" />
              Recent Submissions
            </h2>
            <span className="text-[11px] text-slate-400 font-medium">Pending Review</span>
          </div>

          <EmptyState
            icon={CheckSquare}
            title="No pending student submissions"
            description="Student assignment submissions waiting for evaluation will appear in this queue."
            className="border-none shadow-none my-2 p-6"
          />
        </div>

        {/* Today's Teaching Schedule */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-2xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Clock className="w-4 h-4 text-emerald-600" />
              Today's Teaching Schedule
            </h2>
            <span className="text-[11px] text-slate-400 font-medium">Timetable</span>
          </div>

          <EmptyState
            icon={Clock}
            title="No lectures scheduled for today"
            description="Your daily timetable classes and lab sessions will be displayed here."
            className="border-none shadow-none my-2 p-6"
          />
        </div>
      </div>
    </div>
  );
};

export default FacultyDashboard;
