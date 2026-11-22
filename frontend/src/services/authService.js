import { authClient } from "./api.js";
import { tokenStorage } from "./tokenStorage.js";

/**
 * Normalizes error responses from the Auth Service into user-friendly messages.
 * @param {Error} error
 * @returns {string} Readable message
 */
export const formatAuthError = (error) => {
  if (!error.response) {
    if (
      error.code === "ECONNABORTED" ||
      error.message?.toLowerCase().includes("timeout")
    ) {
      return "The authentication server took too long to respond while waking up. Please try signing in again.";
    }
    if (error.code === "ERR_NETWORK" || error.message?.includes("Network Error")) {
      return "Unable to reach CampusOS Authentication Service. Please verify that the Auth server is running and check your network.";
    }
    return error.message || "An unexpected network error occurred.";
  }

  const { status, data } = error.response;

  if (status === 401) {
    if (data?.detail === "No active account found with the given credentials") {
      return "Invalid username or password. Please verify your credentials and try again.";
    }
    return data?.detail || "Authentication failed. Invalid or expired session.";
  }

  if (status === 400) {
    if (data?.non_field_errors) {
      return Array.isArray(data.non_field_errors)
        ? data.non_field_errors.join(", ")
        : data.non_field_errors;
    }
    if (data?.username) {
      return `Username error: ${Array.isArray(data.username) ? data.username.join(", ") : data.username}`;
    }
    if (data?.password) {
      return `Password error: ${Array.isArray(data.password) ? data.password.join(", ") : data.password}`;
    }
    if (typeof data === "object") {
      const firstKey = Object.keys(data)[0];
      const val = data[firstKey];
      return `${firstKey}: ${Array.isArray(val) ? val.join(", ") : val}`;
    }
  }

  if (status >= 500) {
    return "CampusOS Authentication Service encountered an internal server error. Please try again later.";
  }

  return data?.detail || data?.message || "An unexpected authentication error occurred.";
};

/**
 * Authentication Service API Calls
 */
export const authService = {
  /**
   * Authenticate user with credentials via Django SimpleJWT
   * @param {Object} credentials - { username, password }
   * @returns {Promise<{ access: string, refresh: string }>}
   */
  login: async ({ username, password }) => {
    try {
      const response = await authClient.post(
        "/api/token/",
        {
          username: username.trim(),
          password,
        },
        { timeout: 45000 }
      );
      return response.data;
    } catch (error) {
      const friendlyMessage = formatAuthError(error);
      const enhancedError = new Error(friendlyMessage);
      enhancedError.original = error;
      enhancedError.code = error.code;
      enhancedError.status = error.response?.status;
      throw enhancedError;
    }
  },

  /**
   * Fetch authenticated user's profile from Django Auth Service
   * @param {string} [tokenOverride] - Optional token to use in header
   * @returns {Promise<{ id: number, username: string, email: string, role: string, first_name: string, last_name: string }>}
   */
  getProfile: async (tokenOverride) => {
    try {
      const headers = {};
      const token = tokenOverride || tokenStorage.getAccessToken();
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      const response = await authClient.get("/api/user/me/", {
        headers,
        timeout: 45000,
      });
      return response.data;
    } catch (error) {
      const friendlyMessage = formatAuthError(error);
      const enhancedError = new Error(friendlyMessage);
      enhancedError.original = error;
      enhancedError.code = error.code;
      enhancedError.status = error.response?.status;
      throw enhancedError;
    }
  },

  /**
   * Refresh the access token using SimpleJWT refresh endpoint
   * @param {string} [refreshToken] - Optional refresh token
   * @returns {Promise<{ access: string, refresh?: string }>}
   */
  refreshToken: async (refreshToken) => {
    const token = refreshToken || tokenStorage.getRefreshToken();
    if (!token) {
      throw new Error("No refresh token available.");
    }

    try {
      const response = await authClient.post(
        "/api/token/refresh/",
        {
          refresh: token,
        },
        { timeout: 45000 }
      );
      return response.data;
    } catch (error) {
      const friendlyMessage = formatAuthError(error);
      const enhancedError = new Error(friendlyMessage);
      enhancedError.original = error;
      enhancedError.code = error.code;
      enhancedError.status = error.response?.status;
      throw enhancedError;
    }
  },

  /**
   * Logout user by purging stored tokens and session state
   */
  logout: () => {
    tokenStorage.clearAll();
  },
};
