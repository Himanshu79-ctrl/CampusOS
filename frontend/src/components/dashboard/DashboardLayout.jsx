import React, { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export const DashboardLayout = ({ role, roleLabel, navItems = [] }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-900 font-sans antialiased">
      {/* Role-Specific Responsive Sidebar */}
      <Sidebar
        roleLabel={roleLabel}
        navItems={navItems}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed(!isCollapsed)}
        isMobileOpen={isMobileOpen}
        onCloseMobile={() => setIsMobileOpen(false)}
      />

      {/* Main App Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        <Topbar onOpenMobile={() => setIsMobileOpen(true)} />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
          <Outlet />
        </main>

        {/* Global Dashboard Footer */}
        <footer className="bg-white border-t border-slate-200/80 py-4 px-4 sm:px-6 lg:px-8 text-xs text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>&copy; {new Date().getFullYear()} CampusOS &bull; Academic Learning Management System</span>
          <span className="text-slate-400">Campus Learning Portal</span>
        </footer>
      </div>
    </div>
  );
};

export default DashboardLayout;
