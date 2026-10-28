import type { HistoryFact, HistoryView } from "./historyTypes";

export type BriefRequest = {
  as_of: string | null;
  known_at: string;
  selected_fact_ids: string[];
  title: string;
  owner_note: string;
};

export type BriefEntry = HistoryFact & {
  citation: string;
  source_citation: string;
  selected_by_owner: boolean;
  added_for_conflict: boolean;
};

export type RecordBriefData = {
  format: "modus-record-brief-v1";
  preview_id: string;
  title: string;
  owner_note: string;
  scope: HistoryView["scope"];
  generated_at: string;
  entries: BriefEntry[];
  sources: (HistoryView["sources"][number] & { citation: string })[];
  conflicts: HistoryView["conflicts"];
  warnings: string[];
  counts: {
    selected: number;
    conflict_companions: number;
    total: number;
    sources: number;
  };
  history_evidence: HistoryView;
};
