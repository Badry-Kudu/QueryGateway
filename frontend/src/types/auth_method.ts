export type AuthMethodType = "bearer" | "basic" | "api_key";

export interface AuthMethod {
  id: string;
  name: string;
  description: string | null;
  method_type: AuthMethodType;
  is_active: boolean;
  algorithm: string | null;
  expire_minutes: number | null;
  username: string | null;
  key_prefix: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthMethodCreate {
  name: string;
  description?: string | null;
  method_type: AuthMethodType;
  is_active?: boolean;
  // Bearer
  algorithm?: string;
  expire_minutes?: number;
  // Basic
  username?: string | null;
  password?: string | null;
  // API key
  key_prefix?: string;
}

export interface AuthMethodUpdate {
  name?: string | null;
  description?: string | null;
  is_active?: boolean | null;
  expire_minutes?: number | null;
  username?: string | null;
  password?: string | null;
}

export interface TokenIssuedResponse {
  token: string;
  token_type: string;
  expires_at: string;
  note: string;
}

export interface ApiKeyIssuedResponse {
  api_key: string;
  note: string;
}

export interface RotateResponse {
  message: string;
}
