import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { tokenStorage } from "@/lib/auth";

import App from "./App";

// Stub the API modules so no real HTTP requests are made during tests.
vi.mock("@/lib/api", () => ({
  connectionsApi: {
    list: vi.fn().mockResolvedValue([]),
  },
  authMethodsApi: {
    list: vi.fn().mockResolvedValue([]),
  },
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
  },
  getApiError: vi.fn((err: unknown) => String(err)),
}));

describe("App", () => {
  beforeEach(() => {
    // Authenticated by default for the dashboard tests below.
    tokenStorage.write("test-token");
  });

  afterEach(() => {
    tokenStorage.clear();
  });

  it("renders the dashboard page h1 heading when authenticated", () => {
    render(<App />);
    // The <h1> on the DashboardPage (not the sidebar nav link)
    expect(screen.getByRole("heading", { name: "Dashboard", level: 1 })).toBeInTheDocument();
  });

  it("renders at least one connections link when authenticated", () => {
    render(<App />);
    const links = screen.getAllByRole("link", { name: /connections/i });
    expect(links.length).toBeGreaterThan(0);
  });

  it("redirects to the login page when no token is present", () => {
    tokenStorage.clear();
    render(<App />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });
});
