export interface Setting {
  key: string;
  value: string;
  description: string | null;
  is_secret: boolean;
  updated_at: string;
  updated_by: string | null;
}

export interface SettingUpdate {
  value: string;
}

export interface SettingBulkUpdate {
  settings: Record<string, string>;
}

export interface HealthDashboard {
  overall: "ok" | "degraded";
  components: {
    database?: { status: string; detail?: string };
    connections?: { total: number; active: number };
    endpoints?: { total: number; active: number };
  };
  scheduler: {
    status: string;
    job_count?: number;
    active_schedules?: number;
  };
  recent_jobs: {
    total_24h: number;
    success_24h: number;
    failed_24h: number;
    success_rate: number | null;
  };
  stale_snapshots: {
    endpoint_id: string;
    endpoint_name: string;
    reason: string;
    last_snapshot_age_hours?: number;
    threshold_hours?: number;
  }[];
}
