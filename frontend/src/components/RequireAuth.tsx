import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/lib/auth";

/**
 * Route guard. Renders the child route when authenticated, otherwise
 * redirects to /login and remembers the attempted path so the user
 * lands back where they wanted after signing in.
 */
export function RequireAuth() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
