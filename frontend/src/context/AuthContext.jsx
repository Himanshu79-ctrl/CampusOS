import React, { createContext, useState, useEffect, useCallback, useMemo } from "react";
import { authService } from "@/services/authService";
import { tokenStorage } from "@/services/tokenStorage";
import { parseJwtClaims } from "@/types";

export { parseJwtClaims };

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const cached = tokenStorage.getUser();
    const token = tokenStorage.getAccessToken();
    const claims = parseJwtClaims(token);
    if (claims?.role) {
      if (cached) {
        return { ...cached, role: claims.role };
      }
      return { id: claims.user_id, role: claims.role };
    }
    return cached;
  });
  const [accessToken, setAccessToken] = useState(() => tokenStorage.getAccessToken());
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    authService.logout();
    tokenStorage.clearAll();
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
        // Crucial: Clear any lingering stale storage or previous user state before new login
        tokenStorage.clearAll();

        // Step 1: Request JWT tokens
        const tokens = await authService.login({ username, password });
        const { access, refresh } = tokens;

        // Step 2: Extract verified cryptographic role directly from JWT access token
        const claims = parseJwtClaims(access);
        const tokenRole = claims?.role;

        // Step 3: Store tokens matching remember preference
        tokenStorage.setTokens(access, refresh, rememberMe);
        setAccessToken(access);

        // Step 4: Fetch verified user profile with the new token
        let profile;
        try {
          profile = await authService.getProfile(access);
          if (tokenRole) {
            profile.role = profile.role || tokenRole;
          }
        } catch (profileErr) {
          if (tokenRole) {
            profile = {
              id: claims?.user_id,
              username: username.trim(),
              role: tokenRole,
            };
          } else {
            throw profileErr;
          }
        }

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
        const claims = parseJwtClaims(storedToken);
        if (claims?.role) {
          profile.role = profile.role || claims.role;
        }
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
            const claims = parseJwtClaims(newAccessToken);
            if (claims?.role) {
              profile.role = profile.role || claims.role;
            }
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
          const claims = parseJwtClaims(storedToken);
          if (claims?.role && cachedUser) {
            cachedUser.role = claims.role;
          }
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
