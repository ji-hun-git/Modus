import type { Scope, Source } from "./types";

export const factKindLabels = {
  measurement: "Measurement",
  encounter: "Visit",
  recorded_diagnosis: "Diagnosis as recorded",
  procedure: "Procedure",
  prescription: "Prescription",
  vaccination: "Vaccination",
  imaging_text: "Imaging report text",
  recorded_text: "Other recorded text",
};
export type FactKind = keyof typeof factKindLabels;
export type ReviewedFact = {
  id: string;
  kind: FactKind;
  label: string;
  value: string;
  unit: string | null;
  occurred_on: string | null;
  facility: string | null;
};
export type DraftFact = ReviewedFact & {
  source_quote: string;
  page: number | null;
  bbox?: number[] | null;
};
export type FactReviewRow = DraftFact & { keep: boolean };
export type HistoryFact = Omit<DraftFact, "source_quote" | "value"> & {
  source_id: string;
  available_at: string;
  date?: string | null;
  source_quote: string | null;
  value: string | null;
  value_withheld?: boolean;
  source_quote_withheld?: boolean;
  original_available?: boolean;
  within_date_scope?: boolean;
  age_years?: number | null;
  reviewed_fields?: string[];
  normalization?: {
    status: "identity" | "converted" | "unresolved";
    normalized: {
      value: string;
      unit: string;
      display_is_exact: boolean;
    } | null;
  } | null;
};
export type HistoryView = {
  scope: Omit<Scope, "as_of"> & { as_of: string | null };
  facts: HistoryFact[];
  undated_facts: HistoryFact[];
  sources: Pick<
    Source,
    | "id"
    | "title"
    | "type"
    | "provider"
    | "date"
    | "available_at"
    | "availability_basis"
    | "original_available"
  >[];
  counts: {
    facts: number;
    sources: number;
    conflicts: number;
    undated_facts: number;
    measurements: number;
  };
  conflicts: { id: string; fact_ids: string[]; reason?: string }[];
  profile?: { date_of_birth: string | null; updated_at?: string | null };
};

export type HistoryComparison = {
  format: "modus-history-comparison-v1";
  before: HistoryView;
  after: HistoryView;
  added: HistoryFact[];
  added_counts: { total: number; dated: number; undated: number };
  unchanged_count: number;
  new_conflicts: HistoryView["conflicts"];
  captured_at: string;
};
