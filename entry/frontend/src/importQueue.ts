import type { Commit, Draft, Reviewed, ReviewRow } from "./types";
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
  receipt: Commit | null;
  error: string;
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
    !draft.extraction_review?.facts.length
  )
    return {
      ...item,
      status: "error",
      error: "No supported measurements were found. This file was not saved.",
    };
  return {
    ...item,
    draft,
    rows: draft.observations.map((row) => ({
      ...row,
      keep: true,
      valueText: String(row.value),
    })),
    selected: 0,
    attempt: null,
    factRows: draft.facts?.map((fact) => ({ ...fact, keep: true })),
    factAttempt: null,
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
    item.draft.already_committed ||
    !["review", "uncertain"].includes(item.status)
  )
    throw new Error("Choose a review before saving.");
  const kept = (item.factRows || []).filter((fact) => fact.keep);
  if (
    !item.factAttempt &&
    (!kept.length ||
      kept.some((fact) => !fact.label.trim() || !fact.value.trim()))
  )
    throw new Error(
      "Include at least one recorded fact with a name and value.",
    );
  return {
    ...item,
    status: "saving",
    error: "",
    factAttempt:
      item.factAttempt ||
      kept.map(({ id, kind, label, value, unit, occurred_on, facility }) => ({
        id,
        kind,
        label,
        value,
        unit,
        occurred_on,
        facility,
      })),
  };
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
    error,
  };
}

export function finishCommit(item: QueueItem, receipt: Commit): QueueItem {
  return {
    ...item,
    status: receipt.duplicate ? "duplicate" : "saved",
    receipt,
    attempt: null,
    factAttempt: null,
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
    saved: items.filter((item) => item.receipt && !item.receipt.duplicate)
      .length,
    measurements: items.reduce(
      (count, item) => count + (item.receipt?.inserted || 0),
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
