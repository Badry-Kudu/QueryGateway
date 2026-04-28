import { Button } from "@/components/ui/button";
import { SqlEditor } from "@/components/endpoints/SqlEditor";
import type { SqlPreviewResponse } from "@/types/endpoint";

import type { WizardState, WizardUpdate } from "./types";

interface SqlStepProps {
  state: WizardState;
  update: WizardUpdate;
  preview: SqlPreviewResponse | null;
  isPreviewing: boolean;
  onPreview: () => void;
}

export function SqlStep({ state, update, preview, isPreviewing, onPreview }: SqlStepProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Write SQL Query</h3>
      <p className="text-sm text-muted-foreground">
        Use named bind parameters like <code className="rounded bg-muted px-1">:param_name</code>.
        String interpolation is rejected.
      </p>
      <SqlEditor value={state.sql_text} onChange={(v) => update({ sql_text: v })} height="250px" />
      <Button
        variant="outline"
        size="sm"
        onClick={onPreview}
        disabled={!state.sql_text.trim() || isPreviewing}
      >
        {isPreviewing ? "Running..." : "Preview Query"}
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
  );
}
