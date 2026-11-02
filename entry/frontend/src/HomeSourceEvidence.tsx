import { useState } from "react";
import RecordDateEvidence from "./RecordDateEvidence";
import { ArrowUpRight, FileText } from "lucide-react";
import type { HistoryFact, HistoryView } from "./historyTypes";
import { reportSummaries, sourceRegion } from "./homeReportData";
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
  const region = sourceRegion(fact);
  const imageReady = imageUrl && failedImage !== imageUrl;
  const canHighlight = imageReady && region && (fact.page == null || fact.page === 1);
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
          <RecordDateEvidence evidence={fact.date_evidence} currentDate={fact.occurred_on}
            hidden={fact.source_quote_withheld || fact.value_withheld} />
        </div>
        {!!fact.reviewed_fields?.length && (
          <p className="home-proof-edited">
            {fact.previous_revision_id ? "Corrected after saving" : "Edited during review"}:{" "}
            {fact.reviewed_fields.map(reviewedFieldLabel).join(", ")}. The
            excerpt keeps the original wording.
          </p>
        )}
        {imageReady && (
          <figure className="home-proof-page">
            <img
            className="home-proof-original"
            src={imageUrl}
            alt={"Original image from " + source.title}
            onError={() => setFailedImage(imageUrl)}
            />
            {canHighlight && <svg viewBox="0 0 1000 1000" preserveAspectRatio="none" role="img" aria-label="Recorded source region">
              <rect x={region[0] * 1000} y={region[1] * 1000} width={(region[2] - region[0]) * 1000}
                height={(region[3] - region[1]) * 1000} vectorEffect="non-scaling-stroke" />
            </svg>}
          </figure>
        )}
        {(sourceKind(source.type, source.title) === 'image' || region) && <p className="home-proof-region-status">
          {canHighlight ? "Outline marks the saved source region."
            : region ? "Source region cannot be previewed for this file. Inspect the original page."
            : "Source region not located."}
        </p>}
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
        {source.original_available ? <a className="text-button home-proof-open"
          href={originalDownloadUrl(source.id, view.scope)} download>Download original</a>
          : <p>Original file unavailable in this view.</p>}
        <details className="home-proof-details">
          <summary>File details</summary>
          <dl>
            <dt>Original filename / title</dt>
            <dd>{source.title}</dd>
            <dt>Added to your record</dt>
            <dd>{dateLabel(source.available_at.slice(0, 10))}</dd>
          </dl>
        </details>
      </div>
    </section>
  );
}
