/**
 * Hook for the standard CRUD-resource page pattern.
 *
 * The Connections, AuthMethods, and Schedules pages all share the same
 * shape: one ``useQuery`` for the list, three ``useMutation`` calls
 * (create / update / delete), plus a ``formError`` string that the
 * mutations push into and the create/edit dialogs render. That's
 * ~40 LOC of boilerplate per page, copy-pasted three times.
 *
 * This hook centralises the wiring. Callers pass in the API methods,
 * the React Query keys, and (optionally) per-mutation ``onSuccess``
 * callbacks; the hook returns the query result, the three mutations
 * (already wired to invalidate the right keys and surface errors via
 * ``formError``), and the ``formError`` state itself.
 *
 * All three mutations write failures into ``formError``. There are no
 * ``onError`` callback options — pages that want bespoke error
 * handling should observe ``formError`` (or the ``mutation.error``
 * fields directly).
 *
 * Special-case mutations (test-connection, issue-token, rotate, etc.)
 * stay in the page — this hook only handles the *standard* three.
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";

import { getApiError } from "@/lib/api";

export interface ResourceApi<T, Create, Update> {
  list: (activeOnly?: boolean) => Promise<T[]>;
  create: (payload: Create) => Promise<T>;
  update: (id: string, payload: Update) => Promise<T>;
  delete: (id: string) => Promise<void>;
}

export interface UseResourceMutationsOptions<T, Create, Update> {
  api: ResourceApi<T, Create, Update>;
  /**
   * Root query key — the hook invalidates this after every mutation.
   * Use the ``.all`` field of the resource's key factory.
   */
  invalidateKey: QueryKey;
  /** Concrete list query key passed to ``useQuery``. */
  listKey: QueryKey;
  /** Forwarded to ``api.list`` — most pages call with ``false``. */
  activeOnly?: boolean;
  /** Optional hook called after a successful create. */
  onCreateSuccess?: (created: T) => void;
  /** Optional hook called after a successful update. */
  onUpdateSuccess?: (updated: T) => void;
  /** Optional hook called after a successful delete. */
  onDeleteSuccess?: () => void;
}

export function useResourceMutations<T, Create, Update>(
  opts: UseResourceMutationsOptions<T, Create, Update>,
) {
  const qc = useQueryClient();
  const [formError, setFormError] = useState<string | null>(null);

  const list = useQuery({
    queryKey: opts.listKey,
    queryFn: () => opts.api.list(opts.activeOnly ?? false),
  });

  const createMut = useMutation({
    mutationFn: (payload: Create) => opts.api.create(payload),
    onSuccess: (created) => {
      void qc.invalidateQueries({ queryKey: opts.invalidateKey });
      setFormError(null);
      opts.onCreateSuccess?.(created);
    },
    onError: (err) => setFormError(getApiError(err)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Update }) => opts.api.update(id, payload),
    onSuccess: (updated) => {
      void qc.invalidateQueries({ queryKey: opts.invalidateKey });
      setFormError(null);
      opts.onUpdateSuccess?.(updated);
    },
    onError: (err) => setFormError(getApiError(err)),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => opts.api.delete(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: opts.invalidateKey });
      opts.onDeleteSuccess?.();
    },
    // Surface delete failures the same way as create/update so users
    // see actionable feedback. Without this the mutation silently
    // swallowed errors.
    onError: (err) => setFormError(getApiError(err)),
  });

  return {
    list,
    createMut,
    updateMut,
    deleteMut,
    formError,
    setFormError,
  };
}
