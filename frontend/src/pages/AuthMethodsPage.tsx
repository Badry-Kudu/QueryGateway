import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, Pencil, Plus, RefreshCw, RotateCw, Trash2 } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { AuthMethodForm } from "@/components/auth/AuthMethodForm";
import { authMethodsApi, getApiError } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";
import type {
  ApiKeyIssuedResponse,
  AuthMethod,
  AuthMethodCreate,
  AuthMethodUpdate,
  TokenIssuedResponse,
} from "@/types/auth_method";

function methodTypeLabel(type: string): string {
  if (type === "bearer") return "Bearer JWT";
  if (type === "basic") return "Basic";
  if (type === "api_key") return "API Key";
  return type;
}

export function AuthMethodsPage() {
  const qc = useQueryClient();

  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<AuthMethod | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AuthMethod | null>(null);
  const [tokenResult, setTokenResult] = useState<TokenIssuedResponse | null>(null);
  const [rotateResult, setRotateResult] = useState<
    (ApiKeyIssuedResponse & { message?: undefined }) | { message: string } | null
  >(null);
  const [rotateTarget, setRotateTarget] = useState<AuthMethod | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [createdKey, setCreatedKey] = useState<ApiKeyIssuedResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const {
    data: methods = [],
    isLoading,
    isError,
    error: listError,
    refetch,
  } = useQuery({
    queryKey: queryKeys.authMethods.list(false),
    queryFn: () => authMethodsApi.list(false),
  });

  const createMut = useMutation({
    mutationFn: (payload: AuthMethodCreate) => {
      if (payload.method_type === "api_key") {
        return authMethodsApi.createWithKey(payload).then((keyResp) => {
          setCreatedKey(keyResp);
          return null as unknown as AuthMethod;
        });
      }
      return authMethodsApi.create(payload);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.authMethods.all });
      setCreateOpen(false);
      setFormError(null);
    },
    onError: (err) => setFormError(getApiError(err)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AuthMethodUpdate }) =>
      authMethodsApi.update(id, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.authMethods.all });
      setEditTarget(null);
      setFormError(null);
    },
    onError: (err) => setFormError(getApiError(err)),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => authMethodsApi.delete(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.authMethods.all });
      setDeleteTarget(null);
    },
  });

  const issueTokenMut = useMutation({
    mutationFn: (id: string) => authMethodsApi.issueToken(id),
    onSuccess: (result) => setTokenResult(result),
  });

  const rotateMut = useMutation({
    mutationFn: (id: string) => authMethodsApi.rotate(id),
    onSuccess: (result) => {
      void qc.invalidateQueries({ queryKey: queryKeys.authMethods.all });
      setRotateResult(result as typeof rotateResult);
    },
  });

  function handleCreate(data: AuthMethodCreate | AuthMethodUpdate) {
    setFormError(null);
    createMut.mutate(data as AuthMethodCreate);
  }

  function handleUpdate(data: AuthMethodCreate | AuthMethodUpdate) {
    if (!editTarget) return;
    setFormError(null);
    updateMut.mutate({ id: editTarget.id, payload: data as AuthMethodUpdate });
  }

  function handleCopy(text: string) {
    void navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="mx-auto max-w-6xl p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Auth Methods</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Configure authentication for your data API endpoints.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={() => refetch()} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button
            onClick={() => {
              setFormError(null);
              setCreateOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            New auth method
          </Button>
        </div>
      </div>

      {/* Error state */}
      {isError && (
        <Alert variant="destructive" className="mb-4">
          <AlertTitle>Failed to load auth methods</AlertTitle>
          <AlertDescription>{getApiError(listError)}</AlertDescription>
        </Alert>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
          Loading auth methods…
        </div>
      ) : methods.length === 0 ? (
        <div className="flex h-48 flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed text-muted-foreground">
          <p className="font-medium">No auth methods yet</p>
          <p className="text-sm">Create your first auth method to secure data endpoints.</p>
          <Button variant="outline" size="sm" className="mt-2" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1 h-4 w-4" /> Create auth method
          </Button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Name</th>
                <th className="px-4 py-3 text-left font-medium">Type</th>
                <th className="px-4 py-3 text-left font-medium">Config</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {methods.map((m) => (
                <tr key={m.id} className="bg-background transition-colors hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium">
                    {m.name}
                    {m.description && (
                      <p className="max-w-[200px] truncate text-xs font-normal text-muted-foreground">
                        {m.description}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline">{methodTypeLabel(m.method_type)}</Badge>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {m.method_type === "bearer" && (
                      <span>
                        {m.algorithm} · {m.expire_minutes}m
                      </span>
                    )}
                    {m.method_type === "basic" && <span>user: {m.username}</span>}
                    {m.method_type === "api_key" && <span>prefix: {m.key_prefix}</span>}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={m.is_active ? "success" : "secondary"}>
                      {m.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {m.method_type === "bearer" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Issue token"
                          onClick={() => {
                            setTokenResult(null);
                            issueTokenMut.mutate(m.id);
                          }}
                        >
                          <KeyRound className="h-4 w-4" />
                        </Button>
                      )}
                      {m.method_type !== "basic" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Rotate credentials"
                          onClick={() => {
                            setRotateTarget(m);
                            setRotateResult(null);
                            rotateMut.mutate(m.id);
                          }}
                        >
                          <RotateCw className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Edit"
                        onClick={() => {
                          setFormError(null);
                          setEditTarget(m);
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Delete"
                        onClick={() => setDeleteTarget(m)}
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

      {/* ── Create dialog ────────────────────────────────────────────────── */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Auth Method</DialogTitle>
            <DialogDescription>
              Choose a method type and configure it. For API key methods the key is returned once.
            </DialogDescription>
          </DialogHeader>
          <AuthMethodForm
            mode="create"
            onSubmit={handleCreate}
            onCancel={() => setCreateOpen(false)}
            isLoading={createMut.isPending}
            error={formError}
          />
        </DialogContent>
      </Dialog>

      {/* ── Edit dialog ──────────────────────────────────────────────────── */}
      <Dialog open={!!editTarget} onOpenChange={(o) => !o && setEditTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Auth Method</DialogTitle>
            <DialogDescription>
              Update settings. Auth type cannot be changed after creation.
            </DialogDescription>
          </DialogHeader>
          {editTarget && (
            <AuthMethodForm
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

      {/* ── Delete dialog ────────────────────────────────────────────────── */}
      <Dialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete auth method?</DialogTitle>
            <DialogDescription>
              This will permanently delete <strong>{deleteTarget?.name}</strong>. Any endpoints
              using this auth method will reject requests.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteMut.isPending}
              onClick={() => deleteTarget && deleteMut.mutate(deleteTarget.id)}
            >
              {deleteMut.isPending ? "Deleting…" : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Issue token result dialog ────────────────────────────────────── */}
      <Dialog open={!!tokenResult} onOpenChange={(o) => !o && setTokenResult(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bearer Token Issued</DialogTitle>
            <DialogDescription>{tokenResult?.note}</DialogDescription>
          </DialogHeader>
          {tokenResult && (
            <div className="space-y-3">
              <div className="break-all rounded-md bg-muted p-3 font-mono text-xs">
                {tokenResult.token}
              </div>
              <p className="text-xs text-muted-foreground">
                Expires: {new Date(tokenResult.expires_at).toLocaleString()}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => handleCopy(tokenResult.token)}
              >
                <Copy className="mr-2 h-3 w-3" />
                {copied ? "Copied!" : "Copy token"}
              </Button>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setTokenResult(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Created API key dialog ───────────────────────────────────────── */}
      <Dialog open={!!createdKey} onOpenChange={(o) => !o && setCreatedKey(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>API Key Created</DialogTitle>
            <DialogDescription>{createdKey?.note}</DialogDescription>
          </DialogHeader>
          {createdKey && (
            <div className="space-y-3">
              <div className="break-all rounded-md bg-muted p-3 font-mono text-xs">
                {createdKey.api_key}
              </div>
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => handleCopy(createdKey.api_key)}
              >
                <Copy className="mr-2 h-3 w-3" />
                {copied ? "Copied!" : "Copy key"}
              </Button>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setCreatedKey(null)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Rotate result dialog ────────────────────────────────────────── */}
      <Dialog
        open={!!rotateResult}
        onOpenChange={(o) => {
          if (!o) {
            setRotateResult(null);
            setRotateTarget(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Credentials Rotated — {rotateTarget?.name}</DialogTitle>
          </DialogHeader>
          {rotateResult && (
            <div className="space-y-3">
              {"api_key" in rotateResult ? (
                <>
                  <p className="text-sm text-muted-foreground">
                    New API key (shown once — store it now):
                  </p>
                  <div className="break-all rounded-md bg-muted p-3 font-mono text-xs">
                    {rotateResult.api_key}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => "api_key" in rotateResult && handleCopy(rotateResult.api_key)}
                  >
                    <Copy className="mr-2 h-3 w-3" />
                    {copied ? "Copied!" : "Copy key"}
                  </Button>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">{rotateResult.message}</p>
              )}
            </div>
          )}
          <DialogFooter>
            <Button
              onClick={() => {
                setRotateResult(null);
                setRotateTarget(null);
              }}
            >
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
