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
export type DateEvidence = {
  value: string;
  source_quote: string;
  page: number;
  bbox: number[] | null;
  check: { status: "matched_text" | "mismatch" | "unavailable"; issues: string[] };
  relation: "requires_review";
};
export type ReviewedFact = {
  id: string;
  kind: FactKind;
  label: string;
  value: string;
  unit: string | null;
  occurred_on: string | null;
  facility: string | null;
  reference_range?: string | null;
  specimen?: string | null;
  test_method?: string | null;
};
export type DraftFact = ReviewedFact & {
  source_quote: string;
  page: number | null;
  bbox?: number[] | null;
  date_evidence?: DateEvidence | null;
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
  revision_id?: string;
  previous_revision_id?: string;
  first_available_at?: string;
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
  checkup_comparison?: { current:HistoryFact; previous:HistoryFact[]; previous_count:number;
    difference:string|null; unit:string|null; notes:string[]; basis:string; sources:PagedSource[] };
  retrieval?: import('./TerminologyDetails').RetrievalInfo | null;
  page?: { snapshot_id: string; section: string; offset: number; limit: number; returned: number; total: number; matched_sources: number; next_offset: number | null; previous_offset: number | null };
  fields?: { kind: FactKind; label: string; count: number }[];
  facets?: { kinds: FactKind[]; facilities: string[]; facilities_truncated: boolean; date_bounds: string[] };
  scope: Omit<Scope, "as_of"> & { as_of: string | null };
  facts: HistoryFact[];
  undated_facts: HistoryFact[];
  sources: PagedSource[];
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
  updated?: { before: HistoryFact; after: HistoryFact }[];
  removed_from_scope?: HistoryFact[];
  added_counts: { total: number; dated: number; undated: number };
  unchanged_count: number;
  new_conflicts: HistoryView["conflicts"];
  captured_at: string;
};

export type PagedSource = Pick<Source, "id" | "title" | "type" | "provider" | "date" | "available_at" | "availability_basis" | "original_available"> & {
  fact_count?: number; latest_date?: string | null; first_date?: string | null; has_undated?: boolean; display_label?: string;
};
