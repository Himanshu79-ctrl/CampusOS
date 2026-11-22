import axios from "axios";
import { tokenStorage } from "./tokenStorage.js";

/**
 * Backend Microservices Base URLs & Timeout Configuration
 * Configured per service to accommodate Render free-instance cold starts (15-30s).
 */
export const API_CONFIG = {
  lms: (typeof import.meta !== "undefined" && import.meta.env?.VITE_LMS_API_URL) || "http://127.0.0.1:8000",
  auth: (typeof import.meta !== "undefined" && import.meta.env?.VITE_AUTH_API_URL) || "http://127.0.0.1:8001",
  admin: (typeof import.meta !== "undefined" && import.meta.env?.VITE_ADMIN_API_URL) || "http://127.0.0.1:5000",
};

export const API_TIMEOUTS = {
  auth: 45000, // 45 seconds: Auth Service (accounts, JWT login, token refresh, password setup)
  lms: 30000,  // 30 seconds: LMS Service (academics, courses, timetable, gradebook)
  admin: 30000, // 30 seconds: Admin Service (departments, courses, faculty catalog)
};

/**
 * Dedicated Axios client for LMS service (Django REST Framework)
 * Modules: Academics, Learning Content, Assignments, Attendance, Timetable, Grades, Reports, Notifications.
 */
export const lmsClient = axios.create({
  baseURL: API_CONFIG.lms,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: API_TIMEOUTS.lms,
});

/**
 * Dedicated Axios client for Authentication service (Django)
 * Endpoints: /api/token/, /api/token/refresh/, /api/register/, /api/user/me/
 */
export const authClient = axios.create({
  baseURL: API_CONFIG.auth,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: API_TIMEOUTS.auth,
});

/**
 * Dedicated Axios client for Admin backend (Node.js/Express)
 * Endpoints: /api/admin/departments, /api/admin/courses, /api/admin/faculty
 */
export const adminClient = axios.create({
  baseURL: API_CONFIG.admin,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: API_TIMEOUTS.admin,
});

// Flag and queue to manage concurrent token refresh attempts
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

/**
 * Configures request and response interceptors for an Axios instance.
 * Automatically injects JWT Bearer tokens and handles 401 token refresh.
 * @param {import("axios").AxiosInstance} client
 */
const configureAuthInterceptors = (client) => {
  // Request Interceptor: Attach current access token if available
  client.interceptors.request.use(
    (config) => {
      const token = tokenStorage.getAccessToken();
      if (token && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Response Interceptor: Catch 401 and attempt automatic token refresh
  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;

      // Bypass refresh for login, refresh requests, or already-retried requests
      const isAuthEndpoint =
        originalRequest?.url?.includes("/api/token/") ||
        originalRequest?.url?.includes("/api/token/refresh/");

      if (
        !error.response ||
        error.response.status !== 401 ||
        originalRequest._retry ||
        isAuthEndpoint
      ) {
        return Promise.reject(error);
      }

      const refreshToken = tokenStorage.getRefreshToken();
      if (!refreshToken) {
        // No refresh token available; clean up and notify app
        tokenStorage.clearAll();
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("campusos:unauthorized"));
        }
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return client(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Call refresh endpoint directly using clean axios call to prevent recursion
        const refreshResponse = await axios.post(
          `${API_CONFIG.auth}/api/token/refresh/`,
          { refresh: refreshToken },
          {
            headers: { "Content-Type": "application/json" },
            timeout: API_TIMEOUTS.auth,
          }
        );

        const newAccessToken = refreshResponse.data.access;
        tokenStorage.setAccessToken(newAccessToken);

        processQueue(null, newAccessToken);

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return client(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        tokenStorage.clearAll();
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("campusos:unauthorized"));
        }
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }
  );
};

// Apply auth interceptors to all microservice clients
configureAuthInterceptors(lmsClient);
configureAuthInterceptors(authClient);
configureAuthInterceptors(adminClient);
