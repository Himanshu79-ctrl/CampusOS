import { lmsClient, adminClient, authClient } from "./api.js";

/**
 * Normalizes backend error messages into user-friendly strings.
 * @param {Error} err
 * @returns {string}
 */
export const formatApiError = (err) => {
  if (!err) return "An unknown error occurred.";
  if (!err.response) {
    return err.message || "Network error. Please verify service connectivity.";
  }

  const { status, data } = err.response;

  if (status === 403) {
    return data?.detail || "You do not have permission to perform this action.";
  }
  if (status === 404) {
    return data?.message || data?.detail || "The requested resource was not found.";
  }
  if (status === 400 || status === 409) {
    if (data?.message) return data.message;
    if (data?.detail) return data.detail;
    if (typeof data === "object") {
      const msgs = Object.entries(data)
        .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(" ") : val}`)
        .join(" | ");
      if (msgs) return msgs;
    }
  }
  if (status >= 500) {
    return data?.message || "Internal server error. Please try again later.";
  }
  return data?.message || data?.detail || "Request failed with status " + status;
};

// =============================================================================
// 1. Department API (Admin Service - Port 5000)
// =============================================================================
export const departmentApi = {
  getAll: async () => {
    const res = await adminClient.get("/api/admin/departments");
    return res.data?.data || [];
  },
  getById: async (id) => {
    const res = await adminClient.get(`/api/admin/departments/${id}`);
    return res.data?.data || res.data;
  },
  create: async (data) => {
    const res = await adminClient.post("/api/admin/departments", data);
    return res.data;
  },
  update: async (id, data) => {
    const res = await adminClient.put(`/api/admin/departments/${id}`, data);
    return res.data;
  },
  delete: async (id) => {
    const res = await adminClient.delete(`/api/admin/departments/${id}`);
    return res.data;
  },
  assignHOD: async (id, facultyId) => {
    const res = await adminClient.put(`/api/admin/departments/${id}/hod`, { facultyId });
    return res.data;
  },
  removeHOD: async (id) => {
    const res = await adminClient.delete(`/api/admin/departments/${id}/hod`);
    return res.data;
  },
};

// =============================================================================
// 2. Faculty API (Admin Service - Port 5000)
// =============================================================================
export const facultyApi = {
  getAll: async () => {
    const res = await adminClient.get("/api/admin/faculty");
    return res.data?.data || [];
  },
  getById: async (id) => {
    const res = await adminClient.get(`/api/admin/faculty/${id}`);
    return res.data?.data || res.data;
  },
  create: async (data) => {
    const res = await adminClient.post("/api/admin/faculty", data);
    return res.data;
  },
  update: async (id, data) => {
    const res = await adminClient.put(`/api/admin/faculty/${id}`, data);
    return res.data;
  },
  deactivate: async (id) => {
    const res = await adminClient.delete(`/api/admin/faculty/${id}`);
    return res.data;
  },
  provision: async (id, data = {}) => {
    const res = await adminClient.post(`/api/admin/faculty/${id}/provision`, data);
    return res.data;
  },
};

// =============================================================================
// 3. Courses API (Admin Service - Port 5000)
// =============================================================================
export const courseApi = {
  getAll: async () => {
    const res = await adminClient.get("/api/admin/courses");
    return Array.isArray(res.data) ? res.data : res.data?.data || [];
  },
  getById: async (id) => {
    const res = await adminClient.get(`/api/admin/courses/${id}`);
    return res.data?.course || res.data;
  },
  create: async (data) => {
    const res = await adminClient.post("/api/admin/courses", data);
    return res.data;
  },
  update: async (id, data) => {
    const res = await adminClient.put(`/api/admin/courses/${id}`, data);
    return res.data;
  },
  delete: async (id) => {
    const res = await adminClient.delete(`/api/admin/courses/${id}`);
    return res.data;
  },
};

// =============================================================================
// 4. Academic Terms API (LMS Service - Port 8000)
// =============================================================================
export const termApi = {
  getAll: async (params = {}) => {
    const res = await lmsClient.get("/api/academics/terms/", { params });
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  getCurrent: async () => {
    try {
      const res = await lmsClient.get("/api/academics/terms/current/");
      return res.data;
    } catch {
      return null;
    }
  },
  getById: async (id) => {
    const res = await lmsClient.get(`/api/academics/terms/${id}/`);
    return res.data;
  },
  create: async (data) => {
    const res = await lmsClient.post("/api/academics/terms/", data);
    return res.data;
  },
  update: async (id, data) => {
    const res = await lmsClient.patch(`/api/academics/terms/${id}/`, data);
    return res.data;
  },
  activate: async (id) => {
    const res = await lmsClient.post(`/api/academics/terms/${id}/activate/`);
    return res.data;
  },
  complete: async (id) => {
    const res = await lmsClient.post(`/api/academics/terms/${id}/complete/`);
    return res.data;
  },
  setEnrollmentWindow: async (id, isOpen) => {
    const res = await lmsClient.post(`/api/academics/terms/${id}/enrollment-window/`, {
      is_open: isOpen,
    });
    return res.data;
  },
};

// =============================================================================
// 5. Course Offerings API (LMS Service - Port 8000)
// =============================================================================
export const offeringApi = {
  getAll: async (params = {}) => {
    const res = await lmsClient.get("/api/academics/offerings/", { params });
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  getById: async (id) => {
    const res = await lmsClient.get(`/api/academics/offerings/${id}/`);
    return res.data;
  },
  create: async (data) => {
    const res = await lmsClient.post("/api/academics/offerings/", data);
    return res.data;
  },
  update: async (id, data) => {
    const res = await lmsClient.patch(`/api/academics/offerings/${id}/`, data);
    return res.data;
  },
  getRoster: async (id, params = {}) => {
    const res = await lmsClient.get(`/api/academics/offerings/${id}/students/`, { params });
    return res.data;
  },
  enrollStudent: async (id, studentId) => {
    const res = await lmsClient.post(`/api/academics/offerings/${id}/enroll/`, {
      student_id: studentId,
    });
    return res.data;
  },
  dropStudent: async (id, studentId, reason) => {
    const res = await lmsClient.post(`/api/academics/offerings/${id}/drop/`, {
      student_id: studentId,
      reason,
    });
    return res.data;
  },
};

// =============================================================================
// 6. Student Management API (LMS Service - Port 8000)
// =============================================================================
export const studentAdminApi = {
  getAll: async (params = {}) => {
    const res = await lmsClient.get("/api/admin/reports/students/", { params });
    return res.data;
  },
  createProfile: async (data) => {
    const res = await lmsClient.post("/api/students/profile/", data);
    return res.data;
  },
  unifiedProvision: async (data) => {
    const res = await lmsClient.post("/api/students/unified-provision/", data);
    return res.data;
  },
  getById: async (id) => {
    const res = await lmsClient.get(`/api/students/profile/${id}/`);
    return res.data;
  },
  update: async (id, data) => {
    const res = await lmsClient.patch(`/api/students/profile/${id}/`, data);
    return res.data;
  },
};

// =============================================================================
// 6b. Password Setup API (Auth Service - Port 8001)
// =============================================================================
export const passwordSetupApi = {
  verify: async (uid, token) => {
    const res = await authClient.get("/api/password-setup/verify/", {
      params: { uid, token },
    });
    return res.data;
  },
  confirm: async (uid, token, newPassword) => {
    const res = await authClient.post("/api/password-setup/confirm/", {
      uid,
      token,
      new_password: newPassword,
    });
    return res.data;
  },
};

// =============================================================================
// 6c. User Management API (Auth Service - Port 8001)
// =============================================================================
export const userAdminApi = {
  getAll: async (params = {}) => {
    const res = await authClient.get("/api/users/", { params });
    return res.data;
  },
};

// =============================================================================
// 7. Reports & Analytics API (LMS Service - Port 8000)
// =============================================================================
export const reportsApi = {
  getOverview: async (params = {}) => {
    const res = await lmsClient.get("/api/admin/reports/overview/", { params });
    return res.data;
  },
  getAttendance: async (params = {}) => {
    const res = await lmsClient.get("/api/reports/attendance/", { params });
    return res.data;
  },
  exportData: async (type, format = "csv", filterParams = {}) => {
    const params = { type, format, ...filterParams };
    const res = await lmsClient.get("/api/reports/export/", {
      params,
      responseType: "blob",
    });

    // Generate download link in browser
    const blob = new Blob([res.data], {
      type: format === "json" ? "application/json" : "text/csv",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `campusos_${type}_export.${format}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};

// =============================================================================
// 8. Announcements API (LMS Service - Port 8000)
// =============================================================================
export const announcementsApi = {
  getAll: async (params = {}) => {
    const res = await lmsClient.get("/api/notifications/announcements/", { params });
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  getById: async (id) => {
    const res = await lmsClient.get(`/api/notifications/announcements/${id}/`);
    return res.data;
  },
  create: async (data) => {
    const res = await lmsClient.post("/api/notifications/announcements/", data);
    return res.data;
  },
  update: async (id, data) => {
    const res = await lmsClient.patch(`/api/notifications/announcements/${id}/`, data);
    return res.data;
  },
  togglePublish: async (id, isPublished) => {
    const res = await lmsClient.post(`/api/notifications/announcements/${id}/publish/`, {
      is_published: isPublished,
    });
    return res.data;
  },
  delete: async (id) => {
    const res = await lmsClient.delete(`/api/notifications/announcements/${id}/`);
    return res.data;
  },
};
