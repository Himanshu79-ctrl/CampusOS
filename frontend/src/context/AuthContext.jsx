import React, { createContext, useState, useEffect, useCallback, useMemo } from "react";
import { authService } from "@/services/authService";
import { tokenStorage } from "@/services/tokenStorage";

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => tokenStorage.getUser());
  const [accessToken, setAccessToken] = useState(() => tokenStorage.getAccessToken());
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
    setAccessToken(null);
  }, []);

  const refreshAccessToken = useCallback(async () => {
    try {
      const refreshToken = tokenStorage.getRefreshToken();
      if (!refreshToken) {
        throw new Error("No refresh token available");
      }
      const data = await authService.refreshToken(refreshToken);
      const newAccess = data.access;
      tokenStorage.setAccessToken(newAccess);
      setAccessToken(newAccess);
      return newAccess;
    } catch (err) {
      logout();
      throw err;
    }
  }, [logout]);

  /**
   * Performs user login via Auth Service
   * @param {string} username
   * @param {string} password
   * @param {boolean} rememberMe
   * @returns {Promise<Object>} user profile
   */
  const login = useCallback(
    async (username, password, rememberMe = true) => {
      setIsLoading(true);
      try {
        // Step 1: Request JWT tokens
        const tokens = await authService.login({ username, password });
        const { access, refresh } = tokens;

        // Step 2: Store tokens matching remember preference
        tokenStorage.setTokens(access, refresh, rememberMe);
        setAccessToken(access);

        // Step 3: Fetch verified user profile with the new token
        const profile = await authService.getProfile(access);
        tokenStorage.setUser(profile, rememberMe);
        setUser(profile);

        return profile;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  /**
   * Hydrates and verifies active session on application startup
   */
  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      const storedToken = tokenStorage.getAccessToken();
      const storedRefresh = tokenStorage.getRefreshToken();

      if (!storedToken && !storedRefresh) {
        if (isMounted) {
          setUser(null);
          setAccessToken(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        // Attempt to fetch profile using current access token
        const profile = await authService.getProfile(storedToken);
        if (isMounted) {
          setUser(profile);
          setAccessToken(storedToken);
          tokenStorage.setUser(profile);
        }
      } catch (err) {
        // If access token expired or invalid, attempt token refresh
        if (err.status === 401 && storedRefresh) {
          try {
            const refreshData = await authService.refreshToken(storedRefresh);
            const newAccessToken = refreshData.access;
            tokenStorage.setAccessToken(newAccessToken);

            const profile = await authService.getProfile(newAccessToken);
            if (isMounted) {
              setAccessToken(newAccessToken);
              setUser(profile);
              tokenStorage.setUser(profile);
            }
          } catch {
            if (isMounted) {
              tokenStorage.clearAll();
              setUser(null);
              setAccessToken(null);
            }
          }
        } else if (!err.response) {
          // Network error: preserve cached user so temporary offline state doesn't wipe session
          const cachedUser = tokenStorage.getUser();
          if (isMounted && cachedUser && storedToken) {
            setUser(cachedUser);
            setAccessToken(storedToken);
          }
        } else {
          if (isMounted) {
            tokenStorage.clearAll();
            setUser(null);
            setAccessToken(null);
          }
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    restoreSession();

    // Listen for unauthorized events emitted by interceptors
    const handleUnauthorizedEvent = () => {
      if (isMounted) {
        logout();
      }
    };

    if (typeof window !== "undefined") {
      window.addEventListener("campusos:unauthorized", handleUnauthorizedEvent);
    }

    return () => {
      isMounted = false;
      if (typeof window !== "undefined") {
        window.removeEventListener("campusos:unauthorized", handleUnauthorizedEvent);
      }
    };
  }, [logout]);

  const value = useMemo(
    () => ({
      user,
      accessToken,
      isAuthenticated: Boolean(user && accessToken),
      isLoading,
      login,
      logout,
      refreshAccessToken,
    }),
    [user, accessToken, isLoading, login, logout, refreshAccessToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
