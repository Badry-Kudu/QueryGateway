import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

/**
 * Dashed-border placeholder used by every list page when the resource
 * collection is empty. Was duplicated in Connections, AuthMethods, and
 * Schedules with identical Tailwind classes; this consolidates the
 * styling so future pages stay visually aligned.
 */
export function EmptyState({ title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="flex h-48 flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed text-muted-foreground">
      <p className="font-medium">{title}</p>
      <p className="text-sm">{description}</p>
      {actionLabel && onAction && (
        <Button variant="outline" size="sm" className="mt-2" onClick={onAction}>
          <Plus className="mr-1 h-4 w-4" /> {actionLabel}
        </Button>
      )}
    </div>
  );
}
