import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  GraduationCap,
  LogOut,
  User,
  Mail,
  Shield,
  Layers,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";

export const DashboardShell = ({
  title,
  subtitle,
  icon: Icon,
  roleLabel,
  badgeClasses = "bg-indigo-50 text-indigo-700 border-indigo-200",
  children,
}) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true, state: null });
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-2.5 text-slate-900 font-bold text-lg hover:opacity-90">
              <div className="w-9 h-9 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-sm">
                <GraduationCap className="w-5 h-5" />
              </div>
              <span>CampusOS</span>
            </Link>
            <span className="hidden sm:inline-block text-slate-300">|</span>
            <span className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${badgeClasses}`}>
              {roleLabel}
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex flex-col text-right">
              <span className="text-sm font-semibold text-slate-800">
                {user?.first_name ? `${user.first_name} ${user.last_name || ""}`.trim() : user?.username}
              </span>
              <span className="text-xs text-slate-500 font-mono">{user?.email || user?.username}</span>
            </div>

            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Role Hero Card */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
              <Icon className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
              </div>
              <p className="text-sm text-slate-500 mt-1">{subtitle}</p>
            </div>
          </div>

          <Link
            to="/"
            className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
          >
            <span>Overview & Endpoints</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Authenticated Identity Details */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-indigo-600" />
            Verified Auth Service Identity
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase block">Username</span>
              <span className="text-sm font-semibold text-slate-800 font-mono mt-0.5 block truncate">
                {user?.username || "—"}
              </span>
            </div>
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase block">Email</span>
              <span className="text-sm font-semibold text-slate-800 font-mono mt-0.5 block truncate">
                {user?.email || "—"}
              </span>
            </div>
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase block">Full Name</span>
              <span className="text-sm font-semibold text-slate-800 mt-0.5 block truncate">
                {user?.first_name ? `${user.first_name} ${user.last_name || ""}`.trim() : "—"}
              </span>
            </div>
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase block">Role</span>
              <span className="text-sm font-semibold text-slate-800 font-mono mt-0.5 block truncate">
                {user?.role || "—"}
              </span>
            </div>
          </div>
        </div>

        {/* Specific Role Content / Placeholder */}
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        CampusOS Unified Operating System &bull; Active JWT Authentication Session
      </footer>
    </div>
  );
};

export default DashboardShell;
