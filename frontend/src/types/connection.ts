export type OracleMode = "thin" | "thick";

export interface Connection {
  id: string;
  name: string;
  description: string | null;
  host: string;
  port: number;
  service_name: string | null;
  sid: string | null;
  username: string;
  has_password: boolean;
  pool_min: number;
  pool_max: number;
  pool_timeout: number;
  query_timeout: number;
  mode: OracleMode;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConnectionCreate {
  name: string;
  description?: string | null;
  host: string;
  port?: number;
  service_name?: string | null;
  sid?: string | null;
  username: string;
  password: string;
  pool_min?: number;
  pool_max?: number;
  pool_timeout?: number;
  query_timeout?: number;
  mode?: OracleMode;
  is_active?: boolean;
}

export interface ConnectionUpdate {
  name?: string;
  description?: string | null;
  host?: string;
  port?: number;
  service_name?: string | null;
  sid?: string | null;
  username?: string;
  password?: string;
  pool_min?: number;
  pool_max?: number;
  pool_timeout?: number;
  query_timeout?: number;
  mode?: OracleMode;
  is_active?: boolean;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  duration_ms: number | null;
  oracle_version: string | null;
}
