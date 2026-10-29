import { useId } from "react";
import SourceGlyph from "./SourceGlyph";

export default function Lifeline({ sources }: {
  sources: { id: string; title: string; date?: string }[];
  firstYear?: string; lastYear?: string;
}) {
  const titleId = useId();
  const points = sources.map((source) => {
    const time = source.date && /^\d{4}-\d{2}-\d{2}$/.test(source.date)
      ? Date.parse(source.date + "T00:00:00Z") : NaN;
    const valid = Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === source.date;
    return { ...source, time: valid ? time : null };
  });
  const dated = points.filter((point) => point.time !== null).sort((a, b) => a.time! - b.time!);
  const undated = points.filter((point) => point.time === null);
  const first = dated[0]?.time ?? 0;
  const last = dated.at(-1)?.time ?? first;
  const end = undated.length ? 760 : 950;
  const xFor = (time: number) => first === last ? (50 + end) / 2 : 50 + (time - first) / (last - first) * (end - 50);
  const years = [...new Set(dated.map((point) => point.date!.slice(0, 4)))];
  const sameDateCounts = new Map<number, number>();
  const positioned = dated.map((point) => {
    const stack = sameDateCounts.get(point.time!) ?? 0;
    sameDateCounts.set(point.time!, stack + 1);
    return { ...point, x: xFor(point.time!), stack };
  });
  const rows = Math.max(1, ...sameDateCounts.values(), Math.ceil(undated.length / 4));
  const baseline = 70 + (rows - 1) * 38;
  return (
    <figure className="home-lifeline">
      {/* The 1000-unit horizontal grid maps elapsed days; stacked marks retain their date. */}
      <svg viewBox={"0 0 1000 " + (baseline + 40)} role="img" aria-labelledby={titleId}
        fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
        <title id={titleId}>{sources.length} source files across recorded dates{years.length ? ", " + years[0] + " to " + years.at(-1) : ""}</title>
        <line className="lifeline-baseline" x1="26" y1={baseline} x2="974" y2={baseline} />
        {positioned.map((point) => <g key={point.id}>
          <title>{point.title}: {point.date}</title>
          <line x1={point.x} x2={point.x} y1={baseline - 9 - point.stack * 38} y2={baseline} />
          <circle cx={point.x} cy={baseline} r="3.5" fill="var(--canvas)" />
          <g transform={"translate(" + (point.x - 12) + "," + (baseline - 48 - point.stack * 38) + ")"}><SourceGlyph kind="unknown" size={24} /></g>
        </g>)}
        {years.map((year) => {
          const point = dated.find((item) => item.date!.startsWith(year))!;
          return <text key={year} x={xFor(point.time!)} y={baseline + 28} textAnchor="middle">{year}</text>;
        })}
        {undated.map((point, index) => <g key={point.id}>
          <title>{point.title}: exact date not recorded</title>
          <g transform={"translate(" + (825 + index % 4 * 36) + "," + (baseline - 48 - Math.floor(index / 4) * 38) + ")"}><SourceGlyph kind="unknown" size={24} /></g>
          <circle cx={837 + index % 4 * 36} cy={baseline} r="3.5" fill="var(--canvas)" />
        </g>)}
        {!!undated.length && <text x="888" y={baseline + 28} textAnchor="middle">Exact date not recorded</text>}
      </svg>
      <figcaption>Ticks = source files <span>· Earliest recorded date per file</span></figcaption>
    </figure>
  );
}
