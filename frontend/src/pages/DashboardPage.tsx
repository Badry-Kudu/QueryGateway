import { useQuery } from "@tanstack/react-query";
import { Database } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { connectionsApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";

export function DashboardPage() {
  const { data: connections = [] } = useQuery({
    queryKey: queryKeys.connections.list(false),
    queryFn: () => connectionsApi.list(false),
  });

  const active = connections.filter((c) => c.is_active).length;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-1 text-2xl font-bold">Dashboard</h1>
      <p className="mb-6 text-sm text-muted-foreground">System overview for DB2API-Exposure.</p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Connections card */}
        <div className="rounded-lg border bg-card p-5">
          <div className="mb-3 flex items-center gap-3">
            <div className="rounded-md bg-primary/10 p-2">
              <Database className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">Oracle Connections</p>
              <p className="text-xs text-muted-foreground">
                {active} active / {connections.length} total
              </p>
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/connections">Manage connections</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
