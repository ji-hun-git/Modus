import type { HistoryComparison, HistoryView } from "./historyTypes";
export type ReplayRequest = {
  as_of: string | null;
  before_known_at: string;
  after_known_at: null;
};
export function replayRequest(scope: HistoryView["scope"]): ReplayRequest;
export function replayMatchesRequest(
  comparison: HistoryComparison,
  request: ReplayRequest,
): boolean;
