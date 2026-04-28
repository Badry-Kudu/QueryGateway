import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type { ParamDescriptor } from "@/types/endpoint";

import type { WizardState } from "./types";

interface ParamsStepProps {
  state: WizardState;
  onUpdateParam: (name: string, field: keyof ParamDescriptor, value: unknown) => void;
}

export function ParamsStep({ state, onUpdateParam }: ParamsStepProps) {
  const entries = Object.entries(state.param_schema);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Configure Parameters</h3>
      <p className="text-sm text-muted-foreground">
        Define types and defaults for bind parameters detected in your query.
      </p>
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No bind parameters detected. You can proceed or go back to modify your query.
        </p>
      ) : (
        <div className="space-y-3">
          {entries.map(([name, desc]) => (
            <div key={name} className="rounded-lg border p-3">
              <p className="mb-2 font-mono text-sm font-medium">:{name}</p>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <Label className="text-xs">Type</Label>
                  <Select
                    className="mt-1 h-8 px-2 py-1.5"
                    value={desc.type}
                    onChange={(e) => onUpdateParam(name, "type", e.target.value)}
                  >
                    <option value="string">String</option>
                    <option value="integer">Integer</option>
                    <option value="float">Float</option>
                    <option value="boolean">Boolean</option>
                    <option value="date">Date</option>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Required</Label>
                  <Select
                    className="mt-1 h-8 px-2 py-1.5"
                    value={desc.required ? "true" : "false"}
                    onChange={(e) => onUpdateParam(name, "required", e.target.value === "true")}
                  >
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Default</Label>
                  <Input
                    className="mt-1 h-8 text-sm"
                    value={String(desc.default ?? "")}
                    onChange={(e) => onUpdateParam(name, "default", e.target.value || null)}
                    placeholder="(none)"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
