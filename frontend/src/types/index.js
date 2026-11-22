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

export const ROLE_ROUTE_PREFIXES = {
  super_admin: "/super-admin",
  admin: "/admin",
  faculty: "/faculty",
  student: "/student",
};

export const getDashboardForRole = (role) => {
  return ROLE_DASHBOARDS[role] || "/";
};

/**
 * Checks whether a given path is an authorized route for a specific user role.
 * Ensures users cannot be directed to another role's dashboard or subroutes.
 *
 * @param {string} path - URL pathname (e.g. "/student/dashboard", "/super-admin/courses")
 * @param {string} role - User role ("super_admin", "admin", "faculty", "student")
 * @returns {boolean} True if the path is permitted for the given role
 */
export const isRouteAllowedForRole = (path, role) => {
  if (!path || typeof path !== "string" || !role) return false;
  const prefix = ROLE_ROUTE_PREFIXES[role];
  if (!prefix) return false;
  return path === prefix || path.startsWith(`${prefix}/`);
};

/**
 * Decodes and extracts claims from a standard JWT token.
 * Works seamlessly in both browser and Node.js environments.
 *
 * @param {string} token - JWT access token
 * @returns {Object|null} Payload claims or null if invalid
 */
export const parseJwtClaims = (token) => {
  if (!token || typeof token !== "string") return null;
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    if (typeof atob === "function") {
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split("")
          .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
          .join("")
      );
      return JSON.parse(jsonPayload);
    }
    if (typeof Buffer !== "undefined") {
      const jsonPayload = Buffer.from(base64, "base64").toString("utf8");
      return JSON.parse(jsonPayload);
    }
    return null;
  } catch {
    return null;
  }
};
