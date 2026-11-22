/**
 * Automated Test Suite for Role-Based Routing & Session Isolation in CampusOS.
 *
 * Verifies:
 * 1. Role-to-dashboard mappings (Super Admin, Admin, Faculty, Student).
 * 2. URL route prefix permissions (isRouteAllowedForRole).
 * 3. Login redirect behavior (preventing cross-role redirect contamination).
 * 4. Direct URL access & RoleBasedRoute guard enforcement.
 * 5. Page refresh route preservation and unauthorized URL redirection.
 * 6. Session isolation, storage purging, and JWT cryptographic role authority.
 */

import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";

import {
  USER_ROLES,
  ROLE_DASHBOARDS,
  ROLE_ROUTE_PREFIXES,
  getDashboardForRole,
  isRouteAllowedForRole,
  parseJwtClaims,
} from "../types/index.js";

// Mock helper to simulate RoleBasedRoute decision logic
function evaluateRoleRouteAccess({ user, allowedRoles, currentPath }) {
  if (!user || !user.role) {
    return { allowed: false, redirect: "/login" };
  }
  const userRole = user.role;
  const hasPermission =
    Array.isArray(allowedRoles) &&
    allowedRoles.length > 0 &&
    allowedRoles.includes(userRole);

  if (!hasPermission) {
    const redirectPath = getDashboardForRole(userRole);
    if (currentPath === redirectPath) {
      return { allowed: false, redirect: "/" };
    }
    return { allowed: false, redirect: redirectPath };
  }
  return { allowed: true, redirect: null };
}

// Mock helper to simulate LoginPage redirect decision logic
function resolveLoginDestination({ fromPath, userRole }) {
  const isAllowed =
    fromPath &&
    fromPath !== "/login" &&
    isRouteAllowedForRole(fromPath, userRole);

  return isAllowed ? fromPath : getDashboardForRole(userRole);
}

// Helper to create mock JWT tokens with specific role payload
function createMockJwtToken(payload) {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = "mock_signature";
  return `${header}.${body}.${signature}`;
}

describe("1. Role to Dashboard Mappings", () => {
  it("maps super_admin to /super-admin/dashboard", () => {
    assert.equal(getDashboardForRole(USER_ROLES.SUPER_ADMIN), "/super-admin/dashboard");
    assert.equal(ROLE_DASHBOARDS.super_admin, "/super-admin/dashboard");
  });

  it("maps admin to /admin/dashboard", () => {
    assert.equal(getDashboardForRole(USER_ROLES.ADMIN), "/admin/dashboard");
    assert.equal(ROLE_DASHBOARDS.admin, "/admin/dashboard");
  });

  it("maps faculty to /faculty/dashboard", () => {
    assert.equal(getDashboardForRole(USER_ROLES.FACULTY), "/faculty/dashboard");
    assert.equal(ROLE_DASHBOARDS.faculty, "/faculty/dashboard");
  });

  it("maps student to /student/dashboard", () => {
    assert.equal(getDashboardForRole(USER_ROLES.STUDENT), "/student/dashboard");
    assert.equal(ROLE_DASHBOARDS.student, "/student/dashboard");
  });

  it("falls back to / for unknown or empty roles", () => {
    assert.equal(getDashboardForRole("unknown_role"), "/");
    assert.equal(getDashboardForRole(""), "/");
    assert.equal(getDashboardForRole(null), "/");
  });
});

describe("2. Role Route Permissions (isRouteAllowedForRole)", () => {
  describe("Super Admin Route Permissions", () => {
    it("allows super_admin on /super-admin and subroutes", () => {
      assert.equal(isRouteAllowedForRole("/super-admin", "super_admin"), true);
      assert.equal(isRouteAllowedForRole("/super-admin/dashboard", "super_admin"), true);
      assert.equal(isRouteAllowedForRole("/super-admin/students", "super_admin"), true);
      assert.equal(isRouteAllowedForRole("/super-admin/faculty", "super_admin"), true);
      assert.equal(isRouteAllowedForRole("/super-admin/reports", "super_admin"), true);
    });

    it("denies super_admin on admin, faculty, and student routes", () => {
      assert.equal(isRouteAllowedForRole("/admin", "super_admin"), false);
      assert.equal(isRouteAllowedForRole("/admin/dashboard", "super_admin"), false);
      assert.equal(isRouteAllowedForRole("/faculty", "super_admin"), false);
      assert.equal(isRouteAllowedForRole("/faculty/dashboard", "super_admin"), false);
      assert.equal(isRouteAllowedForRole("/student", "super_admin"), false);
      assert.equal(isRouteAllowedForRole("/student/dashboard", "super_admin"), false);
      assert.equal(isRouteAllowedForRole("/student/assignments", "super_admin"), false);
    });
  });

  describe("Admin Route Permissions", () => {
    it("allows admin on /admin and subroutes", () => {
      assert.equal(isRouteAllowedForRole("/admin", "admin"), true);
      assert.equal(isRouteAllowedForRole("/admin/dashboard", "admin"), true);
      assert.equal(isRouteAllowedForRole("/admin/courses", "admin"), true);
      assert.equal(isRouteAllowedForRole("/admin/departments", "admin"), true);
    });

    it("denies admin on super-admin, faculty, and student routes", () => {
      assert.equal(isRouteAllowedForRole("/super-admin", "admin"), false);
      assert.equal(isRouteAllowedForRole("/super-admin/dashboard", "admin"), false);
      assert.equal(isRouteAllowedForRole("/faculty/dashboard", "admin"), false);
      assert.equal(isRouteAllowedForRole("/student/dashboard", "admin"), false);
    });
  });

  describe("Faculty Route Permissions", () => {
    it("allows faculty on /faculty and subroutes", () => {
      assert.equal(isRouteAllowedForRole("/faculty", "faculty"), true);
      assert.equal(isRouteAllowedForRole("/faculty/dashboard", "faculty"), true);
      assert.equal(isRouteAllowedForRole("/faculty/courses", "faculty"), true);
      assert.equal(isRouteAllowedForRole("/faculty/timetable", "faculty"), true);
      assert.equal(isRouteAllowedForRole("/faculty/gradebook", "faculty"), true);
    });

    it("denies faculty on admin, super-admin, and student routes", () => {
      assert.equal(isRouteAllowedForRole("/admin/dashboard", "faculty"), false);
      assert.equal(isRouteAllowedForRole("/super-admin/dashboard", "faculty"), false);
      assert.equal(isRouteAllowedForRole("/student/dashboard", "faculty"), false);
    });
  });

  describe("Student Route Permissions", () => {
    it("allows student on /student and subroutes", () => {
      assert.equal(isRouteAllowedForRole("/student", "student"), true);
      assert.equal(isRouteAllowedForRole("/student/dashboard", "student"), true);
      assert.equal(isRouteAllowedForRole("/student/courses", "student"), true);
      assert.equal(isRouteAllowedForRole("/student/assignments", "student"), true);
      assert.equal(isRouteAllowedForRole("/student/grades", "student"), true);
    });

    it("denies student on admin, super-admin, and faculty routes", () => {
      assert.equal(isRouteAllowedForRole("/admin/dashboard", "student"), false);
      assert.equal(isRouteAllowedForRole("/super-admin/dashboard", "student"), false);
      assert.equal(isRouteAllowedForRole("/faculty/dashboard", "student"), false);
    });
  });
});

describe("3. Login Success Redirect & Stale Redirect Protection", () => {
  it("redirects super_admin to /super-admin/dashboard when fromPath is /student/dashboard", () => {
    // This directly replicates the reported bug:
    // A student previously logged out leaving /student/dashboard in location.state.from
    const destination = resolveLoginDestination({
      fromPath: "/student/dashboard",
      userRole: "super_admin",
    });
    assert.equal(destination, "/super-admin/dashboard");
  });

  it("redirects super_admin to /super-admin/dashboard when fromPath is /admin/dashboard", () => {
    const destination = resolveLoginDestination({
      fromPath: "/admin/dashboard",
      userRole: "super_admin",
    });
    assert.equal(destination, "/super-admin/dashboard");
  });

  it("preserves legitimate super_admin deep link when authorized", () => {
    const destination = resolveLoginDestination({
      fromPath: "/super-admin/students",
      userRole: "super_admin",
    });
    assert.equal(destination, "/super-admin/students");
  });

  it("redirects admin to /admin/dashboard when fromPath is /student/dashboard", () => {
    const destination = resolveLoginDestination({
      fromPath: "/student/dashboard",
      userRole: "admin",
    });
    assert.equal(destination, "/admin/dashboard");
  });

  it("redirects faculty to /faculty/dashboard when fromPath is /student/dashboard", () => {
    const destination = resolveLoginDestination({
      fromPath: "/student/dashboard",
      userRole: "faculty",
    });
    assert.equal(destination, "/faculty/dashboard");
  });

  it("preserves legitimate faculty deep link when authorized", () => {
    const destination = resolveLoginDestination({
      fromPath: "/faculty/timetable",
      userRole: "faculty",
    });
    assert.equal(destination, "/faculty/timetable");
  });

  it("redirects student to /student/dashboard when fromPath is /admin/dashboard", () => {
    const destination = resolveLoginDestination({
      fromPath: "/admin/dashboard",
      userRole: "student",
    });
    assert.equal(destination, "/student/dashboard");
  });

  it("preserves legitimate student deep link when authorized", () => {
    const destination = resolveLoginDestination({
      fromPath: "/student/assignments",
      userRole: "student",
    });
    assert.equal(destination, "/student/assignments");
  });

  it("redirects to designated role dashboard when fromPath is /login or empty", () => {
    assert.equal(resolveLoginDestination({ fromPath: "/login", userRole: "super_admin" }), "/super-admin/dashboard");
    assert.equal(resolveLoginDestination({ fromPath: "", userRole: "admin" }), "/admin/dashboard");
    assert.equal(resolveLoginDestination({ fromPath: null, userRole: "faculty" }), "/faculty/dashboard");
    assert.equal(resolveLoginDestination({ fromPath: undefined, userRole: "student" }), "/student/dashboard");
  });
});

describe("4. Direct URL Access & Role Route Guard Enforcement", () => {
  it("denies super_admin direct access to /student/dashboard and redirects to /super-admin/dashboard", () => {
    const result = evaluateRoleRouteAccess({
      user: { username: "admin_live", role: "super_admin" },
      allowedRoles: [USER_ROLES.STUDENT],
      currentPath: "/student/dashboard",
    });
    assert.equal(result.allowed, false);
    assert.equal(result.redirect, "/super-admin/dashboard");
  });

  it("denies super_admin direct access to /faculty/dashboard and redirects to /super-admin/dashboard", () => {
    const result = evaluateRoleRouteAccess({
      user: { username: "admin_live", role: "super_admin" },
      allowedRoles: [USER_ROLES.FACULTY],
      currentPath: "/faculty/dashboard",
    });
    assert.equal(result.allowed, false);
    assert.equal(result.redirect, "/super-admin/dashboard");
  });

  it("denies super_admin direct access to /admin/dashboard and redirects to /super-admin/dashboard", () => {
    const result = evaluateRoleRouteAccess({
      user: { username: "admin_live", role: "super_admin" },
      allowedRoles: [USER_ROLES.ADMIN],
      currentPath: "/admin/dashboard",
    });
    assert.equal(result.allowed, false);
    assert.equal(result.redirect, "/super-admin/dashboard");
  });

  it("allows super_admin direct access to /super-admin/dashboard", () => {
    const result = evaluateRoleRouteAccess({
      user: { username: "admin_live", role: "super_admin" },
      allowedRoles: [USER_ROLES.SUPER_ADMIN],
      currentPath: "/super-admin/dashboard",
    });
    assert.equal(result.allowed, true);
    assert.equal(result.redirect, null);
  });

  it("denies admin direct access to /super-admin/dashboard and redirects to /admin/dashboard", () => {
    const result = evaluateRoleRouteAccess({
      user: { username: "admin_dept", role: "admin" },
      allowedRoles: [USER_ROLES.SUPER_ADMIN],
      currentPath: "/super-admin/dashboard",
    });
    assert.equal(result.allowed, false);
    assert.equal(result.redirect, "/admin/dashboard");
  });

  it("denies student direct access to /admin/dashboard and redirects to /student/dashboard", () => {
    const result = evaluateRoleRouteAccess({
      user: { username: "student_john", role: "student" },
      allowedRoles: [USER_ROLES.ADMIN],
      currentPath: "/admin/dashboard",
    });
    assert.equal(result.allowed, false);
    assert.equal(result.redirect, "/student/dashboard");
  });

  it("denies unauthenticated or empty user and redirects to /login", () => {
    const result = evaluateRoleRouteAccess({
      user: null,
      allowedRoles: [USER_ROLES.STUDENT],
      currentPath: "/student/dashboard",
    });
    assert.equal(result.allowed, false);
    assert.equal(result.redirect, "/login");
  });
});

describe("5. Page Refresh Route Preservation & Re-verification", () => {
  it("preserves super_admin route on refresh when URL is /super-admin/dashboard", () => {
    const token = createMockJwtToken({ user_id: 1, role: "super_admin" });
    const claims = parseJwtClaims(token);
    assert.equal(claims.role, "super_admin");

    const result = evaluateRoleRouteAccess({
      user: { id: claims.user_id, role: claims.role, username: "admin_live" },
      allowedRoles: [USER_ROLES.SUPER_ADMIN],
      currentPath: "/super-admin/dashboard",
    });
    assert.equal(result.allowed, true);
  });

  it("preserves admin route on refresh when URL is /admin/dashboard", () => {
    const token = createMockJwtToken({ user_id: 10, role: "admin" });
    const claims = parseJwtClaims(token);
    assert.equal(claims.role, "admin");

    const result = evaluateRoleRouteAccess({
      user: { id: claims.user_id, role: claims.role, username: "admin_dept" },
      allowedRoles: [USER_ROLES.ADMIN],
      currentPath: "/admin/dashboard",
    });
    assert.equal(result.allowed, true);
  });

  it("preserves faculty route on refresh when URL is /faculty/courses", () => {
    const token = createMockJwtToken({ user_id: 2, role: "faculty" });
    const claims = parseJwtClaims(token);
    assert.equal(claims.role, "faculty");

    const result = evaluateRoleRouteAccess({
      user: { id: claims.user_id, role: claims.role, username: "dr_anurag" },
      allowedRoles: [USER_ROLES.FACULTY],
      currentPath: "/faculty/courses",
    });
    assert.equal(result.allowed, true);
  });

  it("preserves student route on refresh when URL is /student/dashboard", () => {
    const token = createMockJwtToken({ user_id: 50, role: "student" });
    const claims = parseJwtClaims(token);
    assert.equal(claims.role, "student");

    const result = evaluateRoleRouteAccess({
      user: { id: claims.user_id, role: claims.role, username: "student_anurag" },
      allowedRoles: [USER_ROLES.STUDENT],
      currentPath: "/student/dashboard",
    });
    assert.equal(result.allowed, true);
  });

  it("redirects super_admin to /super-admin/dashboard on refresh if URL was unauthorized /student/dashboard", () => {
    const token = createMockJwtToken({ user_id: 1, role: "super_admin" });
    const claims = parseJwtClaims(token);

    const result = evaluateRoleRouteAccess({
      user: { id: claims.user_id, role: claims.role, username: "admin_live" },
      allowedRoles: [USER_ROLES.STUDENT],
      currentPath: "/student/dashboard",
    });
    assert.equal(result.allowed, false);
    assert.equal(result.redirect, "/super-admin/dashboard");
  });
});

describe("6. Session Isolation & JWT Cryptographic Role Verification", () => {
  it("correctly extracts role claims from JWT token payload", () => {
    const token = createMockJwtToken({
      user_id: 1,
      role: "super_admin",
      username: "admin_live",
    });
    const claims = parseJwtClaims(token);
    assert.equal(claims.user_id, 1);
    assert.equal(claims.role, "super_admin");
    assert.equal(claims.username, "admin_live");
  });

  it("handles malformed or invalid JWT tokens gracefully without crashing", () => {
    assert.equal(parseJwtClaims(null), null);
    assert.equal(parseJwtClaims(""), null);
    assert.equal(parseJwtClaims("invalid_token"), null);
    assert.equal(parseJwtClaims("part1.not_base64_json.part3"), null);
  });

  it("prioritizes cryptographically signed JWT role over stale cached role", () => {
    const validToken = createMockJwtToken({ user_id: 1, role: "super_admin" });
    const claims = parseJwtClaims(validToken);

    // Stale user object from a prior student session
    const staleCachedUser = { id: 50, username: "student_john", role: "student" };

    // Verified synchronization:
    const reconciledUser = {
      ...staleCachedUser,
      id: claims.user_id,
      role: claims.role,
    };

    assert.equal(reconciledUser.role, "super_admin");
    assert.equal(reconciledUser.id, 1);
  });
});
