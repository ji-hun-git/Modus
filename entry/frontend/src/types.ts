import type { DraftFact } from "./historyTypes";

export type Scope = {
  as_of: string;
  known_at: string;
  captured_at: string;
  scope_id: string;
};
export type ScopeRequest = {
  as_of: string;
  known_at: string;
  compare_from?: string | null;
};
export type Observation = {
  id: string;
  metric: "hba1c" | "egfr" | "ldl";
  value: number;
  unit: string;
  date: string;
  source_id: string;
  source_span: string;
  page: number | null;
  reviewed_fields?: string[] | null;
  reported_at?: string | null;
  reported_at_raw?: string | null;
  available_at: string;
  availability_basis?: string | null;
};
export type Source = {
  id: string;
  title: string;
  provider: string;
  date: string;
  type: string;
  content: string;
  synthetic: boolean;
  original_available: boolean;
  available_at: string;
  availability_basis: string;
  ingested_at?: string;
  sha256?: string;
  extraction_mode?: string;
};
export type Conflict = {
  id: string;
  metric: string;
  date: string;
  reason: string;
  observations: Observation[];
};
export type View = {
  scope: Scope;
  observations: Observation[];
  sources: Source[];
  counts: { measurements: number; documents: number; disagreements: number };
  conflicts: Conflict[];
};
export type Comparison = {
  before: View;
  after: View;
  captured_at: string;
  added: Observation[];
  unchanged_count: number;
  new_conflicts: Conflict[];
};
export type Draft = {
  id: string;
  source: Source;
  observations: Observation[];
  warnings: string[];
  extraction_mode: string;
  already_committed?: boolean;
  extraction_review?: ExtractionReview;
  facts?: DraftFact[];
};
export type ExtractedFactReview = {
  id: string;
  label: string;
  value: string | number | null;
  unit: string | null;
  date: string | null;
  page: number | null;
  source_quote: string;
  bbox: number[] | null;
  model_confidence: number | null;
  review_reasons: string[];
  commit_supported: boolean;
};
export type ExtractionReview = {
  document_type: string;
  verification_status: string;
  facts: ExtractedFactReview[];
};
export type ReviewRow = Observation & { keep: boolean; valueText: string };
export type Reviewed = Pick<
  Observation,
  "id" | "metric" | "value" | "unit" | "date"
>;
export type Commit = {
  draft_id: string;
  source_id: string;
  inserted: number;
  duplicate: boolean;
  available_at: string;
  observation_ids: string[];
  fact_ids?: string[];
  bundle_id: string;
};
export type Health = {
  application: string;
  release: string;
  bundle_id: string;
  synthetic_only: boolean;
  local_ocr?: {
    available: boolean;
    mode: "local-teleocr";
    reason?: string;
  };
  provider: {
    mode: string;
    requested_mode: string;
    key_configured: boolean;
    model: string;
    live_verified: boolean;
  };
};
export type Claim = {
  id: string;
  text: string;
  evidence_ids: string[];
  tool_name: string;
  status: string;
};
export type Answer = {
  mode: string;
  answer: string;
  claims: Claim[];
  trace: {
    name: string;
    arguments: unknown;
    result: unknown;
    status: string;
    duration_ms: number;
    executor: string;
  }[];
  execution: unknown;
  telemetry?: unknown;
  scope: Scope;
  comparison?: Comparison | null;
};
export type Change = {
  id: string | number;
  created_at: string;
  kind: string;
  status: string;
  draft_id?: string;
  source_id?: string;
  available_at?: string;
  observation_ids?: string[];
  fact_count?: number;
  scope?: Scope;
  message?: string;
  answer?: string;
  mode?: string;
  error?: string;
  telemetry?: { calls?: ProviderCall[] };
};
export type ProviderCall = {
  stage?: string | null;
  model?: string | null;
  returned_model?: string | null;
  status?: string | null;
  result_validation?: string | null;
  error_kind?: string | null;
  request_id?: string | null;
  response_id?: string | null;
  duration_ms?: number | null;
  usage?: {
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    total_tokens?: number | null;
  } | null;
};
export {
  metricLabel,
  metricDescription,
  recordLabel,
} from "./recordPresentation.mjs";
