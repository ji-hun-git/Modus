import type { HistoryFact, ReviewedFact } from "./historyTypes";

export type Revision = { fact: HistoryFact; reason: string | null };
export type Preview = { preview_id: string; changes: Record<string, { before: string | null; after: string | null }> };
export type Request = { expected_revision_id: string; corrected: ReviewedFact; reason: string };
export type Commit = Request & { preview_id: string; reviewed: true };
export type CorrectionState = {
  versions: Revision[] | null; request: Request | null; preview: Preview | null;
  pending: Commit | null; busy: boolean; error: string; confirmed: boolean;
  savedAt: string | null; originScope: string; versionsScope: string; acknowledged: boolean; rejected: boolean;
};
const empty: CorrectionState = Object.freeze({ versions: null, request: null, preview: null,
  pending: null, busy: false, error: "", confirmed: false, savedAt: null,
  originScope: "", versionsScope: "", acknowledged: false, rejected: false });

/** Tab-lifetime transactions, independent of any source dialog or selected date.
 * Never persist medical text to browser storage or retry without an owner action.
 */
export function createCorrectionSession() {
  const records = new Map<string, CorrectionState>();
  const listeners = new Set<() => void>();
  let snapshot: readonly [string, CorrectionState][] = [];
  const session = {
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    getSnapshot: () => snapshot,
    get: (id: string): CorrectionState => records.get(id) || empty,
    patch(id: string, update: Partial<CorrectionState>) {
      records.set(id, { ...session.get(id), ...update });
      snapshot = [...records.entries()];
      listeners.forEach(listener => listener());
    },
    async save(id: string, send: (body: Commit) => Promise<{ available_at: string }>) {
      const current = session.get(id);
      if (current.busy || (!current.pending && (!current.request || !current.preview || !current.confirmed))) return;
      // A prior uncertain request is authoritative. Never rebuild it from edits.
      const body: Commit = current.pending || structuredClone({ ...current.request!,
        preview_id: current.preview!.preview_id, reviewed: true as const });
      session.patch(id, { pending: body, busy: true, error: "", acknowledged: false, rejected: false });
      try {
        const receipt = await send(structuredClone(body));
        session.patch(id, { savedAt: receipt.available_at, pending: null, request: null,
          preview: null, versions: null, confirmed: false });
      } catch (error) {
        const status = (error as { status?: number }).status;
        const rejected = status !== undefined && status >= 400 && status < 500 && ![408, 429].includes(status);
        session.patch(id, { error: (error as Error).message,
          ...(rejected ? { pending: null, preview: null, confirmed: false, rejected: true } : {}) });
      } finally { session.patch(id, { busy: false }); }
    },
  };
  return session;
}

export const correctionSession = createCorrectionSession();
