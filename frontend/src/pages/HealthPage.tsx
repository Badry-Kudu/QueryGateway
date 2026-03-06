import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle, RefreshCw, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getApiError, healthApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";
import type { HealthDashboard } from "@/types/setting";

function StatusIcon({ status }: { status: string }) {
  if (status === "ok" || status === "running")
    return <CheckCircle className="h-4 w-4 text-green-500" />;
  if (status === "degraded" || status === "stopped")
    return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
  return <XCircle className="h-4 w-4 text-red-500" />;
}

export function HealthPage() {
  const { data, isLoading, error, refetch } = useQuery<HealthDashboard>({
    queryKey: queryKeys.health.dashboard(),
    queryFn: () => healthApi.dashboard(),
    refetchInterval: 30_000,
  });

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">System Health</h1>
          <p className="text-sm text-muted-foreground">Real-time system status and diagnostics.</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Failed to load health data: {getApiError(error)}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : data ? (
        <div className="space-y-6">
          {/* Overall status */}
          <div className="flex items-center gap-3 rounded-lg border bg-card p-4">
            <StatusIcon status={data.overall} />
            <div>
              <p className="font-medium">
                Overall Status:{" "}
                <span className={data.overall === "ok" ? "text-green-600" : "text-yellow-600"}>
                  {data.overall.toUpperCase()}
                </span>
              </p>
              <p className="text-xs text-muted-foreground">Auto-refreshes every 30 seconds.</p>
            </div>
          </div>

          {/* Component health */}
          <div>
            <h2 className="mb-3 text-lg font-semibold">Components</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {/* Database */}
              <div className="rounded-lg border bg-card p-4">
                <div className="mb-1 flex items-center gap-2">
                  <StatusIcon status={data.components.database?.status ?? "unknown"} />
                  <p className="font-medium">Database</p>
                </div>
                <p className="text-xs text-muted-foreground">
                  {data.components.database?.status === "ok" ? "PostgreSQL connected" : "Error"}
                </p>
              </div>

              {/* Connections */}
              {data.components.connections && (
                <div className="rounded-lg border bg-card p-4">
                  <div className="mb-1 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <p className="font-medium">Connections</p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {data.components.connections.active} active /{" "}
                    {data.components.connections.total} total
                  </p>
                </div>
              )}

              {/* Endpoints */}
              {data.components.endpoints && (
                <div className="rounded-lg border bg-card p-4">
                  <div className="mb-1 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <p className="font-medium">Endpoints</p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {data.components.endpoints.active} active / {data.components.endpoints.total}{" "}
                    total
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Scheduler */}
          <div>
            <h2 className="mb-3 text-lg font-semibold">Scheduler</h2>
            <div className="rounded-lg border bg-card p-4">
              <div className="mb-2 flex items-center gap-2">
                <StatusIcon status={data.scheduler.status} />
                <p className="font-medium capitalize">{data.scheduler.status}</p>
              </div>
              <div className="flex gap-4 text-xs text-muted-foreground">
                {data.scheduler.job_count !== undefined && (
                  <span>Registered jobs: {data.scheduler.job_count}</span>
                )}
                {data.scheduler.active_schedules !== undefined && (
                  <span>Active schedules: {data.scheduler.active_schedules}</span>
                )}
              </div>
            </div>
          </div>

          {/* Recent jobs */}
          <div>
            <h2 className="mb-3 text-lg font-semibold">Job Runs (Last 24h)</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg border bg-card p-4 text-center">
                <p className="text-2xl font-bold">{data.recent_jobs.total_24h}</p>
                <p className="text-xs text-muted-foreground">Total</p>
              </div>
              <div className="rounded-lg border bg-card p-4 text-center">
                <p className="text-2xl font-bold text-green-600">{data.recent_jobs.success_24h}</p>
                <p className="text-xs text-muted-foreground">Success</p>
              </div>
              <div className="rounded-lg border bg-card p-4 text-center">
                <p className="text-2xl font-bold text-red-600">{data.recent_jobs.failed_24h}</p>
                <p className="text-xs text-muted-foreground">Failed</p>
              </div>
              <div className="rounded-lg border bg-card p-4 text-center">
                <p className="text-2xl font-bold">
                  {data.recent_jobs.success_rate !== null
                    ? `${data.recent_jobs.success_rate}%`
                    : "—"}
                </p>
                <p className="text-xs text-muted-foreground">Success Rate</p>
              </div>
            </div>
          </div>

          {/* Stale snapshots */}
          {data.stale_snapshots.length > 0 && (
            <div>
              <h2 className="mb-3 text-lg font-semibold">Stale Snapshots</h2>
              <div className="rounded-lg border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="px-4 py-2 text-left font-medium">Endpoint</th>
                      <th className="px-4 py-2 text-left font-medium">Reason</th>
                      <th className="px-4 py-2 text-left font-medium">Age</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.stale_snapshots.map((s) => (
                      <tr key={s.endpoint_id} className="border-b last:border-0">
                        <td className="px-4 py-2 font-medium">{s.endpoint_name}</td>
                        <td className="px-4 py-2">
                          <Badge variant={s.reason === "no_snapshot" ? "destructive" : "outline"}>
                            {s.reason === "no_snapshot" ? "No snapshot" : "Stale"}
                          </Badge>
                        </td>
                        <td className="px-4 py-2 text-muted-foreground">
                          {s.last_snapshot_age_hours
                            ? `${s.last_snapshot_age_hours}h (threshold: ${s.threshold_hours}h)`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
