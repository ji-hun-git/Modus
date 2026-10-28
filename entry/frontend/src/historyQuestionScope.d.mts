import type { HistoryView } from "./historyTypes";
type Scope = HistoryView["scope"];
export function historyQuestionKey(
  scope: Scope,
  compareFrom?: string | null,
): string;
export function historyQuestionRequest(
  scope: Scope,
  message: string,
  compareFrom?: string | null,
): {
  as_of: string | null;
  known_at: string;
  compare_from?: string;
  message: string;
};
export function historyAnswerMatches(
  answer: {
    scope: Scope;
    history_evidence: HistoryView;
    history_comparison?: { before: Scope; after: Scope } | null;
  },
  scope: Scope,
  compareFrom?: string | null,
): boolean;
export function historyClaimEvidence(
  view: HistoryView,
  evidenceIds: string[],
): {
  source: HistoryView["sources"][number];
  facts: HistoryView["facts"];
}[];
