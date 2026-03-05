import { useCallback, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { SqlEditor } from "@/components/endpoints/SqlEditor";
import { authMethodsApi, connectionsApi, endpointsApi, getApiError } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";
import type {
  DataStrategy,
  EndpointCreate,
  ParamDescriptor,
  SqlPreviewResponse,
} from "@/types/endpoint";

const STEPS = ["Connection", "SQL Query", "Parameters", "Auth & Config", "Review"] as const;

type StepName = (typeof STEPS)[number];

interface WizardState {
  name: string;
  description: string;
  path: string;
  connection_id: string;
  sql_text: string;
  param_schema: Record<string, ParamDescriptor>;
  column_map: Record<string, string>;
  auth_method_id: string;
  data_strategy: DataStrategy;
}

const INITIAL_STATE: WizardState = {
  name: "",
  description: "",
  path: "",
  connection_id: "",
  sql_text: "",
  param_schema: {},
  column_map: {},
  auth_method_id: "",
  data_strategy: "live",
};

interface EndpointWizardProps {
  onSuccess: () => void;
  onCancel: () => void;
}

export function EndpointWizard({ onSuccess, onCancel }: EndpointWizardProps) {
  const [step, setStep] = useState(0);
  const [state, setState] = useState<WizardState>(INITIAL_STATE);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<SqlPreviewResponse | null>(null);

  const { data: connections = [] } = useQuery({
    queryKey: queryKeys.connections.list(true),
    queryFn: () => connectionsApi.list(true),
  });

  const { data: authMethods = [] } = useQuery({
    queryKey: queryKeys.authMethods.list(true),
    queryFn: () => authMethodsApi.list(true),
  });

  const previewMutation = useMutation({
    mutationFn: () =>
      endpointsApi.preview({
        connection_id: state.connection_id,
        sql_text: state.sql_text,
        params: Object.fromEntries(
          Object.entries(state.param_schema).map(([k, v]) => [k, v.default ?? ""]),
        ),
        max_rows: 10,
      }),
    onSuccess: (data) => {
      setPreview(data);
      // Auto-populate param_schema from detected bind params
      const newSchema: Record<string, ParamDescriptor> = {};
      for (const p of data.bind_params) {
        newSchema[p] = state.param_schema[p] ?? {
          type: "string",
          required: true,
          default: null,
        };
      }
      setState((s) => ({ ...s, param_schema: newSchema }));
      setError("");
    },
    onError: (err) => setError(getApiError(err)),
  });

  const createMutation = useMutation({
    mutationFn: (payload: EndpointCreate) => endpointsApi.create(payload),
    onSuccess: () => onSuccess(),
    onError: (err) => setError(getApiError(err)),
  });

  const update = useCallback(
    (patch: Partial<WizardState>) => setState((s) => ({ ...s, ...patch })),
    [],
  );

  const canNext = (): boolean => {
    if (step === 0) return !!state.connection_id;
    if (step === 1) return !!state.sql_text.trim();
    if (step === 3) return !!state.name.trim() && !!state.path.trim();
    return true;
  };

  const handleSubmit = () => {
    setError("");
    const payload: EndpointCreate = {
      name: state.name,
      description: state.description || undefined,
      path: state.path,
      connection_id: state.connection_id,
      sql_text: state.sql_text,
      param_schema: state.param_schema,
      column_map: state.column_map,
      auth_method_id: state.auth_method_id || null,
      data_strategy: state.data_strategy,
    };
    createMutation.mutate(payload);
  };

  const updateParam = (name: string, field: keyof ParamDescriptor, value: unknown) => {
    setState((s) => ({
      ...s,
      param_schema: {
        ...s.param_schema,
        [name]: { ...s.param_schema[name], [field]: value },
      },
    }));
  };

  const currentStep: StepName = STEPS[step];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Step indicator */}
      <div className="flex items-center gap-1">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-1">
            <button
              onClick={() => i < step && setStep(i)}
              disabled={i > step}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                i === step
                  ? "bg-primary text-primary-foreground"
                  : i < step
                    ? "cursor-pointer bg-primary/20 text-primary hover:bg-primary/30"
                    : "bg-muted text-muted-foreground"
              }`}
            >
              {i + 1}. {s}
            </button>
            {i < STEPS.length - 1 && <div className="h-px w-4 bg-border" />}
          </div>
        ))}
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Step 1: Connection */}
      {currentStep === "Connection" && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Select Oracle Connection</h3>
          <p className="text-sm text-muted-foreground">
            Choose the Oracle data source this endpoint will query.
          </p>
          {connections.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No active connections available. Create one first.
            </p>
          ) : (
            <div className="grid gap-2">
              {connections.map((c) => (
                <button
                  key={c.id}
                  onClick={() => update({ connection_id: c.id })}
                  className={`rounded-lg border p-3 text-left transition-colors ${
                    state.connection_id === c.id ? "border-primary bg-primary/5" : "hover:bg-muted"
                  }`}
                >
                  <p className="font-medium">{c.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {c.host}:{c.port} / {c.service_name ?? c.sid}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Step 2: SQL Query */}
      {currentStep === "SQL Query" && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Write SQL Query</h3>
          <p className="text-sm text-muted-foreground">
            Use named bind parameters like{" "}
            <code className="rounded bg-muted px-1">:param_name</code>. String interpolation is
            rejected.
          </p>
          <SqlEditor
            value={state.sql_text}
            onChange={(v) => update({ sql_text: v })}
            height="250px"
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => previewMutation.mutate()}
            disabled={!state.sql_text.trim() || previewMutation.isPending}
          >
            {previewMutation.isPending ? "Running..." : "Preview Query"}
          </Button>
          {preview && (
            <div className="space-y-2">
              <p className="text-sm font-medium">
                Preview: {preview.row_count} rows in {preview.duration_ms}ms
              </p>
              {preview.bind_params.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Detected params: {preview.bind_params.join(", ")}
                </p>
              )}
              {preview.rows.length > 0 && (
                <div className="max-h-48 overflow-auto rounded border">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        {preview.columns.map((col) => (
                          <th key={col} className="px-2 py-1 text-left font-medium">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.map((row, i) => (
                        <tr key={i} className="border-b">
                          {preview.columns.map((col) => (
                            <td key={col} className="px-2 py-1">
                              {String(row[col] ?? "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Step 3: Parameters */}
      {currentStep === "Parameters" && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Configure Parameters</h3>
          <p className="text-sm text-muted-foreground">
            Define types and defaults for bind parameters detected in your query.
          </p>
          {Object.keys(state.param_schema).length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No bind parameters detected. You can proceed or go back to modify your query.
            </p>
          ) : (
            <div className="space-y-3">
              {Object.entries(state.param_schema).map(([name, desc]) => (
                <div key={name} className="rounded-lg border p-3">
                  <p className="mb-2 font-mono text-sm font-medium">:{name}</p>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <Label className="text-xs">Type</Label>
                      <select
                        className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-sm"
                        value={desc.type}
                        onChange={(e) => updateParam(name, "type", e.target.value)}
                      >
                        <option value="string">String</option>
                        <option value="integer">Integer</option>
                        <option value="float">Float</option>
                        <option value="boolean">Boolean</option>
                        <option value="date">Date</option>
                      </select>
                    </div>
                    <div>
                      <Label className="text-xs">Required</Label>
                      <select
                        className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-sm"
                        value={desc.required ? "true" : "false"}
                        onChange={(e) => updateParam(name, "required", e.target.value === "true")}
                      >
                        <option value="true">Yes</option>
                        <option value="false">No</option>
                      </select>
                    </div>
                    <div>
                      <Label className="text-xs">Default</Label>
                      <Input
                        className="mt-1 h-8 text-sm"
                        value={String(desc.default ?? "")}
                        onChange={(e) => updateParam(name, "default", e.target.value || null)}
                        placeholder="(none)"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Step 4: Auth & Config */}
      {currentStep === "Auth & Config" && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Endpoint Configuration</h3>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label>Endpoint Name *</Label>
              <Input
                className="mt-1"
                value={state.name}
                onChange={(e) => update({ name: e.target.value })}
                placeholder="My API Endpoint"
              />
            </div>
            <div>
              <Label>URL Path *</Label>
              <div className="mt-1 flex items-center gap-0">
                <span className="rounded-l-md border border-r-0 bg-muted px-2 py-2 text-sm text-muted-foreground">
                  /api/v1/data/
                </span>
                <Input
                  className="rounded-l-none"
                  value={state.path}
                  onChange={(e) => update({ path: e.target.value })}
                  placeholder="employees"
                />
              </div>
            </div>
          </div>

          <div>
            <Label>Description</Label>
            <Textarea
              className="mt-1"
              value={state.description}
              onChange={(e) => update({ description: e.target.value })}
              placeholder="What does this endpoint return?"
              rows={2}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label>Authentication</Label>
              <select
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={state.auth_method_id}
                onChange={(e) => update({ auth_method_id: e.target.value })}
              >
                <option value="">None (public)</option>
                {authMethods.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.method_type})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Data Strategy</Label>
              <select
                className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={state.data_strategy}
                onChange={(e) => update({ data_strategy: e.target.value as DataStrategy })}
              >
                <option value="live">Live (query on each request)</option>
                <option value="snapshot">Snapshot (cached, scheduled refresh)</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Step 5: Review */}
      {currentStep === "Review" && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Review & Publish</h3>
          <div className="space-y-3 rounded-lg border p-4">
            <div className="grid grid-cols-2 gap-y-2 text-sm">
              <span className="text-muted-foreground">Name:</span>
              <span className="font-medium">{state.name}</span>
              <span className="text-muted-foreground">Path:</span>
              <span className="font-mono">/api/v1/data/{state.path}</span>
              <span className="text-muted-foreground">Connection:</span>
              <span>{connections.find((c) => c.id === state.connection_id)?.name ?? "—"}</span>
              <span className="text-muted-foreground">Auth:</span>
              <span>
                {state.auth_method_id
                  ? authMethods.find((a) => a.id === state.auth_method_id)?.name
                  : "None (public)"}
              </span>
              <span className="text-muted-foreground">Strategy:</span>
              <span className="capitalize">{state.data_strategy}</span>
              <span className="text-muted-foreground">Parameters:</span>
              <span>
                {Object.keys(state.param_schema).length > 0
                  ? Object.keys(state.param_schema).join(", ")
                  : "None"}
              </span>
            </div>
            <div>
              <p className="mb-1 text-sm text-muted-foreground">SQL:</p>
              <pre className="max-h-32 overflow-auto rounded bg-muted p-2 text-xs">
                {state.sql_text}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between border-t pt-4">
        <Button variant="outline" onClick={step === 0 ? onCancel : () => setStep(step - 1)}>
          {step === 0 ? "Cancel" : "Back"}
        </Button>
        <div className="flex gap-2">
          {step < STEPS.length - 1 ? (
            <Button onClick={() => setStep(step + 1)} disabled={!canNext()}>
              Next
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending ? "Publishing..." : "Publish Endpoint"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
