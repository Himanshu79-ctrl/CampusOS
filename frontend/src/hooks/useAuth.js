import { useContext } from "react";
import { AuthContext } from "@/context/AuthContext";

/**
 * Custom React hook to consume CampusOS Authentication Context
 * @returns {{
 *   user: Object|null,
 *   accessToken: string|null,
 *   isAuthenticated: boolean,
 *   isLoading: boolean,
 *   login: (username: string, password: string, rememberMe?: boolean) => Promise<Object>,
 *   logout: () => void,
 *   refreshAccessToken: () => Promise<string>
 * }}
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export default useAuth;
