import { CheckCircle, Pencil, Plus, RefreshCw, Trash2, XCircle, Zap } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DeleteConfirmDialog } from "@/components/ui/delete-confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ConnectionForm } from "@/components/connections/ConnectionForm";
import { connectionsApi, getApiError } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";
import { useResourceMutations } from "@/lib/useResourceMutations";
import type {
  Connection,
  ConnectionCreate,
  ConnectionTestResult,
  ConnectionUpdate,
} from "@/types/connection";

export function ConnectionsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Connection | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Connection | null>(null);
  const [testTarget, setTestTarget] = useState<Connection | null>(null);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);

  const { list, createMut, updateMut, deleteMut, formError, setFormError } = useResourceMutations<
    Connection,
    ConnectionCreate,
    ConnectionUpdate
  >({
    api: connectionsApi,
    invalidateKey: queryKeys.connections.all,
    listKey: queryKeys.connections.list(false),
    onCreateSuccess: () => setCreateOpen(false),
    onUpdateSuccess: () => setEditTarget(null),
    onDeleteSuccess: () => setDeleteTarget(null),
  });

  const testMut = useMutation({
    mutationFn: (id: string) => connectionsApi.test(id),
    onSuccess: (result) => setTestResult(result),
    onError: (err) =>
      setTestResult({
        success: false,
        message: getApiError(err),
        duration_ms: null,
        oracle_version: null,
      }),
  });

  function handleCreate(data: ConnectionCreate | ConnectionUpdate) {
    setFormError(null);
    createMut.mutate(data as ConnectionCreate);
  }

  function handleUpdate(data: ConnectionCreate | ConnectionUpdate) {
    if (!editTarget) return;
    setFormError(null);
    updateMut.mutate({ id: editTarget.id, payload: data as ConnectionUpdate });
  }

  function handleTest(conn: Connection) {
    setTestTarget(conn);
    setTestResult(null);
    testMut.mutate(conn.id);
  }

  const connections = list.data ?? [];

  return (
    <div className="mx-auto max-w-6xl p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Oracle Connections</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage Oracle data-source connections for your API endpoints.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={() => list.refetch()} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button
            onClick={() => {
              setFormError(null);
              setCreateOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            New connection
          </Button>
        </div>
      </div>

      {list.isError && (
        <Alert variant="destructive" className="mb-4">
          <AlertTitle>Failed to load connections</AlertTitle>
          <AlertDescription>{getApiError(list.error)}</AlertDescription>
        </Alert>
      )}

      {list.isLoading ? (
        <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
          Loading connections…
        </div>
      ) : connections.length === 0 ? (
        <EmptyState
          title="No connections yet"
          description="Create your first Oracle connection to get started."
          actionLabel="Create connection"
          onAction={() => {
            setFormError(null);
            setCreateOpen(true);
          }}
        />
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Name</th>
                <th className="px-4 py-3 text-left font-medium">Host</th>
                <th className="px-4 py-3 text-left font-medium">Identifier</th>
                <th className="px-4 py-3 text-left font-medium">Mode</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {connections.map((conn) => (
                <tr key={conn.id} className="bg-background transition-colors hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium">
                    {conn.name}
                    {conn.description && (
                      <p className="max-w-[200px] truncate text-xs font-normal text-muted-foreground">
                        {conn.description}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {conn.host}:{conn.port}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {conn.service_name ? `svc: ${conn.service_name}` : `sid: ${conn.sid}`}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline">{conn.mode}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={conn.is_active ? "success" : "secondary"}>
                      {conn.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Test connection"
                        onClick={() => handleTest(conn)}
                      >
                        <Zap className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Edit"
                        onClick={() => {
                          setFormError(null);
                          setEditTarget(conn);
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Delete"
                        onClick={() => {
                          setFormError(null);
                          setDeleteTarget(conn);
                        }}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Create dialog ─────────────────────────────────────────────── */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Oracle Connection</DialogTitle>
            <DialogDescription>
              Configure the Oracle data source. Credentials are encrypted before storage.
            </DialogDescription>
          </DialogHeader>
          <ConnectionForm
            mode="create"
            onSubmit={handleCreate}
            onCancel={() => setCreateOpen(false)}
            isLoading={createMut.isPending}
            error={formError}
          />
        </DialogContent>
      </Dialog>

      {/* ── Edit dialog ───────────────────────────────────────────────── */}
      <Dialog open={!!editTarget} onOpenChange={(o) => !o && setEditTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Connection</DialogTitle>
            <DialogDescription>
              Update connection settings. Leave password blank to keep the current credential.
            </DialogDescription>
          </DialogHeader>
          {editTarget && (
            <ConnectionForm
              mode="edit"
              initial={editTarget}
              onSubmit={handleUpdate}
              onCancel={() => setEditTarget(null)}
              isLoading={updateMut.isPending}
              error={formError}
            />
          )}
        </DialogContent>
      </Dialog>

      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => {
          if (!o) {
            setDeleteTarget(null);
            // Clear stale failure messages when dismissing the dialog
            // so the next delete attempt starts clean.
            setFormError(null);
          }
        }}
        title="Delete connection?"
        description={
          <>
            This will permanently delete <strong>{deleteTarget?.name}</strong>. Any endpoints using
            this connection will stop working.
          </>
        }
        isDeleting={deleteMut.isPending}
        error={formError}
        onConfirm={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
      />

      {/* ── Test result dialog ────────────────────────────────────────── */}
      <Dialog
        open={!!testTarget}
        onOpenChange={(o) => {
          if (!o) {
            setTestTarget(null);
            setTestResult(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Connection test — {testTarget?.name}</DialogTitle>
          </DialogHeader>

          {testMut.isPending ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <RefreshCw className="h-4 w-4 animate-spin" />
              Testing connection…
            </div>
          ) : testResult ? (
            <div className="space-y-3 py-2">
              <Alert variant={testResult.success ? "success" : "destructive"}>
                <span className="absolute left-4 top-4">
                  {testResult.success ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                </span>
                <AlertTitle>
                  {testResult.success ? "Connection successful" : "Connection failed"}
                </AlertTitle>
                <AlertDescription>{testResult.message}</AlertDescription>
              </Alert>

              {testResult.duration_ms != null && (
                <p className="text-xs text-muted-foreground">
                  Response time: {testResult.duration_ms.toFixed(0)} ms
                </p>
              )}
              {testResult.oracle_version && (
                <p className="text-xs text-muted-foreground">Oracle: {testResult.oracle_version}</p>
              )}
            </div>
          ) : null}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setTestTarget(null);
                setTestResult(null);
              }}
            >
              Close
            </Button>
            {testTarget && !testMut.isPending && (
              <Button onClick={() => handleTest(testTarget)}>Retry test</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
