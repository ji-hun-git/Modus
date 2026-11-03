# Verification

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
