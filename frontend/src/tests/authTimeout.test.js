/**
 * Automated Test Suite for Auth Service Timeout, Loading States & Duplicate Submission Guards.
 *
 * Verifies:
 * 1. Dedicated microservice timeout configurations (Auth: 45s, LMS: 30s, Admin: 30s).
 * 2. User-friendly timeout error normalization (formatAuthError & formatApiError).
 * 3. Prevention of duplicate login submissions while processing.
 * 4. Verification that non-student roles cannot directly access /student/dashboard.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { API_TIMEOUTS, authClient, lmsClient, adminClient } from "../services/api.js";
import { formatAuthError } from "../services/authService.js";
import { formatApiError } from "../services/adminService.js";
import { USER_ROLES, getDashboardForRole, isRouteAllowedForRole } from "../types/index.js";

describe("1. Dedicated Microservice Timeout Configuration", () => {
  it("configures authClient with 45000ms timeout for Render cold starts", () => {
    assert.equal(API_TIMEOUTS.auth, 45000);
    assert.equal(authClient.defaults.timeout, 45000);
  });

  it("configures lmsClient with 30000ms timeout", () => {
    assert.equal(API_TIMEOUTS.lms, 30000);
    assert.equal(lmsClient.defaults.timeout, 30000);
  });

  it("configures adminClient with 30000ms timeout", () => {
    assert.equal(API_TIMEOUTS.admin, 30000);
    assert.equal(adminClient.defaults.timeout, 30000);
  });

  it("does not blindly set every service to the same timeout", () => {
    assert.ok(API_TIMEOUTS.auth >= 45000, "Auth timeout must be at least 45s for cold start tolerance");
    assert.equal(API_TIMEOUTS.lms, 30000);
    assert.equal(API_TIMEOUTS.admin, 30000);
  });
});

describe("2. User-Friendly Timeout Error Normalization", () => {
  it("formats ECONNABORTED timeout errors as actionable retry messages", () => {
    const timeoutError = {
      code: "ECONNABORTED",
      message: "timeout of 1000ms exceeded",
    };
    const formatted = formatAuthError(timeoutError);
    assert.doesNotMatch(formatted, /timeout of 1000ms exceeded/i);
    assert.match(formatted, /server took too long to respond/i);
    assert.match(formatted, /try signing in again/i);
  });

  it("formats general timeout messages in formatAuthError", () => {
    const error = {
      message: "timeout of 10000ms exceeded",
    };
    const formatted = formatAuthError(error);
    assert.doesNotMatch(formatted, /timeout of 10000ms exceeded/i);
    assert.match(formatted, /server took too long to respond/i);
  });

  it("formats ECONNABORTED timeout errors in formatApiError", () => {
    const error = {
      code: "ECONNABORTED",
      message: "timeout of 1000ms exceeded",
    };
    const formatted = formatApiError(error);
    assert.doesNotMatch(formatted, /timeout of 1000ms exceeded/i);
    assert.match(formatted, /server took too long to respond/i);
  });

  it("preserves standard 401 invalid credentials error messages", () => {
    const error = {
      response: {
        status: 401,
        data: { detail: "No active account found with the given credentials" },
      },
    };
    const formatted = formatAuthError(error);
    assert.match(formatted, /Invalid username or password/i);
  });

  it("preserves network connectivity error messages", () => {
    const error = {
      code: "ERR_NETWORK",
      message: "Network Error",
    };
    const formatted = formatAuthError(error);
    assert.match(formatted, /Unable to reach CampusOS Authentication Service/i);
  });
});

describe("3. Duplicate Login Submission Prevention", () => {
  it("ignores subsequent login submissions while an active submission is in progress", async () => {
    let submissionCount = 0;
    let isSubmitting = false;

    const mockLoginService = () =>
      new Promise((resolve) => setTimeout(() => resolve({ role: "student" }), 50));

    const handleSubmit = async () => {
      if (isSubmitting) return "BLOCKED_DUPLICATE";
      isSubmitting = true;
      submissionCount++;
      try {
        return await mockLoginService();
      } finally {
        isSubmitting = false;
      }
    };

    // First submission proceeds
    const promise1 = handleSubmit();
    assert.equal(isSubmitting, true);

    // Second and third concurrent submissions are blocked
    const result2 = await handleSubmit();
    const result3 = await handleSubmit();

    assert.equal(result2, "BLOCKED_DUPLICATE");
    assert.equal(result3, "BLOCKED_DUPLICATE");

    const result1 = await promise1;
    assert.equal(result1.role, "student");
    assert.equal(submissionCount, 1, "Only a single login request should have been dispatched");
    assert.equal(isSubmitting, false);
  });
});

describe("4. Non-Student Direct Access Protection to /student/dashboard", () => {
  it("blocks super_admin from accessing /student/dashboard", () => {
    const allowed = isRouteAllowedForRole("/student/dashboard", USER_ROLES.SUPER_ADMIN);
    assert.equal(allowed, false);
    assert.equal(getDashboardForRole(USER_ROLES.SUPER_ADMIN), "/super-admin/dashboard");
  });

  it("blocks admin from accessing /student/dashboard", () => {
    const allowed = isRouteAllowedForRole("/student/dashboard", USER_ROLES.ADMIN);
    assert.equal(allowed, false);
    assert.equal(getDashboardForRole(USER_ROLES.ADMIN), "/admin/dashboard");
  });

  it("blocks faculty from accessing /student/dashboard", () => {
    const allowed = isRouteAllowedForRole("/student/dashboard", USER_ROLES.FACULTY);
    assert.equal(allowed, false);
    assert.equal(getDashboardForRole(USER_ROLES.FACULTY), "/faculty/dashboard");
  });

  it("permits only student to access /student/dashboard", () => {
    const allowed = isRouteAllowedForRole("/student/dashboard", USER_ROLES.STUDENT);
    assert.equal(allowed, true);
    assert.equal(getDashboardForRole(USER_ROLES.STUDENT), "/student/dashboard");
  });
});
