import { useEffect, useState } from "react";
import { api } from "./api";
import type { Scope } from "./types";
import type { HistoryView } from "./historyTypes";

export default function useHistoryView(scope: Scope, allDates: boolean) {
  const [version, setVersion] = useState(0);
  const [loaded, setLoaded] = useState<{
    key: string;
    view: HistoryView;
  } | null>(null);
  const [failure, setFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const asOf = allDates ? null : scope.as_of;
  const key = `${scope.as_of}|${asOf}|${scope.known_at}|${version}`;
  useEffect(() => {
    const controller = new AbortController();
    setFailure(null);
    const query = new URLSearchParams({ known_at: scope.known_at });
    if (asOf !== null) query.set("as_of", asOf);
    void api<HistoryView>(`/history/view?${query}`, {
      signal: controller.signal,
    })
      .then((view) => {
        if (!controller.signal.aborted) setLoaded({ key, view });
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted)
          setFailure({ key, message: error.message });
      });
    return () => controller.abort();
  }, [key, asOf, scope.known_at]);
  return {
    view: loaded?.key === key ? loaded.view : null,
    error: failure?.key === key ? failure.message : null,
    refresh: () => setVersion((value) => value + 1),
  };
}
