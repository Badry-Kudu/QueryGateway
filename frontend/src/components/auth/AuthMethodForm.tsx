import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type {
  AuthMethod,
  AuthMethodCreate,
  AuthMethodType,
  AuthMethodUpdate,
} from "@/types/auth_method";

type Mode = "create" | "edit";

interface AuthMethodFormProps {
  mode: Mode;
  initial?: AuthMethod;
  onSubmit: (data: AuthMethodCreate | AuthMethodUpdate) => void;
  onCancel: () => void;
  isLoading?: boolean;
  error?: string | null;
}

interface FormState {
  name: string;
  description: string;
  method_type: AuthMethodType;
  is_active: boolean;
  // Bearer
  algorithm: string;
  expire_minutes: string;
  // Basic
  username: string;
  password: string;
  // API key
  key_prefix: string;
}

function toFormState(auth?: AuthMethod): FormState {
  return {
    name: auth?.name ?? "",
    description: auth?.description ?? "",
    method_type: auth?.method_type ?? "bearer",
    is_active: auth?.is_active ?? true,
    algorithm: auth?.algorithm ?? "HS256",
    expire_minutes: String(auth?.expire_minutes ?? 60),
    username: auth?.username ?? "",
    password: "",
    key_prefix: auth?.key_prefix ?? "db2api_",
  };
}

export function AuthMethodForm({
  mode,
  initial,
  onSubmit,
  onCancel,
  isLoading = false,
  error,
}: AuthMethodFormProps) {
  const [form, setForm] = useState<FormState>(() => toFormState(initial));
  const [validationErrors, setValidationErrors] = useState<
    Partial<Record<keyof FormState, string>>
  >({});

  useEffect(() => {
    setForm(toFormState(initial));
    setValidationErrors({});
  }, [initial]);

  const set =
    (key: keyof FormState) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const value =
        e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value;
      setForm((prev) => ({ ...prev, [key]: value }));
      setValidationErrors((prev) => ({ ...prev, [key]: undefined }));
    };

  function validate(): boolean {
    const errs: Partial<Record<keyof FormState, string>> = {};
    if (!form.name.trim()) errs.name = "Name is required.";
    if (form.method_type === "basic") {
      if (!form.username.trim()) errs.username = "Username is required for Basic auth.";
      if (mode === "create" && !form.password) errs.password = "Password is required.";
    }
    if (form.method_type === "bearer") {
      const mins = Number(form.expire_minutes);
      if (isNaN(mins) || mins < 1 || mins > 525600)
        errs.expire_minutes = "Expiry must be 1–525600 minutes.";
    }
    setValidationErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    if (mode === "create") {
      const payload: AuthMethodCreate = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        method_type: form.method_type,
        is_active: form.is_active,
      };
      if (form.method_type === "bearer") {
        payload.algorithm = form.algorithm;
        payload.expire_minutes = Number(form.expire_minutes);
      }
      if (form.method_type === "basic") {
        payload.username = form.username.trim();
        payload.password = form.password;
      }
      if (form.method_type === "api_key") {
        payload.key_prefix = form.key_prefix;
      }
      onSubmit(payload);
    } else {
      const payload: AuthMethodUpdate = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        is_active: form.is_active,
      };
      if (form.method_type === "bearer") {
        payload.expire_minutes = Number(form.expire_minutes);
      }
      if (form.method_type === "basic") {
        if (form.username.trim()) payload.username = form.username.trim();
        if (form.password) payload.password = form.password;
      }
      onSubmit(payload);
    }
  }

  const field = (id: keyof FormState, label: string, input: React.ReactNode) => (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      {input}
      {validationErrors[id] && <p className="text-xs text-destructive">{validationErrors[id]}</p>}
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {field(
        "name",
        "Name *",
        <Input
          id="name"
          value={form.name}
          onChange={set("name")}
          placeholder="my-api-auth"
          disabled={isLoading}
        />,
      )}

      {field(
        "description",
        "Description",
        <Textarea
          id="description"
          value={form.description}
          onChange={set("description")}
          placeholder="Optional description"
          rows={2}
          disabled={isLoading}
        />,
      )}

      <div className="space-y-1">
        <Label htmlFor="method_type">Auth type *</Label>
        <Select
          id="method_type"
          value={form.method_type}
          onChange={set("method_type")}
          disabled={mode === "edit" || isLoading}
        >
          <option value="bearer">Bearer (JWT)</option>
          <option value="basic">Basic (username + password)</option>
          <option value="api_key">API Key</option>
        </Select>
      </div>

      {/* Bearer-specific */}
      {form.method_type === "bearer" && (
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label htmlFor="algorithm">Algorithm</Label>
            <Select
              id="algorithm"
              value={form.algorithm}
              onChange={set("algorithm")}
              disabled={isLoading}
            >
              <option value="HS256">HS256</option>
              <option value="HS384">HS384</option>
              <option value="HS512">HS512</option>
            </Select>
          </div>
          {field(
            "expire_minutes",
            "Expiry (minutes)",
            <Input
              id="expire_minutes"
              type="number"
              value={form.expire_minutes}
              onChange={set("expire_minutes")}
              min={1}
              max={525600}
              disabled={isLoading}
            />,
          )}
        </div>
      )}

      {/* Basic-specific */}
      {form.method_type === "basic" && (
        <>
          {field(
            "username",
            "Username *",
            <Input
              id="username"
              value={form.username}
              onChange={set("username")}
              placeholder="admin"
              autoComplete="off"
              disabled={isLoading}
            />,
          )}
          {field(
            "password",
            mode === "create" ? "Password *" : "Password (leave blank to keep current)",
            <Input
              id="password"
              type="password"
              value={form.password}
              onChange={set("password")}
              placeholder={mode === "edit" ? "••••••••" : ""}
              autoComplete="new-password"
              disabled={isLoading}
            />,
          )}
        </>
      )}

      {/* API key-specific */}
      {form.method_type === "api_key" && mode === "create" && (
        <div className="space-y-1">
          <Label htmlFor="key_prefix">Key prefix</Label>
          <Input
            id="key_prefix"
            value={form.key_prefix}
            onChange={set("key_prefix")}
            placeholder="db2api_"
            maxLength={32}
            disabled={isLoading}
          />
          <p className="text-xs text-muted-foreground">
            The generated key will start with this prefix.
          </p>
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        <input
          id="is_active"
          type="checkbox"
          className="h-4 w-4 rounded border-input"
          checked={form.is_active}
          onChange={set("is_active")}
          disabled={isLoading}
        />
        <Label htmlFor="is_active" className="cursor-pointer">
          Active
        </Label>
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading
            ? mode === "create"
              ? "Creating…"
              : "Saving…"
            : mode === "create"
              ? "Create auth method"
              : "Save changes"}
        </Button>
      </div>
    </form>
  );
}
