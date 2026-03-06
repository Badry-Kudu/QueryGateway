import axios from "axios";

import type {
  Connection,
  ConnectionCreate,
  ConnectionTestResult,
  ConnectionUpdate,
} from "@/types/connection";
import type {
  ApiKeyIssuedResponse,
  AuthMethod,
  AuthMethodCreate,
  AuthMethodUpdate,
  RotateResponse,
  TokenIssuedResponse,
} from "@/types/auth_method";
import type {
  Endpoint,
  EndpointCreate,
  EndpointUpdate,
  SqlPreviewRequest,
  SqlPreviewResponse,
} from "@/types/endpoint";
import type {
  JobRun,
  Schedule,
  ScheduleCreate,
  ScheduleUpdate,
  SnapshotSummary,
} from "@/types/schedule";

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

// ── Auth Methods ───────────────────────────────────────────────────────────

export const authMethodsApi = {
  list: (activeOnly = false): Promise<AuthMethod[]> =>
    http
      .get<AuthMethod[]>("/api/v1/admin/auth/", { params: { active_only: activeOnly } })
      .then((r) => r.data),

  get: (id: string): Promise<AuthMethod> =>
    http.get<AuthMethod>(`/api/v1/admin/auth/${id}`).then((r) => r.data),

  create: (payload: AuthMethodCreate): Promise<AuthMethod> =>
    http.post<AuthMethod>("/api/v1/admin/auth/", payload).then((r) => r.data),

  createWithKey: (payload: AuthMethodCreate): Promise<ApiKeyIssuedResponse> =>
    http.post<ApiKeyIssuedResponse>("/api/v1/admin/auth/with-key", payload).then((r) => r.data),

  update: (id: string, payload: AuthMethodUpdate): Promise<AuthMethod> =>
    http.put<AuthMethod>(`/api/v1/admin/auth/${id}`, payload).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    http.delete(`/api/v1/admin/auth/${id}`).then(() => undefined),

  issueToken: (id: string): Promise<TokenIssuedResponse> =>
    http.post<TokenIssuedResponse>(`/api/v1/admin/auth/${id}/issue-token`).then((r) => r.data),

  rotate: (id: string): Promise<RotateResponse | ApiKeyIssuedResponse> =>
    http
      .post<RotateResponse | ApiKeyIssuedResponse>(`/api/v1/admin/auth/${id}/rotate`)
      .then((r) => r.data),
};

// ── Endpoints ─────────────────────────────────────────────────────────────

export const endpointsApi = {
  list: (activeOnly = false): Promise<Endpoint[]> =>
    http
      .get<Endpoint[]>("/api/v1/admin/endpoints/", { params: { active_only: activeOnly } })
      .then((r) => r.data),

  get: (id: string): Promise<Endpoint> =>
    http.get<Endpoint>(`/api/v1/admin/endpoints/${id}`).then((r) => r.data),

  create: (payload: EndpointCreate): Promise<Endpoint> =>
    http.post<Endpoint>("/api/v1/admin/endpoints/", payload).then((r) => r.data),

  update: (id: string, payload: EndpointUpdate): Promise<Endpoint> =>
    http.put<Endpoint>(`/api/v1/admin/endpoints/${id}`, payload).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    http.delete(`/api/v1/admin/endpoints/${id}`).then(() => undefined),

  preview: (payload: SqlPreviewRequest): Promise<SqlPreviewResponse> =>
    http.post<SqlPreviewResponse>("/api/v1/admin/endpoints/preview", payload).then((r) => r.data),
};

// ── Schedules ─────────────────────────────────────────────────────────────

export const schedulesApi = {
  list: (activeOnly = false): Promise<Schedule[]> =>
    http
      .get<Schedule[]>("/api/v1/admin/schedules/", { params: { active_only: activeOnly } })
      .then((r) => r.data),

  get: (id: string): Promise<Schedule> =>
    http.get<Schedule>(`/api/v1/admin/schedules/${id}`).then((r) => r.data),

  create: (payload: ScheduleCreate): Promise<Schedule> =>
    http.post<Schedule>("/api/v1/admin/schedules/", payload).then((r) => r.data),

  update: (id: string, payload: ScheduleUpdate): Promise<Schedule> =>
    http.put<Schedule>(`/api/v1/admin/schedules/${id}`, payload).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    http.delete(`/api/v1/admin/schedules/${id}`).then(() => undefined),

  runNow: (id: string): Promise<{ status: string }> =>
    http.post<{ status: string }>(`/api/v1/admin/schedules/${id}/run`).then((r) => r.data),

  pause: (id: string): Promise<Schedule> =>
    http.post<Schedule>(`/api/v1/admin/schedules/${id}/pause`).then((r) => r.data),

  resume: (id: string): Promise<Schedule> =>
    http.post<Schedule>(`/api/v1/admin/schedules/${id}/resume`).then((r) => r.data),

  listJobRuns: (params?: {
    schedule_id?: string;
    endpoint_id?: string;
    limit?: number;
  }): Promise<JobRun[]> =>
    http.get<JobRun[]>("/api/v1/admin/schedules/jobs/", { params }).then((r) => r.data),

  listSnapshots: (endpointId: string, limit = 10): Promise<SnapshotSummary[]> =>
    http
      .get<SnapshotSummary[]>(`/api/v1/admin/schedules/snapshots/${endpointId}`, {
        params: { limit },
      })
      .then((r) => r.data),
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
