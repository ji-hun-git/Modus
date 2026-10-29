export type SourceKind = "pdf" | "image" | "csv" | "text" | "unknown";

export function sourceKind(type: string, title: string): SourceKind {
  const format = type.toLowerCase();
  if (format.includes("pdf") || /\.pdf$/i.test(title)) return "pdf";
  if (format.startsWith("image") || /\.(png|jpe?g|webp|tiff?)$/i.test(title)) return "image";
  if (format.includes("csv") || /\.csv$/i.test(title)) return "csv";
  if (format === "text" || format.startsWith("text/plain") || /\.txt$/i.test(title)) return "text";
  return "unknown";
}
export const sourceKindLabel = (kind: SourceKind) =>
  ({ pdf: "PDF", image: "IMG", csv: "CSV", text: "TXT", unknown: "FILE" })[kind];

export default function SourceGlyph({ kind, size = 32, active = false }: {
  kind: SourceKind; size?: number; active?: boolean;
}) {
  // The 24 × 28 grid leaves room for a folded document corner.
  return (
    <svg width={size} height={size * 28 / 24} viewBox="0 0 24 28" fill="none"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true" focusable="false" data-active={active || undefined}>
      <path d="M4 2h11l5 5v19H4ZM15 2v6h5" />
      {kind === "image" ? <><circle cx="9" cy="13" r="1.5" /><path d="m6.5 22 4-5 2.5 3 2-2 2.5 4" /></>
        : kind === "csv" ? <path d="M7 12h10v10H7ZM7 17h10M12 12v10" />
        : <><path d="M8 13h8M8 17h8M8 21h5" />{kind === "pdf" && <path d="M8 10h3" />}</>}
    </svg>
  );
}
