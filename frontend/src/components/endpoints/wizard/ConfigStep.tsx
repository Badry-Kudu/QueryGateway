import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { AuthMethod } from "@/types/auth_method";
import type { DataStrategy } from "@/types/endpoint";

import type { WizardState, WizardUpdate } from "./types";

interface ConfigStepProps {
  state: WizardState;
  update: WizardUpdate;
  authMethods: AuthMethod[];
}

export function ConfigStep({ state, update, authMethods }: ConfigStepProps) {
  return (
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
  );
}
