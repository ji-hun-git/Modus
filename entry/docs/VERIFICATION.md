# Verification

## Harder live report probes — 3 November 2026

Six new synthetic files contained 59 expected recorded entries: a two-column
panel, a three-date matrix, a three-page continuation with repeats and an unknown
date, a skewed scan, narrative notes and an empty reference-only template. Source
bytes and expected labels were hashed before the first call. The baseline used
`2bde82b`; the revised pass used the same unchanged files and labels. Both used
the actual Muse import path with `muse-spark-1.3`.

| Development observation | Before | After |
| --- | ---: | ---: |
| Exact page/name/value/unit entries | 58 / 59 | 59 / 59 |
| Absent rows, distinguishing a wrong unit from an absent row | 0 | 0 |
| Missing or incorrect units | 1 | 0 |
| Unsupported/renamed omission flags | 12 | 0 |
| Unit discrepancy presented as a row to add | 1 | 0 |
| Date differences from frozen labels | 0 | 4 |
| Failed files / unavailable inventories | 0 / 0 | 0 / 0 |

The matrix inventory invented date suffixes on test names, creating 12 false
flags despite complete extraction. Prompts now require each result cell to keep
the unchanged printed test label. The scan's final measurement lost its unit;
the inventory found it. A uniquely paired missing unit on the exact same source
passage now warns on the existing field instead of offering a duplicate row.
Both proposals remain intact. Exact matches take priority, ambiguous repeats
stay reviewable, and unsupported labels still cannot match a proposed field.
Two different non-empty units remain separate candidates even if their excerpts
are identical; a final regression locks that boundary. An offline replay
of the unchanged real scan responses separately confirmed this deterministic
behavior; it is not counted as a live rerun. Replaying all six revised live
inventories through the final boundary produced the same zero-flag results.

The four date differences are retained in the result. The narrative page said
“Collected” in its header, but did not explicitly date its narrative statements.
The original assistant-authored labels assigned that date to all four notes;
the revised model left it unknown. This label/linkage ambiguity requires
independent human review. Neither dates nor frozen labels were silently changed.
A separately authored prospective follow-up explicitly linked eight entries to
a visit date: all eight rows and dates were returned, without another code or
prompt change. That easier clarification case is **not** included in the table.

Strict tuple scoring counts the wrong-unit entry as one unmatched expected tuple
and one extra tuple; the supplementary presence count identifies that the row
itself was present. No whole row was naturally missed in either six-file pass.
Consequently, natural omission-detection recall remains **unmeasured**, and zero
final flags is not proof of complete extraction on other reports. These are
assistant-authored, development-tuned examples, not held-out or human-gold scores.

The session used **37 real provider requests**: 17 baseline, 17 revised and
three for the explicit-date follow-up. Recorded usage was 105,610 input and
41,708 output tokens; estimated Standard cost was **$0.30927150**, treating input
as uncached at [Meta's published rates](https://dev.meta.ai/docs/pricing-rate-limits).
This is a usage estimate, not an invoice or account-wide total. Raw responses,
request IDs, latency, labels, source hashes and both score definitions remain in
private development artifacts. The session was closed and its credential removed.

Verification: `python scripts/check_service.py` passed **1,392 backend tests,
2 skipped; 221 frontend tests; and the production build**. New regressions cover
matrix duplicates, invented labels, unique/ambiguous unit disagreements, match
ordering, reviewed correction, duplicate-save rejection and original retention.
The existing Starlette/httpx deprecation warning remains.

Browser verification reopened the cached matrix without a new model call,
reviewed and saved its 12 entries, opened its file satellite, found the 2017
Ferritin result through the real offline Ask path, and opened/downloaded its
original evidence. All 42 read-only service checks passed, including original
bytes for all seven sources, three retained matrix dates, earlier availability
exclusion, unchanged normal workspace data and all 17 served build assets.
The orbit interface is unchanged. Protected evaluations and held-out sets were
not accessed or modified.

## Live report reading and bounded Ask — 3 November 2026

A small development probe used the actual import and Ask paths with
`muse-spark-1.3`: a two-page mixed-test PDF, a scanned table and a reference-only
PDF containing an instruction-injection footer. The files and expected fields
were authored before the calls. They are assistant-authored and assistant-reviewed,
not independent human labels or held-out evidence.

Both extraction rounds retained all 16 measurement rows with exact label, value,
unit, recorded date, lab range, specimen and method. Both conflicting Ferritin
rows and the literal value `<0.5` survived. Initially, the scan also produced one
spurious record from a document disclaimer. The revised prompts excluded that
boilerplate while retaining the genuine recorded note. The reference-only PDF
produced no records; the deterministic document guard quarantined its instruction
footer. This does not demonstrate a hosted Guard model.

The separate row inventory now checks disagreement in both directions: missing
rows remain reviewable, and proposed entries absent from a complete readable-page
inventory receive a review warning. Limited or failed page reads cannot establish
absence. No proposed field is silently deleted. Neither live round omitted a
measurement, so this probe does **not** measure natural omission-detection recall.

Two live Ask attempts failed safely because Muse returned the string `"null"`
instead of JSON null for filters the application had already resolved. The final
interface exposes a zero-argument read for resolved questions, supplies the fixed
filters in code and still rejects any model-supplied filters before executing a
batch. A third attempt completed in two real requests and returned the recorded
Ferritin disagreement with clickable evidence for both original rows. No value
was chosen as correct. The general investigation tool protocol is unchanged.

Browser verification explicitly reviewed and saved 17 entries, asked about an
exact prior result, opened the live disagreement's two source excerpts and
downloaded an unchanged original scan. Read-only checks also confirmed original
PDF bytes, earlier availability excluding the new imports and the normal
workspace's unchanged history. The orbit interface was preserved.

This session made **20 provider requests**: 16 for the two extraction rounds,
two failed Ask requests and two for the completed Ask. Recorded usage was
57,726 input and 13,850 output tokens. Estimated cost was **$0.13102**, treating
all input as uncached at the published [Meta Standard rates](https://dev.meta.ai/docs/pricing-rate-limits);
this is a usage estimate, not an invoice or an account-wide total. Request IDs,
latencies, raw responses, failures and source/build identities were retained
privately. The paid session was closed and its live credential removed.

Final offline service check: **1,384 backend tests passed, 2 skipped; 221 frontend
tests passed; production build passed**. Fourteen read-only service checks passed,
and all 17 served build assets matched the checked files. The existing
Starlette/httpx deprecation warning remains. Extraction was verified before the
final Ask-only change; its extraction code stayed unchanged across that change.

The same three files were re-read after tuning, so these are development results,
not a general accuracy estimate. Real-history quality, independent human review,
live omission recall and final release qualification remain unproven. Protected
evaluation and held-out artifacts were not accessed or changed.

## Complete offline rehearsal — 3 November 2026

The rehearsal found and fixed two usability failures: natural questions such as
“When was my ferritin 30 ng/mL?” now use exact equality, and same-named reports
in Home's picker show their recorded dates. The printable summary also uses
readable correction labels instead of internal field names.

The offline service gate passed **1,371 backend tests, with 2 skipped; 221
frontend tests; and the production build**. These are software checks. The
existing Starlette/httpx deprecation warning remains.

A fresh isolated store received one authored PDF and one authored CSV through
the browser. The PDF used three explicitly artificial extraction responses;
CSV reading, Ask, corrections, replay and exports used the real offline paths.
The owner-reviewed missing row survived restart, was found by Ask and retained
its unchanged original excerpt and downloaded bytes. A saved pressure correction
kept 100 in the earlier view and 101 in the updated view. Replay excluded files
that had not yet arrived. The reviewed two-report export retained both corrected
values and original wording, with working internal evidence links. Escape from
the evidence drawer restored focus to the answer's source button.

A small local concurrency check sent 40 Ask requests with four workers. All 40
returned the expected records or clarification, with no HTTP failures or live
model calls. This is shared-host offline service evidence, not model accuracy
or production capacity.

This used the existing local dependencies, not a fresh machine or live model.
The normal workspace was separate from the rehearsal store. No paid model calls
or protected evaluation reads are part of this evidence. Live omission quality,
human-labelled accuracy and final contest release qualification remain open.

## Reviewed omissions — 3 November 2026

Offline service check: **1,347 backend tests passed, 2 skipped; 220 frontend
tests passed; production build passed**. The existing Starlette/httpx test-client
deprecation warning remains. The checked source stayed unchanged during the run.

New regressions cover explicit selection, edited values, missing dates, original
evidence retention, additions to saved sources, temporal snapshots in both APIs,
later corrections, exact retries, concurrent requests and transactional rollback.
Twenty-six pinned NVIDIA garak payloads exercise inert document handling; seven
browser-script payloads also pass through the actual React review renderer.
[Open-source scope and attribution](OPEN_SOURCE.md) distinguish corpus reuse from
a live scanner or model test.

Browser verification used two authored PDFs with explicitly artificial model
responses in an isolated offline store. It exercised an initial save, an edited
missing-row addition, an empty extraction, reload/reopen and remaining-row save.
The changed value was visible in the file orbit beside its unchanged original
excerpt. Downloaded original bytes matched the uploaded PDF. No model call,
protected evaluation access or medical-quality claim is part of this evidence.

Run the offline service gate on the revision being reviewed:

```sh
python scripts/check_service.py
```

It runs selected backend regressions, frontend tests and the production build,
with credentials removed and protected evaluation paths excluded. Source and
build hashes are recorded in ignored local output. The preview launcher refuses
a stale check. Windows and Ubuntu CI run the same command; consult the workflow
run for the exact commit rather than transferring an earlier result to new code.

## Software contracts

- Review is required before a save; idempotent recovery preserves exact submitted rows.
- Corrections retain originals and earlier availability views.
- Retrieved values, units, dates and sources remain scoped to the captured history.
- Conflicts, partial dates and qualified values are not silently resolved.
- Typed arithmetic and claim verification prevent model-generated numerical findings.
- Original downloads, comparisons and reviewed exports obey source/temporal bounds.
- Browser checks cover real inputs, keyboard focus, original evidence and narrow layouts.

Software test counts are not medical accuracy or model-quality scores. Injected
provider responses test contracts and failures without proving live behavior.
Live model qualification and independent human-labelled comparisons require
separate evidence and authorization. Historical results remain version-specific
in [SCOREBOARD.md](../../SCOREBOARD.md).

The local prototype is not production privacy/security qualification, clinical
validation or a final contest release. Private working notes and credentials
must remain outside the public repository.
