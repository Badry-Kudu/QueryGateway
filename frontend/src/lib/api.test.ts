import MockAdapter from "axios-mock-adapter";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { connectionsApi, http } from "@/lib/api";
import { tokenStorage } from "@/lib/auth";

const mock = new MockAdapter(http);

const originalAssign = window.location.assign;

beforeEach(() => {
  mock.reset();
  tokenStorage.clear();
  // jsdom's location.assign throws by default; replace with a spy.
  Object.defineProperty(window, "location", {
    configurable: true,
    value: {
      ...window.location,
      pathname: "/connections",
      assign: vi.fn(),
    },
  });
});

afterEach(() => {
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { ...window.location, assign: originalAssign, pathname: "/" },
  });
});

describe("axios interceptors", () => {
  it("attaches the stored bearer token to admin requests", async () => {
    tokenStorage.write("a-fresh-token");
    mock.onGet("/api/v1/admin/connections/").reply((config) => {
      expect(config.headers?.Authorization).toBe("Bearer a-fresh-token");
      return [200, []];
    });

    await connectionsApi.list();
    expect.assertions(1);
  });

  it("does not attach an Authorization header when no token is stored", async () => {
    mock.onGet("/api/v1/admin/connections/").reply((config) => {
      expect(config.headers?.Authorization).toBeUndefined();
      return [200, []];
    });

    await connectionsApi.list();
    expect.assertions(1);
  });

  it("clears the token and redirects to /login with ?from= on 401 from a protected endpoint", async () => {
    tokenStorage.write("about-to-expire");
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...window.location,
        pathname: "/endpoints",
        search: "?step=2",
        hash: "#preview",
        assign: vi.fn(),
      },
    });
    mock.onGet("/api/v1/admin/connections/").reply(401, { detail: "expired" });

    await expect(connectionsApi.list()).rejects.toBeDefined();
    expect(tokenStorage.read()).toBeNull();
    expect(window.location.assign).toHaveBeenCalledWith(
      `/login?from=${encodeURIComponent("/endpoints?step=2#preview")}`,
    );
  });

  it("does NOT clear the token or redirect on 401 from /api/v1/auth/login", async () => {
    tokenStorage.write("a-token-from-a-prior-session");
    mock.onPost("/api/v1/auth/login").reply(401, {
      detail: "Invalid username or password.",
    });

    await expect(
      http.post("/api/v1/auth/login", { username: "x", password: "y" }),
    ).rejects.toBeDefined();
    // Token preserved (the 401 is a wrong-password response, not a session
    // expiry); no forced redirect either.
    expect(tokenStorage.read()).toBe("a-token-from-a-prior-session");
    expect(window.location.assign).not.toHaveBeenCalled();
  });
});
