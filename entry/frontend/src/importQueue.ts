import type { Commit, Draft, Reviewed, ReviewRow, ReportCoverage } from "./types";
import type { FactReviewRow, ReviewedFact } from "./historyTypes";

export const MAX_FILES = 10;
export const MAX_FILE_BYTES = 8 * 1024 * 1024;
export type Extraction = "local" | "meta";
export type QueueStatus =
  | "selected"
  | "reading"
  | "review"
  | "saving"
  | "saved"
  | "skipped"
  | "error"
  | "uncertain"
  | "duplicate";
export type QueueItem = {
  id: string;
  file: File;
  status: QueueStatus;
  extraction: Extraction;
  draft: Draft | null;
  rows: ReviewRow[];
  selected: number;
  attempt: Reviewed[] | null;
  factRows?: FactReviewRow[];
  factAttempt?: ReviewedFact[] | null;
  omissionAttempt?: ReviewedFact[] | null;
  receipt: Commit | null;
  totalInserted?: number;
  error: string;
  reportCoverage?: ReportCoverage;
};

export function extension(file: Pick<File, "name">) {
  return file.name.split(".").pop()?.toLowerCase() || "";
}

export function readingOptions(file: Pick<File, "name">, metaAvailable: boolean) {
  const suffix = extension(file);
  return [
    { value: "local" as const, label: "Local text · no model",
      available: ["csv", "txt", "pdf"].includes(suffix) },
    { value: "meta" as const, label: `Meta${metaAvailable ? "" : " · not configured"}`,
      available: metaAvailable && ["pdf", "png", "jpg", "jpeg"].includes(suffix) },
  ];
}

export function previewReaderFields(file: Pick<File, "name">, reader: string, metaAvailable: boolean) {
  if (!readingOptions(file, metaAvailable).some((option) => option.value === reader && option.available))
    throw new Error("Choose an available reading method. Images require Meta.");
  return { use_meta: String(reader === "meta") };
}

export function fileError(file: Pick<File, "name" | "size">) {
  if (!["csv", "txt", "pdf", "png", "jpg", "jpeg"].includes(extension(file)))
    return "This file type is not supported. Choose CSV, text, PDF, PNG or JPEG.";
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_FILE_BYTES)
    return "This file is larger than 8 MB. Choose a smaller file.";
  return "";
}

export function navigationLocked(items: QueueItem[]) {
  return items.some((item) =>
    ["reading", "saving", "uncertain"].includes(item.status),
  );
}

export function appendFiles(
  items: QueueItem[],
  files: File[],
  makeId = () => crypto.randomUUID(),
) {
  if (navigationLocked(items)) return { items, omitted: files.length };
  const accepted = files.slice(0, Math.max(0, MAX_FILES - items.length));
  return {
    items: [
      ...items,
      ...accepted.map((file): QueueItem => {
        const error = fileError(file);
        return {
          id: makeId(),
          file,
          status: error ? "error" : "selected",
          extraction: "local",
          draft: null,
          rows: [],
          selected: 0,
          attempt: null,
          receipt: null,
          error,
        };
      }),
    ],
    omitted: files.length - accepted.length,
  };
}

export function acceptDraft(item: QueueItem, draft: Draft): QueueItem {
  if (
    !draft.observations.length &&
    !draft.facts?.length &&
    !draft.extraction_review?.facts.length &&
    !draft.extraction_review?.completeness_check?.omissions.length &&
    !draft.extraction_review?.coverage
  )
    return {
      ...item,
      status: "error",
      error: "No recorded fields were found. This file was not saved.",
    };
  return {
    ...item,
    draft,
    reportCoverage: undefined,
    rows: draft.observations.map((row) => ({
      ...row,
      keep: true,
      valueText: String(row.value),
    })),
    selected: 0,
    attempt: null,
    factRows: draft.facts?.map((fact) => ({ ...fact, keep: true })),
    factAttempt: null,
    omissionAttempt: null,
    error: "",
    status: draft.already_committed ? "duplicate" : "review",
  };
}

export function beginCommit(item: QueueItem): QueueItem {
  if (
    !item.draft ||
    !!item.draft.facts ||
    item.draft.already_committed ||
    !["review", "uncertain"].includes(item.status)
  )
    throw new Error("Choose a review before saving.");
  const kept = item.rows.filter((row) => row.keep);
  if (
    !item.attempt &&
    (!kept.length ||
      kept.some(
        (row) =>
          !row.valueText.trim() ||
          !Number.isFinite(Number(row.valueText)) ||
          Number(row.valueText) < 0 ||
          !row.unit.trim() ||
          !row.date,
      ))
  )
    throw new Error(
      "Include at least one measurement with a value, printed unit and date.",
    );
  return {
    ...item,
    status: "saving",
    error: "",
    attempt:
      item.attempt ||
      kept.map((row) => ({
        id: row.id,
        metric: row.metric,
        value: Number(row.valueText),
        unit: row.unit,
        date: row.date,
      })),
  };
}

export function beginFactCommit(item: QueueItem): QueueItem {
  if (
    !item.draft?.facts ||
    !["review", "uncertain"].includes(item.status)
  )
    throw new Error("Choose a review before saving.");
  const kept = (item.factRows || []).filter((fact) => fact.keep);
  const omissionIds = new Set(item.draft.extraction_review?.completeness_check?.omissions.map(row => row.id));
  if (item.draft.already_committed && kept.some(row => !omissionIds.has(row.id)))
    throw new Error("Saved fields must be edited through Corrections.");
  if (
    !item.factAttempt &&
    (!kept.length ||
      kept.some((fact) => !fact.label.trim() || !fact.value.trim()))
  )
    throw new Error(
      "Include at least one recorded fact with a name and value.",
    );
  const reviewed = kept.map(({ id, kind, label, value, unit, occurred_on, facility, reference_range, specimen, test_method }) => ({
    id, kind, label, value, unit, occurred_on, facility,
    reference_range: reference_range ?? null, specimen: specimen ?? null, test_method: test_method ?? null,
  }));
  return {
    ...item,
    status: "saving",
    error: "",
    factAttempt:
      item.factAttempt ||
      reviewed.filter(row => !omissionIds.has(row.id)),
    omissionAttempt: item.omissionAttempt || reviewed.filter(row => omissionIds.has(row.id)),
  };
}

export function omissionProposal(draft: Draft, id: string): FactReviewRow | undefined {
  const candidate = draft.extraction_review?.completeness_check?.omissions.find(row => row.id === id);
  return candidate ? { id, label: candidate.label, value: candidate.value, unit: candidate.unit,
    kind: 'recorded_text', occurred_on: null, facility: null, reference_range: null, specimen: null,
    test_method: null, source_quote: candidate.source_quote, page: candidate.page, bbox: candidate.bbox, keep: true } : undefined;
}

export function addOmissionToReview(item: QueueItem, id: string): QueueItem {
  if (!item.draft || navigationLocked([item]) || item.draft.omission_reviews?.some(row => row.candidate_id === id)) return item;
  const candidate = omissionProposal(item.draft, id);
  if (!candidate) return item;
  const rows = item.draft.already_committed && ['saved', 'duplicate', 'skipped'].includes(item.status) ? [] : item.factRows || [];
  return { ...item, status: 'review', error: '', factRows: rows.some(row => row.id === id)
    ? rows.map(row => row.id === id ? { ...row, keep: true } : row) : [...rows, candidate] };
}

export function failCommit(
  item: QueueItem,
  definitive: boolean,
  wasUncertain: boolean,
  error: string,
): QueueItem {
  return {
    ...item,
    status: definitive && !wasUncertain ? "review" : "uncertain",
    attempt: definitive && !wasUncertain ? null : item.attempt,
    factAttempt: definitive && !wasUncertain ? null : item.factAttempt,
    omissionAttempt: definitive && !wasUncertain ? null : item.omissionAttempt,
    error,
  };
}

export function finishCommit(item: QueueItem, receipt: Commit): QueueItem {
  return {
    ...item,
    status: receipt.duplicate ? "duplicate" : "saved",
    receipt,
    totalInserted: (item.totalInserted || 0) + receipt.inserted,
    attempt: null,
    factAttempt: null,
    omissionAttempt: null,
    draft: item.draft ? { ...item.draft, already_committed: true,
      saved_available_at: item.draft.saved_available_at || receipt.available_at,
      omission_reviews: [...(item.draft.omission_reviews || []), ...(receipt.omission_ids || [])
        .filter(id => !item.draft?.omission_reviews?.some(row => row.candidate_id === id))
        .map(candidate_id => ({ candidate_id, available_at: receipt.available_at }))],
    } : null,
    error: "",
  };
}

export function summary(items: QueueItem[]) {
  return {
    confirmed: new Set(
      items.flatMap((item) =>
        item.receipt
          ? [item.receipt.source_id]
          : item.status === "duplicate" && item.draft
            ? [item.draft.source.id || item.draft.id]
            : [],
      ),
    ).size,
    saved: items.filter((item) => (item.totalInserted ?? item.receipt?.inserted ?? 0) > 0)
      .length,
    measurements: items.reduce(
      (count, item) => count + (item.totalInserted ?? item.receipt?.inserted ?? 0),
      0,
    ),
    duplicates: items.filter(
      (item) => item.status === "duplicate" || item.receipt?.duplicate,
    ).length,
    skipped: items.filter((item) => item.status === "skipped").length,
    errors: items.filter((item) => item.status === "error").length,
    pending: items.filter(
      (item) => !["saved", "duplicate", "skipped"].includes(item.status),
    ).length,
  };
}

export const statusLabel: Record<QueueStatus, string> = {
  selected: "Selected",
  reading: "Reading…",
  review: "Ready to review",
  saving: "Saving…",
  saved: "Saved",
  skipped: "Skipped",
  error: "Needs attention",
  uncertain: "Save unconfirmed",
  duplicate: "Already saved",
};
