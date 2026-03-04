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
};
