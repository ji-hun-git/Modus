import { useRef } from "react";
import { orbitLayout, type HomeReportSummary } from "./homeReportData";
import { sourceDateRange, sourceTitle } from "./sourceDisplay";
import AmbientMotionControl from "./AmbientMotionControl";

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
  const rings = layout.rings;
  const nodes = compact || prominent ? layout.nodes.map((node,index)=> {
    if (prominent && node.era === null) return { ...node, y: 430 };
    const radius = rings.find(ring=>ring.era===node.era)?.radius ?? 208;
    const angle=(-90+index*360/Math.max(layout.nodes.length,1))*Math.PI/180;
    return {...node,x:300+radius*Math.cos(angle),y:222+radius*Math.sin(angle)};
  }) : layout.nodes;
  const buttons = useRef(new Map<string, SVGGElement>());
  const selected = nodes.find((node) => node.id === selectedId);
  return (
    <section className={`orbit-map${compact?' orbit-map-compact':''}${prominent?' orbit-map-prominent':''}`} aria-label="Your source files in orbit">
      <header className="orbit-map-heading">
        <span>{prominent ? 'Your files, through the years' : 'Your medical records'}</span>
        <div className="orbit-map-tools"><span>{total && total > reports.length ? `${reports.length} of ${total}` : reports.length} {total === 1 || !total && reports.length === 1 ? 'file' : 'files'}</span><AmbientMotionControl compact /></div>
      </header>
      <svg className="orbit-chart" viewBox="0 0 600 480" role="group" aria-label="Select a source file">
        <g className="orbit-guides" aria-hidden="true">
          <path d="M300 18V426 M76 222H524" />
          {rings.map((ring) => <g key={ring.era}>
            <circle className="orbit-ring" cx="300" cy="222" r={ring.radius} pathLength="1" />
            <text x={prominent ? 12 : 308} y={222 - ring.radius + 14}>{ring.label}</text>
          </g>)}
          <path className="orbit-crosshair" d="M288 18H312 M288 426H312 M76 210V234 M524 210V234" />
        </g>
        <g className="orbit-ambient" aria-hidden="true">
          {rings.map((ring, index) => <g key={ring.era} className="orbit-drift"
            style={{ animationDuration: `${48 + index * 14}s`, animationDelay: `${-index * 11}s` }}>
            <circle cx="300" cy={222 - ring.radius} r="2.2" />
          </g>)}
          <g className="orbit-presence"><circle cx="300" cy="222" r="58" /></g>
        </g>
        {selected && <path key={selected.id} className="orbit-connection" aria-hidden="true"
          d={`M300 222 L${selected.x} ${selected.y}`} pathLength="1" />}
        <g className="orbit-owner" aria-label="You, at the center of your history">
          <circle cx="300" cy="222" r="49" />
          <circle className="orbit-owner-inner" cx="300" cy="222" r="42" />
          <text className="orbit-owner-label" x="300" y="222" textAnchor="middle" dominantBaseline="central">You</text>
        </g>
        {nodes.map((node, index) => {
          const report = reports.find((item) => item.source.id === node.id)!;
          const active = node.id === selectedId;
          const right = node.x >= 300;
          return <g key={node.id} ref={(element) => { if (element) buttons.current.set(node.id, element); else buttons.current.delete(node.id); }}
            role="button" tabIndex={0} aria-pressed={active}
            aria-controls={prominent ? 'home-selected-report' : undefined}
            aria-label={`Open source file: ${report.source.title}; ${report.dateRange || sourceDateRange(report.facts)}`}
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
            <title>{`${report.source.title} · ${report.count ?? report.facts.length} recorded items`}</title>
            <circle className="orbit-hit-area" r="23" />
            <circle className="orbit-node-presence" r="25" aria-hidden="true"
              style={{ animationDelay: `${-index * 1.3}s` }} />
            <g className="orbit-satellite-mark">
              <circle className="orbit-node-halo" r="17" />
              <path className="orbit-file-glyph" d="M-7-9 H3 L8-4 V10 H-7Z M3-9V-4H8 M-3 1H4 M-3 5H4" />
            </g>
            <text className="orbit-node-date" x={prominent ? 0 : right ? 27 : -27} y={prominent ? 38 : -6} textAnchor={prominent ? 'middle' : right ? 'start' : 'end'}>
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
          {reports.map(report=><option key={report.source.id} value={report.source.id}>{report.source.title}</option>)}
        </select>
      </label>}
      {(!prominent || !!total && total > reports.length) && <footer><span>{prominent ? 'More files are available in Records.' : 'One satellite. One source file.'}</span>
        {total && total > reports.length && onOpenAll ? <button type="button" className="text-button" onClick={onOpenAll}>All files</button>
          : !prominent && <span>Rings group recorded years.</span>}</footer>}
    </section>
  );
}
