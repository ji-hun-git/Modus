import { useState } from "react";
import { FileText, History, Inbox, MessageSquare } from "lucide-react";
import type { HistoryView } from "./historyTypes";
import type { Page } from "./Shell";
import { dateLabel, timeLabel } from "./ui";
import { dateDay, dayDate } from "./homeReportData";

export type KnowledgeMode = "latest" | "then" | "custom";

export default function HomeIntegrityTools({
  scope, dates, currentDay, knowledge, pendingCount, onDate, onNavigate, onReview,
  orbit = false,
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
}) {
  const [date, setDate] = useState(scope.as_of || currentDay);
  const [mode, setMode] = useState(knowledge);
  const dated = [...new Set(dates.filter((day) => dateDay(day) !== null && day <= currentDay))].sort();
  const points = [...new Set([...dated, currentDay])].sort();
  const min = dateDay(points[0])!, max = dateDay(currentDay)!;
  const position = Math.max(min, Math.min(max, dateDay(date) ?? max));
  const apply = (day = date, nextMode = mode) => {
    if (dateDay(day) !== null && day <= currentDay) onDate(day, nextMode);
  };
  const timeline = <div className="home-replay-track">
    <input type="range" aria-label="Scrub recorded history" min={min} max={max}
      step={1} value={position} disabled={points.length < 2}
      aria-valuetext={dateLabel(date)}
      onChange={(event) => setDate(dayDate(Number(event.target.value)))}
      onPointerUp={(event) => apply(dayDate(Number(event.currentTarget.value)))}
      onKeyUp={(event) => { if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End", "PageUp", "PageDown"].includes(event.key)) apply(dayDate(Number(event.currentTarget.value))); }} />
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
      <div><span>Your timeline</span><strong>{scope.as_of ? `Through ${dateLabel(scope.as_of)}` : 'All recorded dates'}</strong></div>
    </header>
    {timeline}
    <details className="orbit-history-options">
      <summary>History options <span>{knowledge === 'latest' ? 'Files available now' : `Files available ${dateLabel(scope.known_at.slice(0, 10))}`}</span></summary>
      <div className="home-replay-controls">{dateControls}</div>
      <div className="home-integrity-actions">
        {pendingCount > 0 && <button type="button" className="secondary" onClick={onReview}>
          <Inbox size={15} aria-hidden="true" /> Continue review <span>{pendingCount}</span>
        </button>}
        <button type="button" className="secondary" onClick={() => onNavigate("Replay")}>
          <History size={15} aria-hidden="true" /> Compare past views
        </button>
        <button type="button" className="secondary" onClick={() => onNavigate("Brief")}>
          <FileText size={15} aria-hidden="true" /> Prepare a brief
        </button>
      </div>
      <p className="home-integrity-notes">Files available through {timeLabel(scope.known_at)}.{pendingCount > 0 && ' Unsaved reviews stay in this tab.'}</p>
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
