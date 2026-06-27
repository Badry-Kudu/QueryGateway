import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ParamsStep } from "@/components/endpoints/wizard/ParamsStep";
import type { WizardState } from "@/components/endpoints/wizard/types";

function makeState(params: WizardState["param_schema"]): WizardState {
  return {
    name: "",
    description: "",
    path: "",
    connection_id: "",
    sql_text: "",
    param_schema: params,
    column_map: {},
    auth_method_id: "",
    allow_unauthenticated: false,
    data_strategy: "live",
  };
}

describe("ParamsStep", () => {
  it("renders an empty-state message when no params exist", () => {
    render(<ParamsStep state={makeState({})} onUpdateParam={vi.fn()} />);
    expect(screen.getByText(/No bind parameters detected/i)).toBeInTheDocument();
  });

  describe("string type", () => {
    it("renders a plain text input", () => {
      render(
        <ParamsStep
          state={makeState({ q: { type: "string", required: false, default: null } })}
          onUpdateParam={vi.fn()}
        />,
      );
      const input = screen.getByPlaceholderText("(none)") as HTMLInputElement;
      expect(input.type).toBe("text");
    });

    it("passes the string value to onUpdateParam", () => {
      const onUpdateParam = vi.fn();
      render(
        <ParamsStep
          state={makeState({ q: { type: "string", required: false, default: null } })}
          onUpdateParam={onUpdateParam}
        />,
      );
      fireEvent.change(screen.getByPlaceholderText("(none)"), { target: { value: "hello" } });
      expect(onUpdateParam).toHaveBeenCalledWith("q", "default", "hello");
    });

    it("resolves an empty string to null", () => {
      const onUpdateParam = vi.fn();
      render(
        <ParamsStep
          state={makeState({ q: { type: "string", required: false, default: "hello" } })}
          onUpdateParam={onUpdateParam}
        />,
      );
      fireEvent.change(screen.getByDisplayValue("hello"), { target: { value: "" } });
      expect(onUpdateParam).toHaveBeenCalledWith("q", "default", null);
    });
  });

  describe("integer type", () => {
    it("renders a number input without a step attribute", () => {
      render(
        <ParamsStep
          state={makeState({ page: { type: "integer", required: false, default: null } })}
          onUpdateParam={vi.fn()}
        />,
      );
      const input = screen.getByPlaceholderText("(none)") as HTMLInputElement;
      expect(input.type).toBe("number");
      expect(input).not.toHaveAttribute("step");
    });

    it("passes a parsed integer to onUpdateParam", () => {
      const onUpdateParam = vi.fn();
      render(
        <ParamsStep
          state={makeState({ page: { type: "integer", required: false, default: null } })}
          onUpdateParam={onUpdateParam}
        />,
      );
      fireEvent.change(screen.getByPlaceholderText("(none)"), { target: { value: "42" } });
      expect(onUpdateParam).toHaveBeenCalledWith("page", "default", 42);
    });

    it("resolves an empty value to null", () => {
      const onUpdateParam = vi.fn();
      render(
        <ParamsStep
          state={makeState({ page: { type: "integer", required: false, default: 10 } })}
          onUpdateParam={onUpdateParam}
        />,
      );
      fireEvent.change(screen.getByDisplayValue("10"), { target: { value: "" } });
      expect(onUpdateParam).toHaveBeenCalledWith("page", "default", null);
    });
  });

  describe("float type", () => {
    it("renders a number input with step='any'", () => {
      render(
        <ParamsStep
          state={makeState({ ratio: { type: "float", required: false, default: null } })}
          onUpdateParam={vi.fn()}
        />,
      );
      const input = screen.getByPlaceholderText("(none)") as HTMLInputElement;
      expect(input.type).toBe("number");
      expect(input).toHaveAttribute("step", "any");
    });

    it("passes a parsed float to onUpdateParam", () => {
      const onUpdateParam = vi.fn();
      render(
        <ParamsStep
          state={makeState({ ratio: { type: "float", required: false, default: null } })}
          onUpdateParam={onUpdateParam}
        />,
      );
      fireEvent.change(screen.getByPlaceholderText("(none)"), { target: { value: "3.14" } });
      expect(onUpdateParam).toHaveBeenCalledWith("ratio", "default", 3.14);
    });

    it("resolves an empty value to null", () => {
      const onUpdateParam = vi.fn();
      render(
        <ParamsStep
          state={makeState({ ratio: { type: "float", required: false, default: 1.5 } })}
          onUpdateParam={onUpdateParam}
        />,
      );
      fireEvent.change(screen.getByDisplayValue("1.5"), { target: { value: "" } });
      expect(onUpdateParam).toHaveBeenCalledWith("ratio", "default", null);
    });
  });

  describe("boolean type", () => {
    it("renders a checkbox", () => {
      render(
        <ParamsStep
          state={makeState({ active: { type: "boolean", required: false, default: null } })}
          onUpdateParam={vi.fn()}
        />,
      );
      expect(screen.getByRole("checkbox")).toBeInTheDocument();
    });

    it("is unchecked when default is null", () => {
      render(
        <ParamsStep
          state={makeState({ active: { type: "boolean", required: false, default: null } })}
          onUpdateParam={vi.fn()}
        />,
      );
      expect(screen.getByRole("checkbox")).not.toBeChecked();
    });

    it("is checked when default is true", () => {
      render(
        <ParamsStep
          state={makeState({ active: { type: "boolean", required: false, default: true } })}
          onUpdateParam={vi.fn()}
        />,
      );
      expect(screen.getByRole("checkbox")).toBeChecked();
    });

    it("sends true when checked", () => {
      const onUpdateParam = vi.fn();
      render(
        <ParamsStep
          state={makeState({ active: { type: "boolean", required: false, default: null } })}
          onUpdateParam={onUpdateParam}
        />,
      );
      // fireEvent.click toggles the native checked state and fires the change
      // event, which React maps to the synthetic onChange handler.
      fireEvent.click(screen.getByRole("checkbox"));
      expect(onUpdateParam).toHaveBeenCalledWith("active", "default", true);
    });

    it("sends null when unchecked", () => {
      const onUpdateParam = vi.fn();
      render(
        <ParamsStep
          state={makeState({ active: { type: "boolean", required: false, default: true } })}
          onUpdateParam={onUpdateParam}
        />,
      );
      fireEvent.click(screen.getByRole("checkbox"));
      expect(onUpdateParam).toHaveBeenCalledWith("active", "default", null);
    });
  });

  describe("date type", () => {
    it("renders a date input", () => {
      const { container } = render(
        <ParamsStep
          state={makeState({ since: { type: "date", required: false, default: null } })}
          onUpdateParam={vi.fn()}
        />,
      );
      const input = container.querySelector('input[type="date"]') as HTMLInputElement;
      expect(input).toBeInTheDocument();
    });

    it("passes the ISO date string to onUpdateParam", () => {
      const onUpdateParam = vi.fn();
      const { container } = render(
        <ParamsStep
          state={makeState({ since: { type: "date", required: false, default: null } })}
          onUpdateParam={onUpdateParam}
        />,
      );
      const input = container.querySelector('input[type="date"]') as HTMLInputElement;
      fireEvent.change(input, { target: { value: "2025-01-15" } });
      expect(onUpdateParam).toHaveBeenCalledWith("since", "default", "2025-01-15");
    });

    it("resolves an empty value to null", () => {
      const onUpdateParam = vi.fn();
      const { container } = render(
        <ParamsStep
          state={makeState({ since: { type: "date", required: false, default: "2025-01-01" } })}
          onUpdateParam={onUpdateParam}
        />,
      );
      const input = container.querySelector('input[type="date"]') as HTMLInputElement;
      fireEvent.change(input, { target: { value: "" } });
      expect(onUpdateParam).toHaveBeenCalledWith("since", "default", null);
    });
  });
});
