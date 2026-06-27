import type { DataStrategy, ParamDescriptor } from "@/types/endpoint";

export const WIZARD_STEPS = [
  "Connection",
  "SQL Query",
  "Parameters",
  "Auth & Config",
  "Review",
] as const;

export type WizardStepName = (typeof WIZARD_STEPS)[number];

export interface WizardState {
  name: string;
  description: string;
  path: string;
  connection_id: string;
  sql_text: string;
  param_schema: Record<string, ParamDescriptor>;
  column_map: Record<string, string>;
  auth_method_id: string;
  /** Explicit opt-in to a public endpoint when no auth method is selected. */
  allow_unauthenticated: boolean;
  data_strategy: DataStrategy;
}

export const INITIAL_WIZARD_STATE: WizardState = {
  name: "",
  description: "",
  path: "",
  connection_id: "",
  sql_text: "",
  param_schema: {},
  column_map: {},
  auth_method_id: "",
  allow_unauthenticated: false,
  data_strategy: "live",
};

export type WizardUpdate = (patch: Partial<WizardState>) => void;
