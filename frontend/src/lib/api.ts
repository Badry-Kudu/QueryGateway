import axios from "axios";

import type {
  Connection,
  ConnectionCreate,
  ConnectionTestResult,
  ConnectionUpdate,
} from "@/types/connection";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

// ── Connections ────────────────────────────────────────────────────────────

export const connectionsApi = {
  list: (activeOnly = false): Promise<Connection[]> =>
    http
      .get<Connection[]>("/api/v1/admin/connections/", {
        params: { active_only: activeOnly },
      })
      .then((r) => r.data),

  get: (id: string): Promise<Connection> =>
    http.get<Connection>(`/api/v1/admin/connections/${id}`).then((r) => r.data),

  create: (payload: ConnectionCreate): Promise<Connection> =>
    http.post<Connection>("/api/v1/admin/connections/", payload).then((r) => r.data),

  update: (id: string, payload: ConnectionUpdate): Promise<Connection> =>
    http.put<Connection>(`/api/v1/admin/connections/${id}`, payload).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    http.delete(`/api/v1/admin/connections/${id}`).then(() => undefined),

  test: (id: string): Promise<ConnectionTestResult> =>
    http.post<ConnectionTestResult>(`/api/v1/admin/connections/${id}/test`).then((r) => r.data),
};

// ── Error helpers ──────────────────────────────────────────────────────────

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join("; ");
    }
    return error.message;
  }
  return String(error);
}
