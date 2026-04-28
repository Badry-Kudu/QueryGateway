import type { Connection } from "@/types/connection";

import type { WizardState, WizardUpdate } from "./types";

interface ConnectionStepProps {
  state: WizardState;
  update: WizardUpdate;
  connections: Connection[];
}

export function ConnectionStep({ state, update, connections }: ConnectionStepProps) {
  return (
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
              aria-pressed={state.connection_id === c.id}
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
  );
}
