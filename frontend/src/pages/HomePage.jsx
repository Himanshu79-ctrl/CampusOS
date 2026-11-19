import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { getDashboardForRole } from "@/types";
import {
  GraduationCap,
  BookOpen,
  CheckCircle,
  Calendar,
  ArrowRight,
  UserCheck,
  Award,
  Sparkles,
} from "lucide-react";

export const HomePage = () => {
  const { isAuthenticated, user } = useAuth();

  const destination = isAuthenticated && user ? getDashboardForRole(user.role) : "/login";

  return (
    <div className="space-y-12 py-4">
      {/* Hero Welcome Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-900 via-indigo-800 to-slate-900 text-white p-8 sm:p-14 shadow-xl">
        {/* Subtle background glow */}
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/15 text-indigo-200 text-xs font-medium">
            <GraduationCap className="w-4 h-4 text-indigo-300" />
            <span>Academic Learning Management System</span>
          </div>

          <div className="space-y-3">
            <h1 className="text-3xl sm:text-5xl font-black tracking-tight leading-tight">
              Your Campus. Your Learning. <br className="hidden sm:inline" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-200 via-white to-blue-200">
                One Platform.
              </span>
            </h1>
            <p className="text-indigo-100 text-sm sm:text-base leading-relaxed max-w-2xl">
              Welcome to CampusOS. A simple, unified academic portal for students, faculty, and academic staff to access courses, lecture materials, attendance, assignments, and grades.
            </p>
          </div>

          <div className="pt-2 flex flex-wrap items-center gap-4">
            <Link
              to={destination}
              className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-2xl text-sm font-bold text-slate-900 bg-white hover:bg-indigo-50 shadow-lg hover:shadow-xl transition-all duration-200 hover:-translate-y-0.5 cursor-pointer"
            >
              <span>{isAuthenticated ? "Go to My Dashboard" : "Sign In to CampusOS"}</span>
              <ArrowRight className="w-4 h-4 text-indigo-600" />
            </Link>

            {!isAuthenticated && (
              <span className="text-xs text-indigo-200">
                Use your university username and password to log in.
              </span>
            )}
          </div>
        </div>
      </section>

      {/* Everyday LMS Pillars */}
      <section className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            Everything you need for your academic journey
          </h2>
          <p className="text-xs sm:text-sm text-slate-500">
            Designed for an intuitive learning and teaching experience across all college departments.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:border-slate-300 transition-all space-y-4">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
              <BookOpen className="w-6 h-6" />
            </div>
            <div className="space-y-1.5">
              <h3 className="font-bold text-slate-900 text-base">Course Content & Lessons</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Browse course modules, read lecture notes, explore study links, and track your lesson progress at your own pace.
              </p>
            </div>
            <ul className="space-y-2 pt-2 border-t border-slate-100 text-xs text-slate-600">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Weekly lecture syllabi & readings</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Reference materials & slide decks</span>
              </li>
            </ul>
          </div>

          {/* Card 2 */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:border-slate-300 transition-all space-y-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
              <Award className="w-6 h-6" />
            </div>
            <div className="space-y-1.5">
              <h3 className="font-bold text-slate-900 text-base">Assignments & Grades</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Stay updated on assignment deadlines, submit homework online, and receive transparent evaluation feedback.
              </p>
            </div>
            <ul className="space-y-2 pt-2 border-t border-slate-100 text-xs text-slate-600">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Online submissions & rubrics</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Continuous assessment gradebook</span>
              </li>
            </ul>
          </div>

          {/* Card 3 */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:border-slate-300 transition-all space-y-4">
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
              <Calendar className="w-6 h-6" />
            </div>
            <div className="space-y-1.5">
              <h3 className="font-bold text-slate-900 text-base">Attendance & Timetables</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Check your weekly classroom schedule, room allocations, and maintain the minimum 75% attendance threshold.
              </p>
            </div>
            <ul className="space-y-2 pt-2 border-t border-slate-100 text-xs text-slate-600">
              <li className="flex items-center gap-2">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Weekly lecture & lab schedule</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                <span>Session presence history & alerts</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Role Access Banner */}
      <section className="bg-white rounded-2xl border border-slate-200 p-8 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="space-y-1">
          <h3 className="font-bold text-slate-900 text-lg">Are you a Student, Faculty, or Administrator?</h3>
          <p className="text-xs text-slate-500 max-w-xl">
            CampusOS automatically routes you to your designated portal upon signing in with your institutional credentials.
          </p>
        </div>
        <Link
          to={destination}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors shrink-0"
        >
          <UserCheck className="w-4 h-4" />
          <span>{isAuthenticated ? "Open My Portal" : "Sign In Now"}</span>
        </Link>
      </section>
    </div>
  );
};

export default HomePage;
