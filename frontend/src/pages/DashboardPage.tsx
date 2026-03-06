import { useQuery } from "@tanstack/react-query";
import { Activity, Clock, Cog, Database, Globe, Shield } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { authMethodsApi, connectionsApi, endpointsApi, healthApi, schedulesApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";

export function DashboardPage() {
  const { data: connections = [] } = useQuery({
    queryKey: queryKeys.connections.list(false),
    queryFn: () => connectionsApi.list(false),
  });

  const { data: authMethods = [] } = useQuery({
    queryKey: queryKeys.authMethods.list(false),
    queryFn: () => authMethodsApi.list(false),
  });

  const { data: endpoints = [] } = useQuery({
    queryKey: queryKeys.endpoints.list(false),
    queryFn: () => endpointsApi.list(false),
  });

  const { data: schedules = [] } = useQuery({
    queryKey: queryKeys.schedules.list(false),
    queryFn: () => schedulesApi.list(false),
  });

  const { data: health } = useQuery({
    queryKey: queryKeys.health.dashboard(),
    queryFn: () => healthApi.dashboard(),
  });

  const activeConns = connections.filter((c) => c.is_active).length;
  const activeAuth = authMethods.filter((a) => a.is_active).length;
  const activeEndpoints = endpoints.filter((e) => e.is_active).length;
  const activeSchedules = schedules.filter((s) => s.is_active).length;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-1 text-2xl font-bold">Dashboard</h1>
      <p className="mb-6 text-sm text-muted-foreground">System overview for DB2API-Exposure.</p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Connections card */}
        <div className="rounded-lg border bg-card p-5">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-md bg-primary/10 p-2">
              <Database className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">Oracle Connections</p>
              <p className="text-xs text-muted-foreground">
                {activeConns} active / {connections.length} total
              </p>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/connections">Manage connections</Link>
          </Button>
        </div>

        {/* Auth methods card */}
        <div className="rounded-lg border bg-card p-5">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-md bg-primary/10 p-2">
              <Shield className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">Auth Methods</p>
              <p className="text-xs text-muted-foreground">
                {activeAuth} active / {authMethods.length} total
              </p>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/auth">Manage auth</Link>
          </Button>
        </div>

        {/* Endpoints card */}
        <div className="rounded-lg border bg-card p-5">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-md bg-primary/10 p-2">
              <Globe className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">API Endpoints</p>
              <p className="text-xs text-muted-foreground">
                {activeEndpoints} active / {endpoints.length} total
              </p>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/endpoints">Manage endpoints</Link>
          </Button>
        </div>

        {/* Schedules card */}
        <div className="rounded-lg border bg-card p-5">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-md bg-primary/10 p-2">
              <Clock className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">Schedules</p>
              <p className="text-xs text-muted-foreground">
                {activeSchedules} active / {schedules.length} total
              </p>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/schedules">Manage schedules</Link>
          </Button>
        </div>

        {/* Settings card */}
        <div className="rounded-lg border bg-card p-5">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-md bg-primary/10 p-2">
              <Cog className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">Settings</p>
              <p className="text-xs text-muted-foreground">Application configuration</p>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/settings">Manage settings</Link>
          </Button>
        </div>

        {/* Health card */}
        <div className="rounded-lg border bg-card p-5">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-md bg-primary/10 p-2">
              <Activity className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">System Health</p>
              <p className="text-xs text-muted-foreground">
                {health ? health.overall.toUpperCase() : "—"}
              </p>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/health">View health</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
