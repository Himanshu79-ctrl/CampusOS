import React from "react";
import { NavLink, Link } from "react-router-dom";
import {
  GraduationCap,
  ChevronLeft,
  ChevronRight,
  X,
  LogOut,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export const Sidebar = ({
  roleLabel = "Workspace",
  navItems = [],
  isCollapsed = false,
  onToggleCollapse,
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const { logout, user } = useAuth();

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isMobileOpen && (
        <div
          role="presentation"
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-xs lg:hidden transition-opacity"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed lg:sticky top-0 left-0 z-50 h-screen bg-slate-900 text-slate-300 border-r border-slate-800 flex flex-col justify-between transition-all duration-200 select-none ${
          /* Mobile Drawer Position */
          isMobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        } ${
          /* Desktop Width */
          isCollapsed ? "w-20" : "w-64"
        }`}
      >
        {/* Top Header / Branding */}
        <div>
          <div className="h-16 px-4 flex items-center justify-between border-b border-slate-800/80">
            <Link
              to="/"
              className={`flex items-center gap-3 text-white font-bold transition-opacity hover:opacity-90 ${
                isCollapsed ? "justify-center w-full" : ""
              }`}
              title="CampusOS"
            >
              <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-sm">
                <GraduationCap className="w-5 h-5" />
              </div>
              {!isCollapsed && (
                <div className="flex flex-col leading-none">
                  <span className="text-base tracking-tight text-white font-extrabold">CampusOS</span>
                  <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase mt-0.5">
                    {roleLabel}
                  </span>
                </div>
              )}
            </Link>

            {/* Mobile Close Button */}
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Items */}
          <nav className="p-3 space-y-1 overflow-y-auto max-h-[calc(100vh-140px)]">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => onCloseMobile && onCloseMobile()}
                  title={isCollapsed ? item.label : undefined}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 ${
                      isActive
                        ? "bg-indigo-600 text-white shadow-xs"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                    } ${isCollapsed ? "justify-center px-2" : ""}`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  {!isCollapsed && <span className="truncate">{item.label}</span>}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Bottom Actions: User snippet & Desktop Collapse Toggle */}
        <div className="p-3 border-t border-slate-800/80 space-y-2">
          {/* User info in expanded mode */}
          {!isCollapsed && (
            <div className="p-2.5 rounded-xl bg-slate-800/60 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold text-xs flex items-center justify-center shrink-0">
                  {user?.first_name?.charAt(0) || user?.username?.charAt(0)?.toUpperCase() || "U"}
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-white truncate leading-tight">
                    {user?.first_name ? `${user.first_name} ${user.last_name || ""}`.trim() : user?.username}
                  </p>
                  <p className="text-[10px] text-slate-400 font-mono truncate">{user?.role}</p>
                </div>
              </div>

              <button
                onClick={logout}
                title="Sign Out"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Desktop Collapse Toggle */}
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex w-full items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4" />
                <span className="text-[11px]">Collapse Menu</span>
              </>
            )}
          </button>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
