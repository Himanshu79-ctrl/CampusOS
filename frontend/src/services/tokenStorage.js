/**
 * Token and Session Storage Management for CampusOS
 *
 * Implements strict, tab-isolated authentication using browser sessionStorage.
 * Every browser tab maintains its own independent session, tokens, and role.
 * Cross-tab shared storage (localStorage) is NEVER used for authentication
 * tokens, user profiles, or refresh tokens.
 */

const ACCESS_TOKEN_KEY = "campusos_access_token";
const REFRESH_TOKEN_KEY = "campusos_refresh_token";
const USER_KEY = "campusos_user";
const REMEMBER_KEY = "campusos_remember";

// Proactively purge legacy shared localStorage keys so historical data from
// previous shared-storage versions cannot bleed across or pollute browser tabs.
if (typeof window !== "undefined" && window.localStorage) {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(REMEMBER_KEY);
  } catch {
    // Ignore restricted sandbox or private browsing storage exceptions
  }
}

export const tokenStorage = {
  /**
   * Retrieves the access token strictly from the current tab's sessionStorage.
   * @returns {string|null}
   */
  getAccessToken: () => {
    try {
      if (typeof window === "undefined" || !window.sessionStorage) return null;
      return sessionStorage.getItem(ACCESS_TOKEN_KEY) || null;
    } catch {
      return null;
    }
  },

  /**
   * Retrieves the refresh token strictly from the current tab's sessionStorage.
   * @returns {string|null}
   */
  getRefreshToken: () => {
    try {
      if (typeof window === "undefined" || !window.sessionStorage) return null;
      return sessionStorage.getItem(REFRESH_TOKEN_KEY) || null;
    } catch {
      return null;
    }
  },

  /**
   * Stores access and refresh tokens strictly in the current tab's sessionStorage.
   * Never writes tokens to shared localStorage to guarantee cross-tab isolation.
   * @param {string} access - JWT access token
   * @param {string} refresh - JWT refresh token
   * @param {boolean} [remember=false] - Preserved for API compatibility
   */
  setTokens: (access, refresh, remember = false) => {
    try {
      if (typeof window === "undefined" || !window.sessionStorage) return;
      sessionStorage.setItem(ACCESS_TOKEN_KEY, access);
      if (refresh) {
        sessionStorage.setItem(REFRESH_TOKEN_KEY, refresh);
      }
      sessionStorage.setItem(REMEMBER_KEY, remember ? "true" : "false");
    } catch (err) {
      console.error("Failed to store tab auth tokens:", err);
    }
  },

  /**
   * Updates only the access token in the current tab's sessionStorage.
   * @param {string} access - Refreshed JWT access token
   */
  setAccessToken: (access) => {
    try {
      if (typeof window === "undefined" || !window.sessionStorage) return;
      sessionStorage.setItem(ACCESS_TOKEN_KEY, access);
    } catch (err) {
      console.error("Failed to update tab access token:", err);
    }
  },

  /**
   * Retrieves the cached user profile strictly from the current tab's sessionStorage.
   * @returns {Object|null}
   */
  getUser: () => {
    try {
      if (typeof window === "undefined" || !window.sessionStorage) return null;
      const sessionUser = sessionStorage.getItem(USER_KEY);
      return sessionUser ? JSON.parse(sessionUser) : null;
    } catch {
      return null;
    }
  },

  /**
   * Stores the user profile strictly in the current tab's sessionStorage.
   * Never writes user identity to shared localStorage.
   * @param {Object} user - User profile object
   * @param {boolean} [remember=false] - Preserved for API compatibility
   */
  setUser: (user, remember = false) => {
    try {
      if (typeof window === "undefined" || !window.sessionStorage) return;
      sessionStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch (err) {
      console.error("Failed to cache tab user profile:", err);
    }
  },

  /**
   * Clears all authentication tokens and cached user data for the current tab only.
   * Does NOT broadcast or delete other tabs' session storage.
   */
  clearAll: () => {
    try {
      if (typeof window === "undefined" || !window.sessionStorage) return;
      sessionStorage.removeItem(ACCESS_TOKEN_KEY);
      sessionStorage.removeItem(REFRESH_TOKEN_KEY);
      sessionStorage.removeItem(USER_KEY);
      sessionStorage.removeItem(REMEMBER_KEY);

      // Also ensure localStorage is clean
      if (window.localStorage) {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        localStorage.removeItem(REMEMBER_KEY);
      }
    } catch (err) {
      console.error("Failed to clear tab auth storage:", err);
    }
  },
};
