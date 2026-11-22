import React, { useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import {
  Menu,
  GraduationCap,
  LogOut,
  ChevronDown,
  ExternalLink,
} from "lucide-react";

export const Topbar = ({ onOpenMobile }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true, state: null });
  };

  const userInitial =
    user?.first_name?.charAt(0) || user?.username?.charAt(0)?.toUpperCase() || "U";
  const displayName = user?.first_name
    ? `${user.first_name} ${user.last_name || ""}`.trim()
    : user?.username || "Authenticated User";

  return (
    <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 px-4 sm:px-6 lg:px-8 flex items-center justify-between">
      {/* Left: Mobile trigger & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobile}
          className="lg:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          aria-label="Open mobile menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Brand link on mobile when sidebar is hidden */}
        <Link
          to="/"
          className="lg:hidden flex items-center gap-2 text-slate-900 font-bold text-sm"
        >
          <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center">
            <GraduationCap className="w-4 h-4" />
          </div>
          <span>CampusOS</span>
        </Link>

        {/* Desktop Breadcrumbs */}
        <div className="hidden sm:block">
          <Breadcrumbs />
        </div>
      </div>

      {/* Right: Status badge & User Dropdown */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Academic Session Indicator */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span>Academic Portal Active</span>
        </div>

        {/* User Profile Menu Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2.5 p-1 sm:px-2.5 sm:py-1.5 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer text-left"
            aria-expanded={dropdownOpen}
            aria-haspopup="true"
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shadow-xs">
              {userInitial}
            </div>

            <div className="hidden sm:flex flex-col">
              <span className="text-xs font-semibold text-slate-900 leading-tight">
                {displayName}
              </span>
              <span className="text-[10px] text-slate-500 font-mono">{user?.role}</span>
            </div>

            <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
          </button>

          {/* Dropdown Menu */}
          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border border-slate-200 p-2 z-50 animate-in fade-in zoom-in-95">
              {/* User summary */}
              <div className="p-3 bg-slate-50 rounded-xl mb-1 border border-slate-100">
                <p className="text-xs font-bold text-slate-900 leading-tight">{displayName}</p>
                <p className="text-[11px] text-slate-500 font-mono truncate mt-0.5">
                  {user?.email || "No email registered"}
                </p>
                <div className="mt-2 flex items-center gap-1.5">
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {user?.role}
                  </span>
                </div>
              </div>

              {/* Navigation links */}
              <div className="space-y-0.5">
                <Link
                  to="/"
                  onClick={() => setDropdownOpen(false)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-slate-700 hover:bg-slate-100 transition-colors font-medium"
                >
                  <ExternalLink className="w-4 h-4 text-slate-400" />
                  <span>Public Portal Overview</span>
                </Link>
              </div>

              {/* Sign out button */}
              <div className="mt-1 pt-1 border-t border-slate-100">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-rose-600 hover:bg-rose-50 transition-colors font-medium cursor-pointer"
                >
                  <LogOut className="w-4 h-4 text-rose-500" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Topbar;
