import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Scope } from "./types";
import type { HistoryView } from "./historyTypes";

export type PageOptions = { section?: 'facts' | 'sources' | 'fields'; limit?: number; snapshot_id?: string;
  kind?: string; label?: string; facility?: string; source_id?: string; order?: string; query?: string;
  conflict_id?: string; through?: string; conflicts_only?: boolean; enabled?: boolean; unpaged?: boolean };

export function historyPageQuery(scope: HistoryView['scope'] | Scope, allDates: boolean, options: PageOptions, offset: number, snapshot?: string) {
  const query = new URLSearchParams();
  if (snapshot) query.set('snapshot_id', snapshot);
  else { query.set('known_at', scope.known_at); if (!allDates && scope.as_of) query.set('as_of', scope.as_of); }
  for (const [key, value] of Object.entries(options)) {
    if (!['enabled','unpaged','snapshot_id'].includes(key) && value !== undefined && value !== '') query.set(key,String(value));
  }
  query.set('offset',String(offset));
  return query;
}

export default function useHistoryView(scope: HistoryView['scope'] | Scope, allDates: boolean, options: PageOptions = {}) {
  const [version, setVersion] = useState(0);
  const [renewedFor, setRenewedFor] = useState<string | null>(null);
  const [position, setPosition] = useState({ key: '', offset: 0 });
  const [loaded, setLoaded] = useState<{ key: string; captureKey: string; view: HistoryView } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const captureKey = `${scope.as_of}|${allDates}|${scope.known_at}|${version}|${options.snapshot_id || ''}`;
  const capture = useRef<{ key: string; id: string } | null>(null);
  const filterKey = `${captureKey}|${JSON.stringify(options)}`;
  const offset = position.key === filterKey ? position.offset : 0;
  const key = `${filterKey}|${offset}`;
  useEffect(() => {
    if (options.enabled === false) return;
    const controller = new AbortController();
    setFailure(null);
    const snapshot = (options.snapshot_id !== renewedFor ? options.snapshot_id : undefined) || (capture.current?.key === captureKey ? capture.current.id : undefined);
    const query = historyPageQuery(scope, allDates, options, offset, options.unpaged ? undefined : snapshot);
    void api<HistoryView>(`/history/${options.unpaged ? 'view' : 'page'}?${query}`, { signal: controller.signal })
      .then(view => {
        if (controller.signal.aborted) return;
        if (view.page) capture.current = { key: captureKey, id: view.page.snapshot_id };
        setLoaded({ key, captureKey, view });
      }).catch((error: Error) => { if (!controller.signal.aborted) setFailure({ key, message: error.message }); });
    return () => controller.abort();
  }, [key]);
  return { view: options.enabled !== false && loaded?.key === key ? loaded.view : null,
    metadata: loaded?.captureKey === captureKey ? { ...loaded.view, facts: [], undated_facts: [], sources: [], conflicts: [], fields: [], retrieval: null,
      page: loaded.view.page ? {...loaded.view.page, total: 0, returned: 0, next_offset:null,previous_offset:null} : undefined } as HistoryView : null,
    error: failure?.key === key ? failure.message : null,
    setOffset: (next: number) => setPosition({ key: filterKey, offset: next }),
    refresh: () => { capture.current = null; setRenewedFor(options.snapshot_id || null); setVersion(value => value + 1); } };
}
