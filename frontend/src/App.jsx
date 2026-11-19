import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute, RoleBasedRoute } from "@/components/auth";
import { DashboardLayout } from "@/components/dashboard";
import { RootLayout } from "@/layouts/RootLayout";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/auth/LoginPage";
import { PasswordSetupPage } from "@/pages/auth/PasswordSetupPage";
import {
  AdminDashboard,
  FacultyDashboard,
  StudentDashboard,
  SuperAdminDashboard,
  ModulePlaceholderPage,
} from "@/pages/dashboards";
import {
  AdminDepartmentsPage,
  AdminFacultyPage,
  AdminCoursesPage,
  AdminTermsPage,
  AdminOfferingsPage,
  AdminStudentsPage,
  AdminReportsPage,
  AdminAnnouncementsPage,
} from "@/pages/admin";
import {
  FacultyCoursesPage,
  FacultyContentPage,
  FacultyAssignmentsPage,
  FacultyAttendancePage,
  FacultyTimetablePage,
  FacultyGradebookPage,
  FacultyAnnouncementsPage,
} from "@/pages/faculty";
import {
  StudentCoursesPage,
  StudentMaterialsPage,
  StudentAssignmentsPage,
  StudentAttendancePage,
  StudentTimetablePage,
  StudentGradesPage,
  StudentNotificationsPage,
} from "@/pages/student";
import {
  ADMIN_NAV_ITEMS,
  FACULTY_NAV_ITEMS,
  STUDENT_NAV_ITEMS,
  SUPER_ADMIN_NAV_ITEMS,
} from "@/config/navigation";
import { USER_ROLES } from "@/types";
import { ShieldCheck, Server } from "lucide-react";

export const App = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Root Layout */}
          <Route path="/" element={<RootLayout />}>
            <Route index element={<HomePage />} />
          </Route>

          {/* Authentication Pages */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/set-password" element={<PasswordSetupPage />} />

          {/* =========================================================================
              1. Admin Routes (/admin/*)
              Allowed: admin, super_admin
             ========================================================================= */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <RoleBasedRoute allowedRoles={[USER_ROLES.ADMIN, USER_ROLES.SUPER_ADMIN]}>
                  <DashboardLayout
                    role="admin"
                    roleLabel="Administrator Portal"
                    navItems={ADMIN_NAV_ITEMS}
                  />
                </RoleBasedRoute>
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="dashboard" element={<AdminDashboard />} />
            <Route path="students" element={<AdminStudentsPage />} />
            <Route path="faculty" element={<AdminFacultyPage />} />
            <Route path="departments" element={<AdminDepartmentsPage />} />
            <Route path="courses" element={<AdminCoursesPage />} />
            <Route path="terms" element={<AdminTermsPage />} />
            <Route path="offerings" element={<AdminOfferingsPage />} />
            <Route path="reports" element={<AdminReportsPage />} />
            <Route path="announcements" element={<AdminAnnouncementsPage />} />
          </Route>

          {/* =========================================================================
              2. Faculty Routes (/faculty/*)
              Allowed: faculty, super_admin
             ========================================================================= */}
          <Route
            path="/faculty"
            element={
              <ProtectedRoute>
                <RoleBasedRoute allowedRoles={[USER_ROLES.FACULTY, USER_ROLES.SUPER_ADMIN]}>
                  <DashboardLayout
                    role="faculty"
                    roleLabel="Faculty Portal"
                    navItems={FACULTY_NAV_ITEMS}
                  />
                </RoleBasedRoute>
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/faculty/dashboard" replace />} />
            <Route path="dashboard" element={<FacultyDashboard />} />
            <Route path="courses" element={<FacultyCoursesPage />} />
            <Route path="content" element={<FacultyContentPage />} />
            <Route path="assignments" element={<FacultyAssignmentsPage />} />
            <Route path="attendance" element={<FacultyAttendancePage />} />
            <Route path="timetable" element={<FacultyTimetablePage />} />
            <Route path="gradebook" element={<FacultyGradebookPage />} />
            <Route path="announcements" element={<FacultyAnnouncementsPage />} />
          </Route>

          {/* =========================================================================
              3. Student Routes (/student/*)
              Allowed: student, super_admin
             ========================================================================= */}
          <Route
            path="/student"
            element={
              <ProtectedRoute>
                <RoleBasedRoute allowedRoles={[USER_ROLES.STUDENT, USER_ROLES.SUPER_ADMIN]}>
                  <DashboardLayout
                    role="student"
                    roleLabel="Student Learning Space"
                    navItems={STUDENT_NAV_ITEMS}
                  />
                </RoleBasedRoute>
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/student/dashboard" replace />} />
            <Route path="dashboard" element={<StudentDashboard />} />
            <Route path="courses" element={<StudentCoursesPage />} />
            <Route path="materials" element={<StudentMaterialsPage />} />
            <Route path="assignments" element={<StudentAssignmentsPage />} />
            <Route path="attendance" element={<StudentAttendancePage />} />
            <Route path="timetable" element={<StudentTimetablePage />} />
            <Route path="grades" element={<StudentGradesPage />} />
            <Route path="notifications" element={<StudentNotificationsPage />} />
          </Route>

          {/* =========================================================================
              4. Super Admin Routes (/super-admin/*)
              Allowed: super_admin only
             ========================================================================= */}
          <Route
            path="/super-admin"
            element={
              <ProtectedRoute>
                <RoleBasedRoute allowedRoles={[USER_ROLES.SUPER_ADMIN]}>
                  <DashboardLayout
                    role="super_admin"
                    roleLabel="Super Admin Console"
                    navItems={SUPER_ADMIN_NAV_ITEMS}
                  />
                </RoleBasedRoute>
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/super-admin/dashboard" replace />} />
            <Route path="dashboard" element={<SuperAdminDashboard />} />
            <Route path="console" element={<Navigate to="/super-admin/dashboard" replace />} />
            <Route path="students" element={<AdminStudentsPage />} />
            <Route path="faculty" element={<AdminFacultyPage />} />
            <Route path="departments" element={<AdminDepartmentsPage />} />
            <Route path="courses" element={<AdminCoursesPage />} />
            <Route path="terms" element={<AdminTermsPage />} />
            <Route path="offerings" element={<AdminOfferingsPage />} />
            <Route path="reports" element={<AdminReportsPage />} />
            <Route path="announcements" element={<AdminAnnouncementsPage />} />
            <Route path="system" element={<Navigate to="/super-admin/dashboard" replace />} />
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
