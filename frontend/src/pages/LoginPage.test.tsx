import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, tokenStorage } from "@/lib/auth";

const loginMock = vi.fn();

vi.mock("@/lib/api", () => ({
  authApi: {
    login: (...args: unknown[]) => loginMock(...args),
    me: vi.fn(),
  },
  getApiError: (err: unknown) => {
    if (err && typeof err === "object" && "message" in err) {
      return String((err as { message: unknown }).message);
    }
    return String(err);
  },
}));

// Imported AFTER the mock so it picks up the mocked authApi.
const { LoginPage } = await import("@/pages/LoginPage");

function renderLogin(
  initialEntries: Array<string | { pathname: string; state?: unknown }> = ["/login"],
) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>Dashboard Home</div>} />
          <Route path="/secret" element={<div>Secret Page</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    loginMock.mockReset();
    tokenStorage.clear();
  });

  afterEach(() => {
    tokenStorage.clear();
  });

  it("submits credentials, persists the token, and navigates home on success", async () => {
    loginMock.mockResolvedValueOnce({
      access_token: "minted-jwt",
      token_type: "bearer",
      expires_at: "2026-01-01T00:00:00Z",
    });

    renderLogin();

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "hunter2" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(loginMock).toHaveBeenCalledWith("admin", "hunter2"));
    await waitFor(() => expect(tokenStorage.read()).toBe("minted-jwt"));
    expect(await screen.findByText("Dashboard Home")).toBeInTheDocument();
  });

  it("surfaces server error detail without persisting a token", async () => {
    loginMock.mockRejectedValueOnce({ message: "Invalid username or password." });

    renderLogin();

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/Invalid username or password/i)).toBeInTheDocument();
    expect(tokenStorage.read()).toBeNull();
  });
});
