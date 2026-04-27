import { LogIn } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi, getApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface LocationState {
  from?: { pathname?: string; search?: string; hash?: string };
}

function resolveRedirectTarget(state: LocationState | null, searchParams: URLSearchParams): string {
  // RequireAuth (route guard) sets state.from to the full Location, so we
  // can preserve query string and hash. The axios 401 interceptor uses a
  // ?from= query param fallback because it has no React Router context to
  // pass state through.
  const fromState = state?.from;
  if (fromState?.pathname) {
    return `${fromState.pathname}${fromState.search ?? ""}${fromState.hash ?? ""}`;
  }

  const fromQuery = searchParams.get("from");
  if (fromQuery) {
    // Disallow off-site redirects (any external URL or protocol-relative).
    if (fromQuery.startsWith("/") && !fromQuery.startsWith("//")) {
      return fromQuery;
    }
  }
  return "/";
}

export function LoginPage() {
  const { isAuthenticated, setToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const target = resolveRedirectTarget(
    location.state as LocationState | null,
    new URLSearchParams(location.search),
  );

  // Already signed in (e.g. direct navigation to /login). Honour the
  // attempted-path hints so a deep link still works on a follow-up
  // visit.
  if (isAuthenticated) {
    return <Navigate to={target} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await authApi.login(username, password);
      setToken(response.access_token);
      navigate(target, { replace: true });
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/20 px-4">
      <div className="w-full max-w-sm rounded-lg border bg-background p-6 shadow-sm">
        <div className="mb-6">
          <h1 className="text-xl font-bold tracking-tight">QueryGateway</h1>
          <p className="mt-1 text-sm text-muted-foreground">Sign in to the admin console.</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={submitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={submitting}
            />
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Button type="submit" className="w-full gap-2" disabled={submitting}>
            <LogIn className="h-4 w-4" />
            {submitting ? "Signing in..." : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
}
