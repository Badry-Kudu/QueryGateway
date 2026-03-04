import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import App from "./App";

// Stub the API modules so no real HTTP requests are made during tests.
vi.mock("@/lib/api", () => ({
  connectionsApi: {
    list: vi.fn().mockResolvedValue([]),
  },
  authMethodsApi: {
    list: vi.fn().mockResolvedValue([]),
  },
  getApiError: vi.fn((err: unknown) => String(err)),
}));

describe("App", () => {
  it("renders the dashboard page h1 heading", () => {
    render(<App />);
    // The <h1> on the DashboardPage (not the sidebar nav link)
    expect(screen.getByRole("heading", { name: "Dashboard", level: 1 })).toBeInTheDocument();
  });

  it("renders at least one connections link", () => {
    render(<App />);
    const links = screen.getAllByRole("link", { name: /connections/i });
    expect(links.length).toBeGreaterThan(0);
  });
});
