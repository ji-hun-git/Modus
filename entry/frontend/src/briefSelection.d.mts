import type { HistoryFact, HistoryView } from "./historyTypes";
import type { BriefRequest, RecordBriefData } from "./briefTypes";

export const MAX_BRIEF_SELECTION: number;
export function eligibleBriefFacts(view: HistoryView): HistoryFact[];
export function briefRequest(
  view: HistoryView,
  selectedIds: string[],
  title: string,
  ownerNote: string,
): BriefRequest | null;
export function briefRequestKey(
  view: HistoryView,
  selectedIds: string[],
  title: string,
  ownerNote: string,
): string;
export function briefMatchesRequest(
  brief: RecordBriefData,
  request: BriefRequest | null,
): boolean;
export function reviewedBriefExport(
  brief: RecordBriefData,
  request: BriefRequest | null,
  reviewed: boolean,
  format?: "html" | "json",
):
  | (BriefRequest & {
      preview_id: string;
      reviewed: true;
      format: "html" | "json";
    })
  | null;
