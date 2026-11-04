import { useRef } from "react";
import { orbitLayout, type HomeReportSummary } from "./homeReportData";
import { sourceDateRange, sourceTitle } from "./sourceDisplay";
import AmbientMotionControl from "./AmbientMotionControl";
import { sourceKind, sourceKindLabel } from "./svg/SourceGlyph";

export default function OrbitMap({ reports, selectedId, onSelect, total, compact = false, prominent = false, onOpenAll }: {
  reports: HomeReportSummary[];
  selectedId?: string;
  onSelect: (id: string) => void;
  total?: number;
  compact?: boolean;
  prominent?: boolean;
  onOpenAll?: () => void;
}) {
  const layout = orbitLayout(reports);
  const nodes = compact || prominent ? layout.nodes.map((node,index)=> {
    const angle=(-90+index*360/Math.max(layout.nodes.length,1))*Math.PI/180;
    // Distance means ownership, not a date scale. Equal spacing keeps separate
    // files selectable even when many reports share the same recorded year.
    return {...node,x:300+174*Math.cos(angle),y:222+174*Math.sin(angle)};
  }) : layout.nodes;
  const rings = compact || prominent ? nodes.length ? [{era:-1,radius:104},{era:-2,radius:174}] : [] : layout.rings;
  const buttons = useRef(new Map<string, SVGGElement>());
  const selected = nodes.find((node) => node.id === selectedId);
  const fileCount = `${total && total > reports.length ? `${reports.length} of ${total}` : reports.length} ${total === 1 || !total && reports.length === 1 ? 'file' : 'files'}`;
  const pickerLabels = new Map(reports.map(report => {
    const title = report.source.title;
    const duplicates = reports.filter(other => other.source.title === title);
    if (duplicates.length === 1) return [report.source.id, title];
    const dates = report.dateRange || sourceDateRange(report.facts);
    const sameDates = duplicates.filter(other => (other.dateRange || sourceDateRange(other.facts)) === dates);
    return [report.source.id, `${title} · ${dates}${sameDates.length > 1 ? ` · file ${sameDates.findIndex(other => other.source.id === report.source.id) + 1}` : ''}`];
  }));
  return (
    <section className={`orbit-map${compact?' orbit-map-compact':''}${prominent?' orbit-map-prominent':''}`} aria-label="Your source files in orbit">
      <header className="orbit-map-heading">
        <span>{prominent ? 'Your reports' : 'Your medical records'}</span>
        <div className="orbit-map-tools">{prominent && total && total > reports.length && onOpenAll
          ? <button type="button" className="text-button orbit-file-count" aria-label="All files" title="Open all source files" onClick={onOpenAll}>{fileCount}</button>
          : <span>{fileCount}</span>}<AmbientMotionControl compact /></div>
      </header>
      <svg className="orbit-chart" viewBox="0 0 600 480" role="group" aria-label="Select a source file">
        <g className="orbit-guides" aria-hidden="true">
          {rings.map((ring, index) => <circle key={ring.era} className="orbit-ring" cx="300" cy="222"
            r={ring.radius} pathLength="1" style={{ animationDelay: `${-index * 3}s` }} />)}
        </g>
        <g className="orbit-file-relations" aria-hidden="true">
          {nodes.filter(node => node.id !== selectedId).map(node =>
            <path key={node.id} d={`M300 222 L${node.x} ${node.y}`} />)}
        </g>
        <g className="orbit-ambient" aria-hidden="true">
          <g className="orbit-presence"><circle cx="300" cy="222" r="58" /></g>
        </g>
        {selected && <path key={selected.id} className="orbit-connection" aria-hidden="true"
          d={`M300 222 L${selected.x} ${selected.y}`} pathLength="1" />}
        <g className="orbit-owner" aria-label="You, at the center of your history">
          <circle cx="300" cy="222" r="49" />
          <circle className="orbit-owner-inner" cx="300" cy="222" r="42" />
          <text className="orbit-owner-label" x="300" y="214" textAnchor="middle" dominantBaseline="central">You</text>
          <text className="orbit-owner-count" x="300" y="238" textAnchor="middle">{total ?? reports.length} {(total ?? reports.length) === 1 ? 'file' : 'files'}</text>
        </g>
        {nodes.map((node, index) => {
          const report = reports.find((item) => item.source.id === node.id)!;
          const active = node.id === selectedId;
          const right = node.x >= 300;
          const outwardX = (node.x - 300) / 174;
          const outwardY = (node.y - 222) / 174;
          const yearAnchor = outwardX < -.2 ? 'end' : outwardX > .2 ? 'start' : 'middle';
          const kind = sourceKind(report.source.type || '', report.source.title);
          const format = sourceKindLabel(kind);
          return <g key={node.id} ref={(element) => { if (element) buttons.current.set(node.id, element); else buttons.current.delete(node.id); }}
            role="button" tabIndex={0} aria-pressed={active}
            aria-controls={prominent ? 'home-selected-report' : undefined}
            aria-label={`Open source file: ${report.source.title}; ${format}; ${report.dateRange || sourceDateRange(report.facts)}`}
            className={`orbit-satellite${active ? ' is-selected' : ''}`} transform={`translate(${node.x} ${node.y})`}
            onClick={() => onSelect(node.id)}
            onKeyDown={(event) => {
              if (['Enter', ' '].includes(event.key)) { event.preventDefault(); onSelect(node.id); }
              if (['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp'].includes(event.key)) {
                event.preventDefault();
                const step = ['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1;
                buttons.current.get(nodes[(index + step + nodes.length) % nodes.length].id)?.focus();
              }
            }}>
            <title>{`${report.source.title}; ${format}; ${report.dateRange || sourceDateRange(report.facts)}; ${report.count ?? report.facts.length} recorded items`}</title>
            <circle className="orbit-hit-area" r="23" />
            <circle className="orbit-node-presence" r="25" aria-hidden="true"
              style={{ animationDelay: `${-index * 1.3}s` }} />
            <g className="orbit-satellite-mark">
              <circle className="orbit-node-halo" r="17" />
              <path className="orbit-file-glyph" d="M-7-9 H3 L8-4 V10 H-7Z M3-9V-4H8" />
              <path className="orbit-file-glyph" d={kind === 'csv' ? 'M-4-1H5V7H-4Z M-4 3H5 M0-1V7'
                : kind === 'image' ? 'M-4 7L-1 2L2 5L4 2L6 7 M-3-2H-1'
                : 'M-3 0H4 M-3 4H4 M-3 7H1'} />
            </g>
            <text className="orbit-node-date" x={prominent ? outwardX * 35 : right ? 27 : -27}
              y={prominent ? outwardY * 35 : -6} textAnchor={prominent ? yearAnchor : right ? 'start' : 'end'}
              dominantBaseline={prominent ? 'central' : undefined}>
              {report.latestDate ? report.latestDate.slice(0, 4) : 'Undated'}
            </text>
            <text className="orbit-node-title" x={right ? 27 : -27} y="13" textAnchor={right ? 'start' : 'end'}>
              {(report.displayLabel || sourceTitle(report.facts)).length > 18 ? (report.displayLabel || sourceTitle(report.facts)).slice(0, 17) + '…' : (report.displayLabel || sourceTitle(report.facts))}
            </text>
          </g>;
        })}
        {!reports.length && <text className="orbit-empty" x="300" y="374" textAnchor="middle">0 source files — add the first</text>}
      </svg>
      {(compact || prominent) && !!reports.length && <label className="orbit-file-picker">Open a report
        <select value={selectedId || ''} onChange={event=>onSelect(event.target.value)}>
          {reports.map(report=><option key={report.source.id} value={report.source.id}>{pickerLabels.get(report.source.id)}</option>)}
        </select>
      </label>}
      {!prominent && <footer><span>One satellite. One source file.</span>
        {total && total > reports.length && onOpenAll ? <button type="button" className="text-button" onClick={onOpenAll}>All files</button>
          : !prominent && <span>Each file belongs to your history.</span>}</footer>}
    </section>
  );
}
