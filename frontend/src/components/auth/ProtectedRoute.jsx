import React from "react";
import { Navigate, useLocation, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { LoadingScreen } from "@/components/common/LoadingScreen";

/**
 * ProtectedRoute Guard
 * Ensures only authenticated users can access nested child routes.
 * Preserves the intended destination URL to redirect the user after login.
 */
export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingScreen message="Checking authorization..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children ? children : <Outlet />;
};

export default ProtectedRoute;
