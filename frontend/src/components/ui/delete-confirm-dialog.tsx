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
  /** ``null`` when closed; pass a target object to open. */
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
}: DeleteConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
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
