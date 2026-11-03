import { useEffect, useRef, useState } from "react";
import { FileText, History, Inbox, MessageSquare } from "lucide-react";
import type { HistoryView } from "./historyTypes";
import type { Page } from "./Shell";
import { dateLabel, timeLabel } from "./ui";
import { dateDay, dayDate } from "./homeReportData";

export type KnowledgeMode = "latest" | "then" | "custom";

export default function HomeIntegrityTools({
  scope, dates, currentDay, knowledge, pendingCount, onDate, onNavigate, onReview,
  orbit = false, requestedDate, updating = false, onCurrent, onPreview,
}: {
  scope: HistoryView["scope"];
  dates: string[];
  currentDay: string;
  knowledge: KnowledgeMode;
  pendingCount: number;
  onDate: (date: string, knowledge: KnowledgeMode) => void;
  onNavigate: (page: Page) => void;
  onReview: () => void;
  orbit?: boolean;
  requestedDate?: string;
  updating?: boolean;
  onCurrent?: () => void;
  onPreview?: (date: string) => void;
}) {
  const [date, setDate] = useState(requestedDate || scope.as_of || currentDay);
  const [mode, setMode] = useState(knowledge);
  const dragging = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queued = useRef<{ day: string; mode: KnowledgeMode } | null>(null);
  const last = useRef({ at: 0, day: requestedDate || scope.as_of || currentDay, mode: knowledge });
  const send = useRef(onDate);
  send.current = onDate;
  useEffect(() => {
    if (!dragging.current) {
      const next = requestedDate || scope.as_of || currentDay;
      setDate(next);
      last.current = { ...last.current, day: next, mode: knowledge };
    }
    setMode(knowledge);
  }, [requestedDate, scope.as_of, currentDay, knowledge]);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  const dated = [...new Set(dates.filter((day) => dateDay(day) !== null && day <= currentDay))].sort();
  const points = [...new Set([...dated, currentDay])].sort();
  const min = dateDay(points[0])!, max = dateDay(currentDay)!;
  const position = Math.max(min, Math.min(max, dateDay(date) ?? max));
  const apply = (day = date, nextMode = mode) => {
    if (dateDay(day) !== null && day <= currentDay) {
      onPreview?.(day);
      if (timer.current) clearTimeout(timer.current);
      timer.current = null; queued.current = null;
      last.current = { at: Date.now(), day, mode: nextMode };
      send.current(day, nextMode);
    }
  };
  const flush = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    const next = queued.current;
    queued.current = null;
    if (next && (last.current.day !== next.day || last.current.mode !== next.mode)) apply(next.day, next.mode);
  };
  const scrub = (day: string) => {
    setDate(day);
    onPreview?.(day);
    queued.current = { day, mode };
    const remaining = 120 - (Date.now() - last.current.at);
    if (remaining <= 0) flush();
    else if (!timer.current) timer.current = setTimeout(flush, remaining);
  };
  const timeline = <div className="home-replay-track">
    <input type="range" aria-label="Scrub recorded history" min={min} max={max}
      step={1} value={position} disabled={points.length < 2}
      aria-valuetext={dateLabel(date)}
      onPointerDown={() => { dragging.current = true; }}
      onChange={(event) => scrub(dayDate(Number(event.target.value)))}
      onPointerUp={() => { dragging.current = false; flush(); }}
      onPointerCancel={() => { dragging.current = false; flush(); }}
      onBlur={() => { dragging.current = false; flush(); }}
      onKeyDown={() => { dragging.current = true; }}
      onKeyUp={() => { dragging.current = false; flush(); }} />
    {orbit && <div className="orbit-time-ticks" aria-hidden="true">{points.map((day) => <i key={day} style={{left:`${max === min ? 0 : (dateDay(day)! - min) / (max - min) * 100}%`}} />)}</div>}
    <div><span>{dated.length ? dateLabel(points[0]) : "No dated records"}</span><span>{dateLabel(currentDay)}</span></div>
  </div>;
  const dateControls = <>
    <label>Recorded through
      <input type="date" aria-label="Home record date" max={currentDay} value={date}
        onChange={(event) => setDate(event.target.value)} />
    </label>
    <label>Use files available
      <select aria-label="Home file availability" value={mode} onChange={(event) => setMode(event.target.value as KnowledgeMode)}>
        <option value="latest">Now</option>
        <option value="then">By that date</option>
        {knowledge === "custom" && <option value="custom">At the selected availability</option>}
      </select>
    </label>
    <button type="button" className="text-button" onClick={() => apply()} disabled={dateDay(date) === null || date > currentDay}>View this date</button>
  </>;
  if (orbit) return <section className="home-integrity-tools orbit-telemetry" aria-label="History controls">
    <header className="orbit-timeline-heading">
      <div><span>Recorded dates</span><strong><output aria-label="Selected history date">{date !== currentDay || scope.as_of ? `Through ${dateLabel(date)}` : 'All recorded dates'}</output></strong></div>
      <div><span>Files available through</span><strong><time dateTime={scope.known_at}>{timeLabel(scope.known_at)}</time></strong></div>
      <div className="home-time-feedback"><span role="status">{updating ? 'Updating records…' : ''}</span>
        {onCurrent && <button type="button" className="text-button" onClick={() => { dragging.current = false; if (timer.current) clearTimeout(timer.current); timer.current = null; queued.current = null; setDate(currentDay); setMode('latest'); onPreview?.(currentDay); onCurrent(); }} disabled={date === currentDay && knowledge === 'latest'}>Today</button>}
      </div>
    </header>
    {timeline}
    <details className="orbit-history-options">
      <summary>More history tools</summary>
      <div className="home-replay-controls">{dateControls}</div>
      <div className="home-integrity-actions">
        <button type="button" className="secondary" onClick={() => onNavigate("Replay")}>
          <History size={15} aria-hidden="true" /> Compare past views
        </button>
      </div>
    </details>
  </section>;
  return (
    <section className="home-integrity-tools" aria-label="History controls">
      <div className="home-integrity-actions">
        <button type="button" className="secondary" onClick={onReview}>
          <Inbox size={15} aria-hidden="true" /> Review queue <span>{pendingCount}</span>
        </button>
        <button type="button" className="secondary" onClick={() => onNavigate("Replay")}>
          <History size={15} aria-hidden="true" /> Replay
        </button>
        <button type="button" className="secondary" onClick={() => onNavigate("Brief")}>
          <FileText size={15} aria-hidden="true" /> Prepare a brief / export
        </button>
        <button type="button" className="secondary" onClick={() => onNavigate("Ask")}>
          <MessageSquare size={15} aria-hidden="true" /> Ask your records
        </button>
      </div>
      <div className="home-replay-controls">
        {dateControls}
        {timeline}
      </div>
      <div className="home-integrity-notes">
        <span>Files available through {timeLabel(scope.known_at)} · Queue is for this session.</span>
        <span>Ask cites your records, or says when it cannot answer.</span>
      </div>
    </section>
  );
}
