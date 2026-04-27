import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { AuthProvider, tokenStorage, useAuth } from "@/lib/auth";

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("AuthProvider / useAuth", () => {
  afterEach(() => {
    tokenStorage.clear();
  });

  it("starts unauthenticated when localStorage is empty", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
  });

  it("hydrates from localStorage on mount", () => {
    tokenStorage.write("preloaded-token");
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe("preloaded-token");
  });

  it("setToken persists to localStorage and flips isAuthenticated", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => result.current.setToken("new-token"));
    expect(result.current.token).toBe("new-token");
    expect(result.current.isAuthenticated).toBe(true);
    expect(tokenStorage.read()).toBe("new-token");
  });

  it("clearToken removes the token from storage and state", () => {
    tokenStorage.write("doomed");
    const { result } = renderHook(() => useAuth(), { wrapper });
    act(() => result.current.clearToken());
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(tokenStorage.read()).toBeNull();
  });

  it("syncs across tabs via the storage event", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(false);

    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: tokenStorage.key,
          newValue: "from-other-tab",
        }),
      );
    });

    expect(result.current.token).toBe("from-other-tab");
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("throws when used outside the provider", () => {
    // renderHook will surface the error; assert via spyOn-style pattern.
    expect(() => renderHook(() => useAuth())).toThrow(/AuthProvider/);
  });
});
