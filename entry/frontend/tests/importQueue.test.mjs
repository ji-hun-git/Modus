import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(
  new URL("../src/importQueue.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const queue = await import(
  "data:text/javascript;base64," + Buffer.from(compiled).toString("base64")
);
let sequence = 0;
const id = () => `file-${++sequence}`;
const file = (name = "record.csv", size = 100) => ({ name, size });
const selected = () => queue.appendFiles([], [file()], id).items[0];
const draft = (extra = {}) => ({
  id: "draft-1",
  source: { title: "record.csv" },
  extraction_mode: "local",
  warnings: [],
  observations: [
    {
      id: "row-1",
      source_id: "draft-1",
      metric: "egfr",
      value: 82,
      unit: "mL/min/1.73m2",
      date: "2021-04-08",
      source_span: "recorded row",
    },
    {
      id: "row-2",
      source_id: "draft-1",
      metric: "ldl",
      value: 120,
      unit: "mg/dL",
      date: "2021-04-08",
      source_span: "second row",
    },
  ],
  ...extra,
});
const review = () => queue.acceptDraft(selected(), draft());

test("contest readers offer Meta as the only model and reject stale OCR selection", () => {
  const pdf = file("record.pdf");
  const readers = queue.readingOptions(pdf, true);
  assert.deepEqual(readers.map((reader) => reader.value), ["local", "meta"]);
  assert.deepEqual(queue.previewReaderFields(pdf, "local", false), { use_meta: "false" });
  assert.deepEqual(queue.previewReaderFields(pdf, "meta", true), { use_meta: "true" });
  assert.throws(() => queue.previewReaderFields(pdf, "local-teleocr", true), /available reading method/);
  assert.throws(() => queue.previewReaderFields(pdf, "meta", false), /available reading method/);
});

test("images require explicit Meta selection and cannot silently fall back to a local model", () => {
  const image = file("record.PNG");
  assert.equal(queue.appendFiles([], [image], id).items[0].extraction, "local");
  assert.equal(queue.readingOptions(image, false).some((reader) => reader.available), false);
  assert.throws(() => queue.previewReaderFields(image, "local", true), /Images require Meta/);
  assert.deepEqual(queue.previewReaderFields(image, "meta", true), { use_meta: "true" });
  assert.equal(queue.appendFiles([], [file("record.txt")], id).items[0].extraction, "local");
  assert.deepEqual(queue.previewReaderFields(file("record.txt"), "local", false), { use_meta: "false" });
});
const receipt = (extra = {}) => ({
  draft_id: "draft-1",
  source_id: "draft-1",
  inserted: 1,
  duplicate: false,
  available_at: "2026-10-28T00:00:00Z",
  observation_ids: ["row-1"],
  bundle_id: "test",
  ...extra,
});

test("appending preserves earlier selections and caps the whole queue at ten", () => {
  const first = queue.appendFiles(
    [],
    [file("first.csv"), file("second.txt")],
    id,
  ).items;
  const result = queue.appendFiles(
    first,
    Array.from({ length: 10 }, (_, i) => file(`${i}.pdf`)),
    id,
  );
  assert.equal(result.items.length, 10);
  assert.equal(result.omitted, 2);
  assert.equal(result.items[0], first[0]);
  assert.equal(result.items[1], first[1]);
  assert.equal(new Set(result.items.map((item) => item.id)).size, 10);
});

test("size boundary is eight MiB and invalid files remain individually visible", () => {
  assert.equal(queue.fileError(file("valid.pdf", queue.MAX_FILE_BYTES)), "");
  assert.match(
    queue.fileError(file("large.pdf", queue.MAX_FILE_BYTES + 1)),
    /larger than 8 MB/,
  );
  const result = queue.appendFiles(
    [],
    [file("dna.vcf"), file("empty.csv", 0), file("good.csv")],
    id,
  );
  assert.deepEqual(
    result.items.map((item) => item.status),
    ["error", "error", "selected"],
  );
  assert.equal(queue.summary(result.items).pending, 3);
});

test("selecting an image does not select or call a model", () => {
  const item = queue.appendFiles([], [file("scan.png")], id).items[0];
  assert.equal(item.extraction, "local");
  assert.equal(item.status, "selected");
  assert.equal(item.draft, null);
  assert.equal(item.receipt, null);
});

test("reviewed changes and exclusions form an independent commit snapshot", () => {
  const item = review();
  item.rows[0].valueText = "79";
  item.rows[1].keep = false;
  const saving = queue.beginCommit(item);
  item.rows[0].valueText = "999";
  assert.equal(saving.status, "saving");
  assert.deepEqual(saving.attempt, [
    {
      id: "row-1",
      metric: "egfr",
      value: 79,
      unit: "mL/min/1.73m2",
      date: "2021-04-08",
    },
  ]);
});

test("no included rows, blank values and nonfinite numbers cannot save", () => {
  for (const bad of ["", " ", "NaN", "Infinity", "-1"]) {
    const item = review();
    item.rows[0].valueText = bad;
    assert.throws(() => queue.beginCommit(item));
  }
  const item = review();
  item.rows.forEach((row) => {
    row.keep = false;
  });
  assert.throws(() => queue.beginCommit(item));
});

test("uncertain save locks navigation and preserves exact retry payload even after another failure", () => {
  const saving = queue.beginCommit(review());
  const uncertain = queue.failCommit(saving, false, false, "unknown result");
  assert.equal(uncertain.status, "uncertain");
  assert.equal(queue.navigationLocked([uncertain, selected()]), true);
  const items = [uncertain];
  assert.equal(queue.appendFiles(items, [file()], id).items, items);
  uncertain.rows[0].valueText = "999";
  const retry = queue.beginCommit(uncertain);
  assert.deepEqual(retry.attempt, saving.attempt);
  const stillUncertain = queue.failCommit(retry, true, true, "later 422");
  assert.equal(stillUncertain.status, "uncertain");
  assert.deepEqual(stillUncertain.attempt, saving.attempt);
});

test("first definitive validation rejection unlocks correction without a saved receipt", () => {
  const result = queue.failCommit(
    queue.beginCommit(review()),
    true,
    false,
    "invalid field",
  );
  assert.equal(result.status, "review");
  assert.equal(result.attempt, null);
  assert.equal(result.receipt, null);
  assert.equal(queue.navigationLocked([result]), false);
});

test("reading and saving lock navigation while selected/review/error do not", () => {
  for (const status of ["reading", "saving", "uncertain"])
    assert.equal(queue.navigationLocked([{ ...selected(), status }]), true);
  for (const status of ["selected", "review", "error"])
    assert.equal(queue.navigationLocked([{ ...selected(), status }]), false);
});

test("zero supported measurements cannot become a successful review", () => {
  const item = queue.acceptDraft(selected(), draft({ observations: [] }));
  assert.equal(item.status, "error");
  assert.equal(item.draft, null);
  assert.throws(() => queue.beginCommit(item));
});

test("wider record fields remain visible in a draft without a saveable measurement", () => {
  const reviewOnly = draft({
    observations: [],
    extraction_review: {
      document_type: "vaccination_card",
      verification_status: "completed",
      facts: [
        {
          id: "field-1",
          label: "Vaccine",
          value: "Recorded vaccine",
          commit_supported: false,
        },
      ],
    },
  });
  const item = queue.acceptDraft(selected(), reviewOnly);
  assert.equal(item.status, "review");
  assert.equal(item.draft, reviewOnly);
  assert.deepEqual(item.rows, []);
  assert.equal(queue.summary([item]).confirmed, 0);
  assert.throws(
    () => queue.beginCommit(item),
    /Include at least one measurement/,
  );
});

test("saving supported measurements preserves wider fields in the local draft only", () => {
  const mixed = draft({
    extraction_review: {
      document_type: "checkup",
      verification_status: "unavailable",
      facts: [
        {
          id: "field-1",
          label: "Height",
          value: "170",
          commit_supported: false,
        },
      ],
    },
  });
  const pending = queue.beginCommit(queue.acceptDraft(selected(), mixed));
  assert.ok(
    pending.attempt.every((row) => !Object.hasOwn(row, "extraction_review")),
  );
  const saved = queue.finishCommit(pending, receipt());
  assert.equal(saved.draft.extraction_review, mixed.extraction_review);
  assert.equal(saved.draft.extraction_review.facts[0].commit_supported, false);
  assert.equal(queue.summary([saved]).measurements, 1);
});

test("generic review submits edited recorded fields without source or model authority", () => {
  const generic = draft({
    observations: [],
    facts: [
      {
        id: "field-1",
        kind: "vaccination",
        label: "Vaccine",
        value: "As printed",
        unit: null,
        occurred_on: "2010",
        facility: "Example clinic",
        page: 1,
        source_quote: "Original line",
        bbox: null,
        model_confidence: 0.99,
        available_at: "1900-01-01",
      },
      {
        id: "field-2",
        kind: "recorded_text",
        label: "Note",
        value: "Second line",
        unit: null,
        occurred_on: null,
        facility: null,
        page: 1,
        source_quote: "Second line",
      },
    ],
  });
  const item = queue.acceptDraft(selected(), generic);
  item.factRows[0].value = "Edited as printed";
  item.factRows[1].keep = false;
  const pending = queue.beginFactCommit(item);
  assert.deepEqual(pending.factAttempt, [
    {
      id: "field-1",
      kind: "vaccination",
      label: "Vaccine",
      value: "Edited as printed",
      unit: null,
      occurred_on: "2010",
      facility: "Example clinic",
    },
  ]);
  assert.throws(() => queue.beginCommit(item), /Choose a review/);
  item.factRows[0].value = "Later mutation";
  assert.equal(pending.factAttempt[0].value, "Edited as printed");
});

test("uncertain generic saves retry exact fields and remain locked through later rejection", () => {
  const generic = draft({
    observations: [],
    facts: [
      {
        id: "field-1",
        kind: "recorded_text",
        label: "Note",
        value: "As printed",
        unit: null,
        occurred_on: null,
        facility: null,
        page: 1,
        source_quote: "As printed",
      },
    ],
  });
  const item = queue.acceptDraft(selected(), generic);
  const pending = queue.beginFactCommit(item);
  const uncertain = queue.failCommit(pending, false, false, "Connection lost");
  uncertain.factRows[0].value = "Do not resubmit this mutation";
  const retried = queue.beginFactCommit(uncertain);
  assert.deepEqual(retried.factAttempt, pending.factAttempt);
  const rejected = queue.failCommit(
    retried,
    true,
    true,
    "Later validation failure",
  );
  assert.equal(rejected.status, "uncertain");
  assert.equal(queue.navigationLocked([rejected]), true);
  const saved = queue.finishCommit(
    retried,
    receipt({ fact_ids: ["fact-1"], observation_ids: [] }),
  );
  assert.equal(saved.factAttempt, null);
  assert.equal(saved.receipt.fact_ids[0], "fact-1");
});

test("generic field review rejects blank required values and permits unknown dates and units", () => {
  const generic = draft({
    observations: [],
    facts: [
      {
        id: "field-1",
        kind: "encounter",
        label: "Visit",
        value: "As recorded",
        unit: null,
        occurred_on: null,
        facility: null,
        page: 1,
        source_quote: "As recorded",
      },
    ],
  });
  const item = queue.acceptDraft(selected(), generic);
  assert.equal(queue.beginFactCommit(item).factAttempt[0].occurred_on, null);
  item.factRows[0].value = " ";
  assert.throws(() => queue.beginFactCommit(item), /name and value/);
  item.factRows[0].value = "Restored";
  item.factRows[0].keep = false;
  assert.throws(() => queue.beginFactCommit(item), /Include at least one/);
});

test("duplicate previews cannot be committed and do not inflate saved totals", () => {
  const duplicate = queue.acceptDraft(
    selected(),
    draft({ already_committed: true }),
  );
  assert.equal(duplicate.status, "duplicate");
  assert.throws(() => queue.beginCommit(duplicate));
  assert.deepEqual(queue.summary([duplicate]), {
    confirmed: 1,
    saved: 0,
    measurements: 0,
    duplicates: 1,
    skipped: 0,
    errors: 0,
    pending: 0,
  });
});

test("confirmed receipts count exact inserted rows and clear uncertainty", () => {
  const saved = queue.finishCommit(
    queue.failCommit(queue.beginCommit(review()), false, false, "unknown"),
    receipt(),
  );
  const duplicate = queue.finishCommit(
    queue.beginCommit(review()),
    receipt({ duplicate: true, inserted: 0 }),
  );
  assert.equal(saved.status, "saved");
  assert.equal(duplicate.status, "duplicate");
  assert.equal(saved.attempt, null);
  assert.equal(queue.navigationLocked([saved]), false);
  assert.deepEqual(
    queue.summary([
      saved,
      duplicate,
      { ...selected(), status: "skipped" },
      selected(),
    ]),
    {
      confirmed: 1,
      saved: 1,
      measurements: 1,
      duplicates: 1,
      skipped: 1,
      errors: 0,
      pending: 1,
    },
  );
});

test("switching to another queued file does not replace the first reviewed rows", () => {
  const first = review();
  first.rows[0].valueText = "78";
  first.rows[1].keep = false;
  const items = queue.appendFiles([first], [file("later.txt")], id).items;
  const second = queue.acceptDraft(items[1], draft({ id: "draft-2" }));
  const updated = items.map((item) => (item.id === second.id ? second : item));
  assert.equal(updated[0].rows[0].valueText, "78");
  assert.equal(updated[0].rows[1].keep, false);
  assert.equal(updated[1].rows[0].valueText, "82");
});
