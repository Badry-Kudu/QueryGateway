/**
 * Admin auth context.
 *
 * Token storage: localStorage. The trade-off is XSS vs CSRF posture —
 * localStorage avoids CSRF entirely (no cookie auto-attached) but is
 * readable by any script that runs on the page. We're protected from
 * XSS by:
 *   - React's default JSX escaping
 *   - shadcn primitives that don't render arbitrary HTML
 *   - no use of dangerouslySetInnerHTML in this app
 *   - no CSP-evading inline scripts
 * The token TTL is short (60 minutes by default; see backend
 * jwt_access_token_expire_minutes), which limits the blast radius if a
 * token is exfiltrated. If a future change introduces user-supplied
 * HTML rendering, revisit and switch to an httpOnly cookie + CSRF token.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const TOKEN_STORAGE_KEY = "querygateway.admin_token";

interface AuthContextValue {
  token: string | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  clearToken: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    // localStorage can throw in some sandboxed environments (private mode,
    // disabled storage). Treat as "not logged in" rather than crashing.
    return null;
  }
}

function writeStoredToken(token: string | null): void {
  try {
    if (token === null) {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    } else {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    }
  } catch {
    // ignore — see readStoredToken comment
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => readStoredToken());

  const setToken = useCallback((next: string) => {
    writeStoredToken(next);
    setTokenState(next);
  }, []);

  const clearToken = useCallback(() => {
    writeStoredToken(null);
    setTokenState(null);
  }, []);

  // Sync token across browser tabs.  When the user logs out in one tab
  // every other tab should immediately fall back to the login screen.
  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key !== TOKEN_STORAGE_KEY) return;
      setTokenState(event.newValue);
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      isAuthenticated: token !== null,
      setToken,
      clearToken,
    }),
    [token, setToken, clearToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}

// Exported for tests and for the axios interceptor (which can't depend on
// React context but needs to read/clear the same value).
// eslint-disable-next-line react-refresh/only-export-components
export const tokenStorage = {
  read: readStoredToken,
  write: writeStoredToken,
  clear: () => writeStoredToken(null),
  key: TOKEN_STORAGE_KEY,
};
