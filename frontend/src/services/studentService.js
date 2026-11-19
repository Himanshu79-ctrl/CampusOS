import { lmsClient } from "./api";
import { formatApiError } from "./facultyService";

export { formatApiError };

// =============================================================================
// 1. Student Courses & Profile API
// =============================================================================
export const studentCourseApi = {
  getMyEnrollments: async (params = {}) => {
    const res = await lmsClient.get("/api/students/profile/me/enrollments/", { params });
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  getMyProfile: async () => {
    const res = await lmsClient.get("/api/students/profile/me/");
    return res.data;
  },
};

// =============================================================================
// 2. Student Materials & Learning Content API
// =============================================================================
export const studentMaterialsApi = {
  getModules: async (offeringId) => {
    const res = await lmsClient.get(`/api/learning/offerings/${offeringId}/modules/`);
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  getLessonDetail: async (lessonId) => {
    const res = await lmsClient.get(`/api/learning/lessons/${lessonId}/`);
    return res.data;
  },
  markLessonProgress: async (lessonId, status = "COMPLETED") => {
    const res = await lmsClient.post(`/api/learning/lessons/${lessonId}/progress/`, { status });
    return res.data;
  },
};

// =============================================================================
// 3. Student Assignments & Submissions API
// =============================================================================
export const studentAssignmentApi = {
  getAssignments: async (offeringId) => {
    const res = await lmsClient.get(`/api/assignments/offerings/${offeringId}/`);
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  getMySubmission: async (assignmentId) => {
    try {
      const res = await lmsClient.get(`/api/assignments/${assignmentId}/my-submission/`);
      return res.data;
    } catch (err) {
      if (err?.response?.status === 404) return null;
      throw err;
    }
  },
  submitAssignment: async (assignmentId, data) => {
    const isFormData = typeof FormData !== "undefined" && data instanceof FormData;
    const res = await lmsClient.post(`/api/assignments/${assignmentId}/submit/`, data, {
      headers: isFormData ? { "Content-Type": "multipart/form-data" } : {},
    });
    return res.data;
  },
};

// =============================================================================
// 4. Student Attendance API
// =============================================================================
export const studentAttendanceApi = {
  getMySummary: async (params = {}) => {
    const res = await lmsClient.get("/api/attendance/my-summary/", { params });
    return res.data;
  },
  getMyHistory: async (params = {}) => {
    const res = await lmsClient.get("/api/attendance/my-history/", { params });
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
};

// =============================================================================
// 5. Student Timetable API
// =============================================================================
export const studentTimetableApi = {
  getMyTimetable: async (params = {}) => {
    const res = await lmsClient.get("/api/timetable/my-timetable/", { params });
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
};

// =============================================================================
// 6. Student Grades API
// =============================================================================
export const studentGradeApi = {
  getMyGrades: async (params = {}) => {
    const res = await lmsClient.get("/api/grades/my-grades/", { params });
    return res.data;
  },
};

// =============================================================================
// 7. Student Notifications & Announcements API
// =============================================================================
export const studentNotificationApi = {
  getNotifications: async () => {
    const res = await lmsClient.get("/api/notifications/");
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  getUnreadCount: async () => {
    try {
      const res = await lmsClient.get("/api/notifications/unread-count/");
      return res.data?.unread_count ?? 0;
    } catch {
      return 0;
    }
  },
  markAsRead: async (notificationId) => {
    const res = await lmsClient.post(`/api/notifications/${notificationId}/read/`);
    return res.data;
  },
  markAllAsRead: async () => {
    const res = await lmsClient.post("/api/notifications/mark-all-read/");
    return res.data;
  },
  getAnnouncements: async (params = {}) => {
    const res = await lmsClient.get("/api/notifications/announcements/", { params });
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
};
