import React from "react";
import { Navigate, useLocation, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { getDashboardForRole } from "@/types";
import { LoadingScreen } from "@/components/common/LoadingScreen";

/**
 * RoleBasedRoute Guard
 * Verifies that the authenticated user possesses one of the allowed roles.
 * Redirects unauthorized users to their designated role dashboard.
 */
export const RoleBasedRoute = ({ allowedRoles = [], children }) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingScreen message="Verifying role permissions..." />;
  }

  if (!isAuthenticated || !user || !user.role) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const userRole = user.role;
  const hasPermission =
    Array.isArray(allowedRoles) &&
    allowedRoles.length > 0 &&
    allowedRoles.includes(userRole);

  if (!hasPermission) {
    // Redirect unauthorized user to their designated role dashboard
    const redirectPath = getDashboardForRole(userRole);
    // Guard against potential redirect loop if already on target path
    if (location.pathname === redirectPath) {
      return <Navigate to="/" replace />;
    }
    return <Navigate to={redirectPath} replace />;
  }

  return children ? children : <Outlet />;
};

export default RoleBasedRoute;
