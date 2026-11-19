/**
 * Shared Constant Definitions for CampusOS Frontend.
 */

export const USER_ROLES = {
  SUPER_ADMIN: "super_admin",
  ADMIN: "admin",
  FACULTY: "faculty",
  STUDENT: "student",
};

export const ROLE_DASHBOARDS = {
  super_admin: "/super-admin/dashboard",
  admin: "/admin/dashboard",
  faculty: "/faculty/dashboard",
  student: "/student/dashboard",
};

export const getDashboardForRole = (role) => {
  return ROLE_DASHBOARDS[role] || "/";
};
