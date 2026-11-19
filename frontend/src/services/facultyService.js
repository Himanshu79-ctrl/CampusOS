import { lmsClient } from "./api";

// Format API errors
export const formatApiError = (err) => {
  if (err?.response?.data) {
    const data = err.response.data;
    if (typeof data === "string") return data;
    if (data.detail) return data.detail;
    if (data.message) return data.message;
    if (data.error) return data.error;

    // Handle field-level validation errors
    if (typeof data === "object") {
      const messages = [];
      for (const [key, val] of Object.entries(data)) {
        if (Array.isArray(val)) {
          messages.push(`${key}: ${val.join(" ")}`);
        } else if (typeof val === "string") {
          messages.push(`${key}: ${val}`);
        } else if (typeof val === "object" && val !== null) {
          messages.push(`${key}: ${JSON.stringify(val)}`);
        }
      }
      if (messages.length > 0) return messages.join(" | ");
    }
  }
  return err.message || "An unexpected network or service error occurred.";
};

// =============================================================================
// 1. Faculty Courses & Offerings API
// =============================================================================
export const facultyCourseApi = {
  getMyOfferings: async (facultyId) => {
    const params = facultyId ? { faculty: facultyId } : {};
    const res = await lmsClient.get("/api/academics/offerings/", { params });
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  getOfferingDetail: async (offeringId) => {
    const res = await lmsClient.get(`/api/academics/offerings/${offeringId}/`);
    return res.data;
  },
  getRoster: async (offeringId, params = {}) => {
    const res = await lmsClient.get(`/api/academics/offerings/${offeringId}/students/`, { params });
    return res.data;
  },
};

// =============================================================================
// 2. Course Content & Modules API (apps.learning)
// =============================================================================
export const facultyContentApi = {
  getModules: async (offeringId) => {
    const res = await lmsClient.get(`/api/learning/offerings/${offeringId}/modules/`);
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  createModule: async (offeringId, data) => {
    const res = await lmsClient.post(`/api/learning/offerings/${offeringId}/modules/`, data);
    return res.data;
  },
  updateModule: async (moduleId, data) => {
    const res = await lmsClient.patch(`/api/learning/modules/${moduleId}/`, data);
    return res.data;
  },
  deleteModule: async (moduleId) => {
    const res = await lmsClient.delete(`/api/learning/modules/${moduleId}/`);
    return res.data;
  },
  toggleModulePublish: async (moduleId, isPublished, cascadeLessons = false) => {
    const res = await lmsClient.post(`/api/learning/modules/${moduleId}/publish/`, {
      is_published: isPublished,
      cascade_lessons: cascadeLessons,
    });
    return res.data;
  },
  // Lessons
  createLesson: async (moduleId, data) => {
    const res = await lmsClient.post(`/api/learning/modules/${moduleId}/lessons/`, data);
    return res.data;
  },
  getLessonDetail: async (lessonId) => {
    const res = await lmsClient.get(`/api/learning/lessons/${lessonId}/`);
    return res.data;
  },
  updateLesson: async (lessonId, data) => {
    const res = await lmsClient.patch(`/api/learning/lessons/${lessonId}/`, data);
    return res.data;
  },
  deleteLesson: async (lessonId) => {
    const res = await lmsClient.delete(`/api/learning/lessons/${lessonId}/`);
    return res.data;
  },
  toggleLessonPublish: async (lessonId, isPublished) => {
    const res = await lmsClient.post(`/api/learning/lessons/${lessonId}/publish/`, {
      is_published: isPublished,
    });
    return res.data;
  },
  // Resources
  createModuleResource: async (moduleId, data) => {
    const res = await lmsClient.post(`/api/learning/modules/${moduleId}/resources/`, data);
    return res.data;
  },
  deleteResource: async (resourceId) => {
    const res = await lmsClient.delete(`/api/learning/resources/${resourceId}/`);
    return res.data;
  },
};

// =============================================================================
// 3. Assignments & Grading API (apps.assignments)
// =============================================================================
export const facultyAssignmentApi = {
  getAssignments: async (offeringId) => {
    const res = await lmsClient.get(`/api/assignments/offerings/${offeringId}/`);
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  createAssignment: async (offeringId, data) => {
    const res = await lmsClient.post(`/api/assignments/offerings/${offeringId}/`, data);
    return res.data;
  },
  updateAssignment: async (assignmentId, data) => {
    const res = await lmsClient.patch(`/api/assignments/${assignmentId}/`, data);
    return res.data;
  },
  deleteAssignment: async (assignmentId) => {
    const res = await lmsClient.delete(`/api/assignments/${assignmentId}/`);
    return res.data;
  },
  togglePublish: async (assignmentId, isPublished) => {
    const res = await lmsClient.post(`/api/assignments/${assignmentId}/publish/`, {
      is_published: isPublished,
    });
    return res.data;
  },
  getSubmissions: async (assignmentId) => {
    const res = await lmsClient.get(`/api/assignments/${assignmentId}/submissions/`);
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  gradeSubmission: async (submissionId, data) => {
    const res = await lmsClient.post(`/api/assignments/submissions/${submissionId}/grade/`, data);
    return res.data;
  },
};

// =============================================================================
// 4. Attendance API (apps.attendance)
// =============================================================================
export const facultyAttendanceApi = {
  getSessions: async (offeringId) => {
    const res = await lmsClient.get(`/api/attendance/offerings/${offeringId}/sessions/`);
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  createSession: async (offeringId, data) => {
    const res = await lmsClient.post(`/api/attendance/offerings/${offeringId}/sessions/`, data);
    return res.data;
  },
  getSessionDetail: async (sessionId) => {
    const res = await lmsClient.get(`/api/attendance/sessions/${sessionId}/`);
    return res.data;
  },
  markAttendance: async (sessionId, records) => {
    const res = await lmsClient.post(`/api/attendance/sessions/${sessionId}/mark/`, { records });
    return res.data;
  },
  getCourseReport: async (offeringId) => {
    const res = await lmsClient.get(`/api/attendance/offerings/${offeringId}/report/`);
    return res.data;
  },
};

// =============================================================================
// 5. Timetable API (apps.timetable)
// =============================================================================
export const facultyTimetableApi = {
  getMyTimetable: async (params = {}) => {
    const res = await lmsClient.get("/api/timetable/faculty-timetable/", { params });
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  createEntry: async (offeringId, data) => {
    const res = await lmsClient.post(`/api/timetable/offerings/${offeringId}/`, data);
    return res.data;
  },
  updateEntry: async (entryId, data) => {
    const res = await lmsClient.patch(`/api/timetable/entries/${entryId}/`, data);
    return res.data;
  },
  deleteEntry: async (entryId) => {
    const res = await lmsClient.delete(`/api/timetable/entries/${entryId}/`);
    return res.data;
  },
};

// =============================================================================
// 6. Gradebook API (apps.grades)
// =============================================================================
export const facultyGradebookApi = {
  getGradeItems: async (offeringId) => {
    const res = await lmsClient.get(`/api/grades/offerings/${offeringId}/items/`);
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  createGradeItem: async (offeringId, data) => {
    const res = await lmsClient.post(`/api/grades/offerings/${offeringId}/items/`, data);
    return res.data;
  },
  updateGradeItem: async (itemId, data) => {
    const res = await lmsClient.patch(`/api/grades/items/${itemId}/`, data);
    return res.data;
  },
  deleteGradeItem: async (itemId) => {
    const res = await lmsClient.delete(`/api/grades/items/${itemId}/`);
    return res.data;
  },
  togglePublishItem: async (itemId, isPublished) => {
    const res = await lmsClient.post(`/api/grades/items/${itemId}/publish/`, {
      is_published: isPublished,
    });
    return res.data;
  },
  getGradebookMatrix: async (offeringId) => {
    const res = await lmsClient.get(`/api/grades/offerings/${offeringId}/gradebook/`);
    return res.data;
  },
  bulkEnterMarks: async (itemId, records) => {
    const res = await lmsClient.post(`/api/grades/items/${itemId}/marks/`, { records });
    return res.data;
  },
  syncAssignmentGrades: async (itemId) => {
    const res = await lmsClient.post(`/api/grades/items/${itemId}/sync-assignment/`);
    return res.data;
  },
};

// =============================================================================
// 7. Announcements API (Course scope)
// =============================================================================
export const facultyAnnouncementApi = {
  getCourseAnnouncements: async (offeringId) => {
    const res = await lmsClient.get("/api/notifications/announcements/", {
      params: { scope: "COURSE", course_offering: offeringId },
    });
    return Array.isArray(res.data) ? res.data : res.data?.results || [];
  },
  createAnnouncement: async (data) => {
    const res = await lmsClient.post("/api/notifications/announcements/", data);
    return res.data;
  },
  updateAnnouncement: async (id, data) => {
    const res = await lmsClient.patch(`/api/notifications/announcements/${id}/`, data);
    return res.data;
  },
  deleteAnnouncement: async (id) => {
    const res = await lmsClient.delete(`/api/notifications/announcements/${id}/`);
    return res.data;
  },
  togglePublish: async (id, isPublished) => {
    const res = await lmsClient.post(`/api/notifications/announcements/${id}/publish/`, {
      is_published: isPublished,
    });
    return res.data;
  },
};
