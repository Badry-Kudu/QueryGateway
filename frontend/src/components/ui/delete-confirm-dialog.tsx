import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface DeleteConfirmDialogProps {
  /** ``true`` to show the dialog; ``false`` to hide it. Most pages
   * derive this from ``!!deleteTarget`` so the dialog opens whenever a
   * resource is selected for deletion. */
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /**
   * Description shown inside the dialog. Pass JSX so the caller can
   * embed the resource name in bold or include side-effect warnings
   * ("any endpoints using this connection will stop working").
   */
  description: ReactNode;
  isDeleting: boolean;
  onConfirm: () => void;
  /**
   * Server-side error message rendered inside the dialog. Pages
   * typically wire this from their ``formError`` state so a failed
   * delete (FK constraint violation, missing perms, etc.) surfaces
   * in the active confirmation flow rather than silently leaving
   * the resource present.
   */
  error?: string | null;
}

/**
 * Identical "Delete X?" confirmation in Connections, AuthMethods, and
 * Schedules. Pulled out so the buttons, copy, and pending state stay
 * in lockstep across pages.
 */
export function DeleteConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  isDeleting,
  onConfirm,
  error,
}: DeleteConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="destructive" disabled={isDeleting} onClick={onConfirm}>
            {isDeleting ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
