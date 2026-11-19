import React from "react";
import { Outlet, Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { getDashboardForRole } from "@/types";
import {
  GraduationCap,
  LogIn,
  LogOut,
  LayoutDashboard,
} from "lucide-react";

export const RootLayout = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans antialiased">
      {/* Top Navbar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link
            to="/"
            className="flex items-center gap-2.5 text-slate-900 font-bold text-lg hover:opacity-90 transition-opacity"
          >
            <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-xs">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div className="flex flex-col leading-tight">
              <span className="font-extrabold tracking-tight text-slate-900">CampusOS</span>
              <span className="text-[10px] text-slate-500 font-medium tracking-wide">University LMS</span>
            </div>
          </Link>

          <nav className="flex items-center gap-3">
            {isAuthenticated && user ? (
              <div className="flex items-center gap-3">
                <Link
                  to={getDashboardForRole(user.role)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors shadow-2xs"
                >
                  <LayoutDashboard className="w-3.5 h-3.5" />
                  <span>My Dashboard</span>
                </Link>

                <div className="hidden sm:flex items-center gap-2 text-xs text-slate-600 pl-3 border-l border-slate-200">
                  <span className="font-semibold text-slate-800">
                    {user.first_name || user.username}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 text-[10px] font-mono capitalize">
                    {user.role}
                  </span>
                </div>

                <button
                  onClick={handleLogout}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-600 hover:text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition-colors cursor-pointer"
                  title="Sign out of CampusOS"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Sign Out</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span>Sign In</span>
                </Link>
              </div>
            )}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Clean University Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span>&copy; {new Date().getFullYear()} CampusOS &bull; Academic Learning Management System. All rights reserved.</span>
          <span className="text-slate-400">Unified Portal for Students, Faculty & Administrators</span>
        </div>
      </footer>
    </div>
  );
};

export default RootLayout;
