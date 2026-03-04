import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { Connection, ConnectionCreate, ConnectionUpdate } from "@/types/connection";

type Mode = "create" | "edit";

interface ConnectionFormProps {
  mode: Mode;
  initial?: Connection;
  onSubmit: (data: ConnectionCreate | ConnectionUpdate) => void;
  onCancel: () => void;
  isLoading?: boolean;
  error?: string | null;
}

interface FormState {
  name: string;
  description: string;
  host: string;
  port: string;
  identifier_type: "service_name" | "sid";
  identifier_value: string;
  username: string;
  password: string;
  pool_min: string;
  pool_max: string;
  pool_timeout: string;
  query_timeout: string;
  mode: "thin" | "thick";
  is_active: boolean;
}

function toFormState(conn?: Connection): FormState {
  return {
    name: conn?.name ?? "",
    description: conn?.description ?? "",
    host: conn?.host ?? "",
    port: String(conn?.port ?? 1521),
    identifier_type: conn?.service_name ? "service_name" : "sid",
    identifier_value: conn?.service_name ?? conn?.sid ?? "",
    username: conn?.username ?? "",
    password: "",
    pool_min: String(conn?.pool_min ?? 1),
    pool_max: String(conn?.pool_max ?? 5),
    pool_timeout: String(conn?.pool_timeout ?? 30),
    query_timeout: String(conn?.query_timeout ?? 30),
    mode: conn?.mode ?? "thin",
    is_active: conn?.is_active ?? true,
  };
}

export function ConnectionForm({
  mode,
  initial,
  onSubmit,
  onCancel,
  isLoading = false,
  error,
}: ConnectionFormProps) {
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
    if (!form.host.trim()) errs.host = "Host is required.";
    if (!form.identifier_value.trim())
      errs.identifier_value = `${form.identifier_type === "service_name" ? "Service name" : "SID"} is required.`;
    if (!form.username.trim()) errs.username = "Username is required.";
    if (mode === "create" && !form.password) errs.password = "Password is required.";
    const port = Number(form.port);
    if (isNaN(port) || port < 1 || port > 65535) errs.port = "Port must be 1–65535.";
    const pmin = Number(form.pool_min);
    const pmax = Number(form.pool_max);
    if (pmin > pmax) errs.pool_min = "pool_min must be ≤ pool_max.";
    setValidationErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const base = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      host: form.host.trim(),
      port: Number(form.port),
      service_name: form.identifier_type === "service_name" ? form.identifier_value.trim() : null,
      sid: form.identifier_type === "sid" ? form.identifier_value.trim() : null,
      username: form.username.trim(),
      pool_min: Number(form.pool_min),
      pool_max: Number(form.pool_max),
      pool_timeout: Number(form.pool_timeout),
      query_timeout: Number(form.query_timeout),
      mode: form.mode,
      is_active: form.is_active,
    };

    if (mode === "create") {
      onSubmit({ ...base, password: form.password } as ConnectionCreate);
    } else {
      const update: ConnectionUpdate = { ...base };
      if (form.password) update.password = form.password;
      onSubmit(update);
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

      {/* Basic */}
      {field(
        "name",
        "Name *",
        <Input
          id="name"
          value={form.name}
          onChange={set("name")}
          placeholder="production-oracle"
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

      {/* Network */}
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2 space-y-1">
          <Label htmlFor="host">Host *</Label>
          <Input
            id="host"
            value={form.host}
            onChange={set("host")}
            placeholder="oracle.example.com"
            disabled={isLoading}
          />
          {validationErrors.host && (
            <p className="text-xs text-destructive">{validationErrors.host}</p>
          )}
        </div>
        <div className="space-y-1">
          <Label htmlFor="port">Port</Label>
          <Input
            id="port"
            type="number"
            value={form.port}
            onChange={set("port")}
            min={1}
            max={65535}
            disabled={isLoading}
          />
          {validationErrors.port && (
            <p className="text-xs text-destructive">{validationErrors.port}</p>
          )}
        </div>
      </div>

      {/* Identifier */}
      <div className="space-y-1">
        <Label>Identifier type *</Label>
        <div className="flex gap-3">
          <Select
            value={form.identifier_type}
            onChange={set("identifier_type")}
            className="w-40"
            disabled={isLoading}
          >
            <option value="service_name">Service name</option>
            <option value="sid">SID</option>
          </Select>
          <div className="flex-1 space-y-1">
            <Input
              id="identifier_value"
              value={form.identifier_value}
              onChange={set("identifier_value")}
              placeholder={form.identifier_type === "service_name" ? "ORCLPDB" : "ORCL"}
              disabled={isLoading}
            />
            {validationErrors.identifier_value && (
              <p className="text-xs text-destructive">{validationErrors.identifier_value}</p>
            )}
          </div>
        </div>
      </div>

      {/* Credentials */}
      {field(
        "username",
        "Username *",
        <Input
          id="username"
          value={form.username}
          onChange={set("username")}
          placeholder="hr"
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

      {/* Pool */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label htmlFor="pool_min">Pool min</Label>
          <Input
            id="pool_min"
            type="number"
            value={form.pool_min}
            onChange={set("pool_min")}
            min={0}
            max={100}
            disabled={isLoading}
          />
          {validationErrors.pool_min && (
            <p className="text-xs text-destructive">{validationErrors.pool_min}</p>
          )}
        </div>
        <div className="space-y-1">
          <Label htmlFor="pool_max">Pool max</Label>
          <Input
            id="pool_max"
            type="number"
            value={form.pool_max}
            onChange={set("pool_max")}
            min={1}
            max={100}
            disabled={isLoading}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="pool_timeout">Pool timeout (s)</Label>
          <Input
            id="pool_timeout"
            type="number"
            value={form.pool_timeout}
            onChange={set("pool_timeout")}
            min={1}
            max={3600}
            disabled={isLoading}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="query_timeout">Query timeout (s)</Label>
          <Input
            id="query_timeout"
            type="number"
            value={form.query_timeout}
            onChange={set("query_timeout")}
            min={1}
            max={3600}
            disabled={isLoading}
          />
        </div>
      </div>

      {/* Mode + Active */}
      <div className="grid grid-cols-2 gap-3">
        {field(
          "mode",
          "Driver mode",
          <Select id="mode" value={form.mode} onChange={set("mode")} disabled={isLoading}>
            <option value="thin">Thin (default)</option>
            <option value="thick">Thick</option>
          </Select>,
        )}
        <div className="flex items-end pb-0.5">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-input"
              checked={form.is_active}
              onChange={set("is_active")}
              disabled={isLoading}
            />
            <span className="text-sm font-medium">Active</span>
          </label>
        </div>
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
              ? "Create connection"
              : "Save changes"}
        </Button>
      </div>
    </form>
  );
}
