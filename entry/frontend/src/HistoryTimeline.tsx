import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CalendarDays,
  LoaderCircle,
  RefreshCw,
} from "lucide-react";
import { dateLabel, timeLabel } from "./ui";
import type { Scope } from "./types";
import {
  factKindLabels,
  type HistoryFact,
  type HistoryView,
} from "./historyTypes";
import TimelineFact, { exactDate } from "./TimelineFact";
import TimelineSettings from "./TimelineSettings";
import PagedFiles from "./PagedFiles";
import HistoryPager from "./HistoryPager";
import HistoryQuestionPanel from "./HistoryQuestionPanel";
import useHistoryView from "./useHistoryView";
import {RetrievalFeedback} from './TerminologyDetails';
import { facilityLabel, localCalendarDay } from "./recordPresentation.mjs";
import "./history-timeline.css";

export default function HistoryTimeline({
  scope,
  onLatest,
  viewMode = "timeline",
  onScope,
}: {
  scope: Scope;
  onLatest: () => void;
  viewMode?: "timeline" | "files";
  onImport?: () => void;
  hasDraft?: boolean;
  onScope?: (scope: HistoryView["scope"]) => void;
}) {
  const [kind, setKind] = useState("all");
  const [facility, setFacility] = useState("all");
  const [order, setOrder] = useState("newest");
  const [query, setQuery] = useState('');
  const previousAsOf = useRef(scope.as_of);
  const [allDates, setAllDates] = useState(
    () => scope.as_of === localCalendarDay(),
  );
  const effectiveAllDates = previousAsOf.current === scope.as_of && allDates;
  useEffect(() => {
    if (previousAsOf.current !== scope.as_of) {
      previousAsOf.current = scope.as_of;
      setAllDates(false);
    }
  }, [scope.as_of]);
  const { view: loadedView, metadata, error, refresh, setOffset } = useHistoryView(scope, effectiveAllDates, {
    section: viewMode === 'files' ? 'sources' : 'facts', limit: viewMode === 'files' ? 12 : 50,
    kind: kind === 'all' ? undefined : kind, facility: facility === 'all' ? undefined : facility, order, query });
  const view = loadedView || metadata;
  useEffect(() => {
    if (view) onScope?.(view.scope);
  }, [view, onScope]);
  if (error)
    return (
      <div className="panel empty" role="alert">
        <AlertCircle size={24} />
        <h2>These records could not be loaded</h2>
        <p>{error}</p>
        <button className="secondary" onClick={refresh}>
          Retry this view
        </button>
      </div>
    );
  if (!view)
    return (
      <div className="panel loading" role="status">
        <LoaderCircle className="spin" size={24} /> Loading your records…
      </div>
    );
  const dateControl = (
    <div className="history-date-toggle">
      <label className="check-row">
        <input
          type="checkbox"
          checked={effectiveAllDates}
          onChange={(event) => setAllDates(event.target.checked)}
        />
        All recorded dates
      </label>
      <p>
        {effectiveAllDates
          ? "Includes partial and unknown dates. File availability stays fixed to this view."
          : `Records through ${dateLabel(scope.as_of)}. Values that cannot be placed within this period stay hidden.`}
      </p>
    </div>
  );
  if (viewMode === "files")
    return (
      <>
        <HistoryQuestionPanel view={view} />
        {dateControl}
        <label>Search documents<input aria-label="Search documents" value={query} onChange={e => setQuery(e.target.value)} /></label>
        <RetrievalFeedback retrieval={loadedView?.retrieval} onChoose={setQuery} />
        <HistoryPager view={view} onPage={setOffset} noun="files" />
        <PagedFiles view={view} />
        <HistoryPager view={view} onPage={setOffset} noun="files" />
      </>
    );
  const matches = (fact: HistoryFact) =>
    (kind === "all" || fact.kind === kind) &&
    (facility === "all" || fact.facility === facility);
  const dated = view.facts.filter(matches).sort((a, b) => {
    const result =
      (exactDate(a) || "").localeCompare(exactDate(b) || "") ||
      a.id.localeCompare(b.id);
    return order === "newest" ? -result : result;
  });
  const undated = view.undated_facts.filter(matches);
  const visibleFileCount = new Set(
    [...dated, ...undated].map((fact) => fact.source_id),
  ).size;
  const years = [
    ...new Set(
      dated.map((fact) => exactDate(fact)?.slice(0, 4) || "Date not recorded"),
    ),
  ];
  const facilities = view.facets?.facilities || [
    ...new Set(
      [...view.facts, ...view.undated_facts].flatMap((fact) =>
        facilityLabel(fact.facility) ? [fact.facility!] : [],
      ),
    ),
  ].sort();
  const conflicts = new Set(
    view.conflicts.flatMap((conflict) => conflict.fact_ids || []),
  );
  return (
    <section className="history-timeline" aria-label="Record timeline">
      <header className="timeline-heading">
        <div>
          <h2>Recorded history</h2>
          <p>
            {view.page?.matched_sources ?? visibleFileCount} documents · {view.page?.total ?? dated.length + undated.length} matching records
          </p>
        </div>
        <button className="text-button" onClick={refresh}>
          <RefreshCw size={14} /> Refresh
        </button>
      </header>
      {dateControl}
      <label>Search records<input aria-label="Search records" value={query} onChange={e => setQuery(e.target.value)} /></label>
      <RetrievalFeedback retrieval={loadedView?.retrieval} onChoose={setQuery} />
      <HistoryPager view={view} onPage={setOffset} />
      {!loadedView && <p role="status">Loading matching records…</p>}
      <HistoryQuestionPanel view={view} />
      <div className="timeline-filters">
        <label className="field">
          Record type
          <select
            value={kind}
            onChange={(event) => setKind(event.target.value)}
          >
            <option value="all">All types</option>
            {Object.entries(factKindLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Facility
          <input list="history-facilities" value={facility === 'all' ? '' : facility}
            placeholder="All facilities" onChange={event => setFacility(event.target.value || 'all')} />
          <datalist id="history-facilities">
            {facilities.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </datalist>
        </label>
        <label className="field">
          Order
          <select
            value={order}
            onChange={(event) => setOrder(event.target.value)}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </label>
      </div>
      {loadedView && !dated.length && !undated.length && (
        <div className="workspace-empty">
          <CalendarDays size={28} />
          <h3>No matching records in this view</h3>
          <p>Try another type, facility or date range.</p>
        </div>
      )}
      {years.map((year) => (
        <section className="timeline-year" key={year}>
          <h2>{year}</h2>
          <div className="timeline-facts">
            {dated
              .filter(
                (fact) =>
                  (exactDate(fact)?.slice(0, 4) || "Date not recorded") ===
                  year,
              )
              .map((fact) => (
                <TimelineFact
                  key={fact.id}
                  fact={fact}
                  view={view}
                  conflict={conflicts.has(fact.id)}
                  conflictReason={
                    view.conflicts.find((item) =>
                      item.fact_ids.includes(fact.id),
                    )?.reason
                  }
                />
              ))}
          </div>
        </section>
      ))}
      {!!undated.length && (
        <section className="timeline-undated">
          <h2>Dates not fully known</h2>
          <p>
            These records have partial or unknown dates. They are kept separate
            from the dated timeline.
          </p>
          <div className="timeline-facts">
            {undated.map((fact) => (
              <TimelineFact
                key={fact.id}
                fact={fact}
                view={view}
                conflict={conflicts.has(fact.id)}
                conflictReason={
                  view.conflicts.find((item) => item.fact_ids.includes(fact.id))
                    ?.reason
                }
              />
            ))}
          </div>
        </section>
      )}
      <p className="timeline-scope">
        {view.scope.as_of
          ? `Recorded through ${dateLabel(view.scope.as_of)}`
          : "All recorded dates"}{" "}
        · Files available through {timeLabel(scope.known_at)}
      </p>
      <HistoryPager view={view} onPage={setOffset} />
      <TimelineSettings
        key={scope.known_at}
        dateOfBirth={view.profile?.date_of_birth || null}
        onLatest={onLatest}
      />
    </section>
  );
}
