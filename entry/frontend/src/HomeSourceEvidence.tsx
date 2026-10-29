import { useState } from "react";
import { ArrowUpRight, FileText } from "lucide-react";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { reportSummaries } from "./homeReportData";
import { recordLabel } from "./types";
import { unitLabel } from "./recordPresentation.mjs";
import {
  originalDownloadUrl,
  recordedDate,
  reviewedFieldLabel,
  sourceExcerpt,
  sourcePage,
  sourceTitle,
} from "./sourceDisplay";
import { dateLabel } from "./ui";
import { sourceKind } from "./svg/SourceGlyph";

export default function HomeSourceEvidence({
  fact,
  view,
  onOpen,
}: {
  fact: HistoryFact;
  view: HistoryView;
  onOpen: (fact: HistoryFact) => void;
}) {
  const [failedImage, setFailedImage] = useState<string | null>(null);
  const source = view.sources.find((item) => item.id === fact.source_id);
  if (!source) return <p>This source is not available in this view.</p>;
  const facts =
    reportSummaries(view).find((item) => item.source.id === source.id)?.facts ||
    [];
  const page = sourcePage(fact, source);
  const imageUrl =
    source.original_available &&
    !fact.value_withheld &&
    !fact.source_quote_withheld &&
    sourceKind(source.type, source.title) === "image"
      ? originalDownloadUrl(source.id, view.scope)
      : null;
  return (
    <section
      className="home-source-proof"
      aria-label={"Source evidence for " + recordLabel(fact.label)}
    >
      <header className="home-proof-heading">
        <FileText
          size={17}
          strokeWidth={1.5}
          aria-hidden="true"
          focusable="false"
        />
        <span>Source evidence</span>
        {page != null && <span>p. {page}</span>}
      </header>
      <div className="home-proof-body">
        <span className="home-proof-context">
          {sourceTitle(facts)} · {recordedDate(fact)}
        </span>
        <h3>{recordLabel(fact.label)}</h3>
        <p className="home-proof-value">
          {fact.value_withheld
            ? "Hidden by date filter"
            : (fact.value ?? "Not recorded")}
          {!fact.value_withheld && fact.unit && (
            <small>{unitLabel(fact.unit)}</small>
          )}
        </p>
        <div className="home-proof-excerpt">
          <span>As written in your record</span>
          <blockquote>{sourceExcerpt(fact)}</blockquote>
        </div>
        {!!fact.reviewed_fields?.length && (
          <p className="home-proof-edited">
            {fact.previous_revision_id ? "Corrected after saving" : "Edited during review"}:{" "}
            {fact.reviewed_fields.map(reviewedFieldLabel).join(", ")}. The
            excerpt keeps the original wording.
          </p>
        )}
        {imageUrl && failedImage !== imageUrl && (
          <img
            className="home-proof-original"
            src={imageUrl}
            alt={"Original image from " + source.title}
            onError={() => setFailedImage(imageUrl)}
          />
        )}
        <button
          type="button"
          className="text-button home-proof-open"
          onClick={() => onOpen(fact)}
        >
          Inspect source{" "}
          <ArrowUpRight
            size={15}
            strokeWidth={1.5}
            aria-hidden="true"
            focusable="false"
          />
        </button>
        <details className="home-proof-details">
          <summary>File details</summary>
          <dl>
            <dt>Original filename / title</dt>
            <dd>{source.title}</dd>
            <dt>Added to your record</dt>
            <dd>{dateLabel(source.available_at.slice(0, 10))}</dd>
          </dl>
          {source.original_available ? (
            <a href={originalDownloadUrl(source.id, view.scope)} download>
              Download original
            </a>
          ) : (
            <p>Original file unavailable. Saved excerpts are shown.</p>
          )}
        </details>
      </div>
    </section>
  );
}
