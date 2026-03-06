import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw, Save } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getApiError, settingsApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";
import type { Setting } from "@/types/setting";

export function SettingsPage() {
  const qc = useQueryClient();
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");

  const {
    data: settings = [],
    isLoading,
    error: listError,
  } = useQuery({
    queryKey: queryKeys.settings.list(),
    queryFn: () => settingsApi.list(),
  });

  const { data: restartKeys = [] } = useQuery({
    queryKey: queryKeys.settings.restartKeys(),
    queryFn: () => settingsApi.restartKeys(),
  });

  const restartKeySet = new Set(restartKeys);

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => settingsApi.update(key, value),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.settings.all });
      setEditValues((prev) => {
        const next = { ...prev };
        delete next[vars.key];
        return next;
      });
      setSaveError("");
      setSaveSuccess(`Setting "${vars.key}" saved.`);
      setTimeout(() => setSaveSuccess(""), 3000);
    },
    onError: (err) => {
      setSaveError(getApiError(err));
      setSaveSuccess("");
    },
  });

  const getDisplayValue = (s: Setting) => {
    if (s.key in editValues) return editValues[s.key];
    return s.value;
  };

  const hasChanges = (s: Setting) => s.key in editValues && editValues[s.key] !== s.value;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Application configuration. Some settings require a restart.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => qc.invalidateQueries({ queryKey: queryKeys.settings.all })}
        >
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      {listError && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Failed to load settings: {getApiError(listError)}
        </div>
      )}

      {saveError && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {saveError}
        </div>
      )}

      {saveSuccess && (
        <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {saveSuccess}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : (
        <div className="space-y-4">
          {settings.map((s: Setting) => (
            <div key={s.key} className="rounded-lg border bg-card p-4">
              <div className="mb-2 flex items-center gap-2">
                <Label className="font-mono text-sm font-semibold">{s.key}</Label>
                {restartKeySet.has(s.key) && (
                  <Badge variant="outline" className="text-xs">
                    <AlertTriangle className="mr-1 h-3 w-3" />
                    Restart required
                  </Badge>
                )}
                {s.is_secret && (
                  <Badge variant="secondary" className="text-xs">
                    Secret
                  </Badge>
                )}
              </div>
              {s.description && (
                <p className="mb-2 text-xs text-muted-foreground">{s.description}</p>
              )}
              <div className="flex gap-2">
                <Input
                  value={getDisplayValue(s)}
                  onChange={(e) => setEditValues((prev) => ({ ...prev, [s.key]: e.target.value }))}
                  className="font-mono text-sm"
                  disabled={s.is_secret}
                />
                <Button
                  size="sm"
                  disabled={!hasChanges(s) || updateMutation.isPending}
                  onClick={() => updateMutation.mutate({ key: s.key, value: editValues[s.key] })}
                >
                  <Save className="mr-1 h-3.5 w-3.5" />
                  Save
                </Button>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Last updated: {new Date(s.updated_at).toLocaleString()}
                {s.updated_by ? ` by ${s.updated_by}` : ""}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
