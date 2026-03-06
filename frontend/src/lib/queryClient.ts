import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

// Query key factories — keep keys in one place to avoid typos.
export const queryKeys = {
  connections: {
    all: ["connections"] as const,
    list: (activeOnly: boolean) => ["connections", "list", activeOnly] as const,
    detail: (id: string) => ["connections", id] as const,
  },
  authMethods: {
    all: ["authMethods"] as const,
    list: (activeOnly: boolean) => ["authMethods", "list", activeOnly] as const,
    detail: (id: string) => ["authMethods", id] as const,
  },
  endpoints: {
    all: ["endpoints"] as const,
    list: (activeOnly: boolean) => ["endpoints", "list", activeOnly] as const,
    detail: (id: string) => ["endpoints", id] as const,
  },
  schedules: {
    all: ["schedules"] as const,
    list: (activeOnly: boolean) => ["schedules", "list", activeOnly] as const,
    detail: (id: string) => ["schedules", id] as const,
    jobRuns: (scheduleId?: string) => ["schedules", "jobRuns", scheduleId] as const,
    snapshots: (endpointId: string) => ["schedules", "snapshots", endpointId] as const,
  },
};
