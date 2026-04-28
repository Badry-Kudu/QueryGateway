import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DeleteConfirmDialog } from "@/components/ui/delete-confirm-dialog";

describe("DeleteConfirmDialog", () => {
  function renderDialog(overrides: Partial<Parameters<typeof DeleteConfirmDialog>[0]> = {}) {
    const onOpenChange = vi.fn();
    const onConfirm = vi.fn();
    const utils = render(
      <DeleteConfirmDialog
        open
        onOpenChange={onOpenChange}
        title="Delete connection?"
        description="This will permanently delete the connection."
        isDeleting={false}
        onConfirm={onConfirm}
        {...overrides}
      />,
    );
    return { ...utils, onOpenChange, onConfirm };
  }

  it("renders the title and description when open", () => {
    renderDialog();
    expect(screen.getByText("Delete connection?")).toBeInTheDocument();
    expect(screen.getByText("This will permanently delete the connection.")).toBeInTheDocument();
  });

  it("renders nothing when closed", () => {
    render(
      <DeleteConfirmDialog
        open={false}
        onOpenChange={vi.fn()}
        title="Delete connection?"
        description="This will permanently delete the connection."
        isDeleting={false}
        onConfirm={vi.fn()}
      />,
    );
    expect(screen.queryByText("Delete connection?")).not.toBeInTheDocument();
  });

  it("invokes onConfirm when the destructive button is clicked", () => {
    const { onConfirm } = renderDialog();
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("invokes onOpenChange(false) when Cancel is clicked", () => {
    const { onOpenChange } = renderDialog();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    // Radix Dialog also calls onOpenChange via overlay/escape; we only
    // care that our explicit Cancel button wires it.
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("disables the destructive button and shows pending text while deleting", () => {
    renderDialog({ isDeleting: true });
    const button = screen.getByRole("button", { name: "Deleting…" });
    expect(button).toBeDisabled();
  });

  it("accepts JSX in the description prop", () => {
    renderDialog({
      description: (
        <>
          Permanently delete <strong data-testid="resource-name">db-prod</strong>.
        </>
      ),
    });
    expect(screen.getByTestId("resource-name")).toHaveTextContent("db-prod");
  });

  it("renders nothing when error is omitted", () => {
    renderDialog();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("surfaces a server-side error via role=alert", () => {
    renderDialog({
      error: "409 Conflict: connection is referenced by 3 endpoints.",
    });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("409 Conflict: connection is referenced by 3 endpoints.");
  });
});
