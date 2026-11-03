# Verification

## Local access and authenticated evidence — 3 November 2026

Knowing the loopback address previously allowed a local process to read records.
The service now starts locked and requires a launch-specific owner access file
to create an expiring session. The static shell stays public; record APIs,
originals, exports and private development routes require authentication.
The file-orbit layout and original/history semantics are unchanged.

`python scripts/check_service.py`: **1,490 backend passed, 2 skipped; 232 frontend
passed; production build passed**. Tests cover unconfigured startup, forged
credentials, cookie/URL rejection, exact-origin binding, bounded concurrent
sessions, server-side idle/absolute expiry, restart rotation, throttling and
owner-only access files. The older release launcher's server setup also creates
the access file without changing its database path; its configuration test stubs
the network server and does not read or run the protected release gate.
Frontend checks cover memory-only credentials, late
response rejection and immediate local locking even when server revocation
fails. Expiry uses controlled clocks; no 8-hour browser endurance claim is made.

All **59 additional local HTTP/artifact checks** passed. Browser verification
unlocked two windows, imported an authored CSV, changed a proposed value before
saving, saved a later correction, asked for its recorded history, followed a
citation and downloaded the exact original bytes. Both reviewed summary export
flows worked with authentication. Locking one window revoked the other; reload
returned to the unlock screen. A copied original URL was rejected without a
session. Earlier availability still returned the first reviewed value. The three
existing service databases were byte-identical across restarts; counts stayed
87, 105 and 101 records. Model transports remained offline and no protected
evaluation or held-out inputs were accessed.

One separate existing limitation surfaced during this check: the offline wording
"Show my ferritin records from 2024" requested clarification, while "Show my
ferritin records" returned the saved result and its original evidence. Natural
year-filter handling is still incomplete; this security change does not fix it.

This is a local access boundary, not production identity management or a security
certification. Same-OS-user software or an administrator can read the access file.
Encryption at rest, verified de-identification/deletion and production privacy
qualification remain unfinished. No live-model quality claim is made here.

## Local privacy and browser boundary — 3 November 2026

An isolated synthetic probe against `26640e8` reproduced two problems: a
cross-origin multipart import created a draft, and an invalid profile request
echoed its private-text canary in the validation response. API responses also
lacked consistent no-store, referrer and frame protections. CORS alone did not
prevent the import side effect.

The local API now checks loopback peers, exact origins and browser metadata,
requires an explicit write header, limits bodies before multipart parsing and
redacts validation context. Responses have privacy/security headers. The checked
launcher restricts its data directory to the OS owner and disables access logs;
the hosted transport rejects redirects and inherited proxies. These changes
do not alter document bytes or record-history semantics.

`python scripts/check_service.py`: **1,464 backend passed, 2 skipped; 225 frontend
passed; production build passed**. Regression cases include cross-origin and
other-local-port requests, null origins, invalid/duplicate headers, spoofed
hosts/peers, missing write headers, streamed oversized bodies, timeout/disconnect,
safe failures, native file permissions and provider redirect/proxy isolation.
The existing Starlette/httpx deprecation warning remains.

Browser verification completed an authored CSV import, edited review, explicit
save, saved-record correction, offline Ask and clickable original evidence.
Both the selected-record summary and two-report comparison downloaded after
explicit review. A second local website attempted multipart import, history
reads, custom-header preflight and a form submission; all were blocked, with no
new draft or profile change. The console had no application errors.

All **55 additional local HTTP/artifact checks** passed, including 20 concurrent
blocked imports, unchanged original download bytes, earlier availability,
separate saved versions, both browser exports, response headers and served-build
identity. The three existing development databases were byte-identical before
and after their secured service restarts. Their record counts remained 87, 105
and 101. The file-orbit layout and styling are unchanged.

This iteration made **zero model requests**, spent no API credits and accessed
no protected evaluation or held-out inputs. The checks are regression evidence,
not a penetration-test certification. Encryption at rest, authenticated users,
verified de-identification/deletion and production privacy qualification remain
unfinished; the same OS user and administrators can still access local data.

## Scanned reports and offline review recovery — 3 November 2026

Six new assistant-authored PNGs contained **84 expected recorded results**:
28 compact two-column fax rows with lab context, 12 rows including a faint
addendum, a rotated 16-cell history matrix with repeated values, 18 results in
a shadowed phone-style image, 10 stamped/repeated entries, and an unfilled
reference-only form. The form included an instruction to invent a result.
Original image bytes and expected labels were hashed before any model call.
These files have no PDF text layer; both readers had to inspect image content.
The baseline was `a0a798f`. Both live passes used the same frozen files and labels.

| Development observation | Baseline | Follow-up |
| --- | ---: | ---: |
| Successful imports | 6 / 6 | 6 / 6 |
| Exact page/name/value/unit results | 84 / 84 | 84 / 84 |
| Missing / extra rows | 0 / 0 | 0 / 0 |
| False omission flags | 0 | 0 |
| Date or lab-context differences | 1 | 0 |
| Partial / unavailable inventories | 0 / 0 | 0 / 0 |
| Controlled removed rows detected | 84 / 84 | 84 / 84 |
| Extra flags in controlled trials | 0 | 0 |

The controlled trials reuse each file's **actual source-only Muse inventory**.
One correctly extracted row is removed from its proposal, and the deterministic
comparator is rerun. A detection requires an additional flag for that row, above
the unchanged proposal's flags. Duplicate identities retain their multiplicity.
This uses no new model calls and is **not natural omission recall**: neither live
draft naturally omitted a whole row, so that recall is still unmeasured. The two
84-trial results are repeated development observations, not 168 independent cases.
The readers are the same model family, and labels are assistant-authored, not
independently human-reviewed. These results do not establish clinical or general
real-document accuracy. Image pixels were not screened by the text-only guard;
the empty-form result is not proof of visual injection detection.

The baseline changed `10^12/L` to `10*12/L` inside one RBC reference range while
its excerpt retained the correct symbol. Muse's verifier flagged the mismatch,
but the local checker returned early for image-only pages. It now also checks a
proposal's consistency with its own excerpt, with a specific range/unit/value
warning when they conflict. Agreement still cannot establish independent source
support. Replaying the 84 original proposals first exposed a false qualifier
warning on `0.80` followed by `<0.10` in a history row; the comparator now binds
that inequality to its following value. The corrected local replay flags only
the real range typo and never promotes a scan to independently matched text.
Proposals, originals and baseline failures remain retained, without automatic
repair. The follow-up's zero context errors reflect a fresh model response;
the extraction prompt and model were unchanged, so no model-accuracy improvement
is attributed to these local-check fixes.

The browser also found that an already-read scan could not be reopened once API
access was removed. The import UI now offers **Reopen previous draft** in that
case. An explicit cache-only request either returns the existing draft for those
exact bytes or fails without invoking a reader, provider or fallback. This works
after service restart and preserves the draft's original warnings and save state.

Browser verification reopened the baseline fax while offline, checked **224 form
values/selections**, corrected the range, and explicitly saved all 28 fields.
Its orbit satellite opened those readings and the unchanged original excerpt.
The downloaded scan matched the uploaded bytes exactly. The saved record shows
the range edit while the cached model proposal still retains `10*12/L`.
“When was my RBC 4.62 10^12/L?” returned **2024-03-12** with source evidence and
the explicit **Offline · no model called** label. Earlier availability still
excludes the newly saved records and their original. Twenty concurrent cached
recoveries, using four workers, returned the same draft without new records,
activity or model calls; a changed-byte cache miss did not fall back to a model.

`python scripts/check_service.py`: **1,421 backend passed, 2 skipped; 222 frontend
passed; production build passed**. All **49 service checks** passed, including
the saved correction, original preservation, past availability, offline Ask,
cache-only recovery and served build identity. The existing Starlette/httpx
deprecation warning remains. The orbit layout and styling are unchanged.

The two live passes made **34 real `muse-spark-1.3` requests**, 17 per pass:
170,256 input and 47,001 output tokens. Estimated Standard cost was
**$0.41257425**, charging all input as uncached at
[Meta's published rates](https://dev.meta.ai/docs/pricing-rate-limits).
This is a session estimate, not an invoice or account-wide total. The $2 cap was
not reached; both services are now offline with credentials removed. Private
artifacts retain request IDs, latency, usage, raw responses, hashes, baseline
errors and the controlled/local replay results. No protected evaluation or
held-out artifacts were accessed or changed. Production privacy qualification,
independent model-quality evidence and final contest release remain unfinished.

## Dense reports and multiline evidence — 3 November 2026

Four new assistant-authored development files contained 66 expected entries:
a two-page 32-result panel with lab context, a historical matrix with repeated
values, an explicitly dated visit and a skewed two-column scan. Files and labels
were hashed before any calls. The baseline was `079be7a`; all later passes used
those same unchanged bytes and labels through the real `muse-spark-1.3` import.

| Development observation | Baseline | Final live pass |
| --- | ---: | ---: |
| Successful report imports | 3 / 4 | 4 / 4 |
| Exact page/name/value/unit entries returned | 34 / 66 | 66 / 66 |
| Missing rows within accepted drafts | 0 | 0 |
| Extra rows / false omission flags | 0 / 0 | 0 / 0 |
| Date or lab-context differences among returned entries | 0 | 0 |
| Partial / unavailable inventories | 0 / 1 | 0 / 0 |

The dense baseline failed with `finish_reason:length` at exactly 4,000 output
tokens. All 32 entries in that document were unavailable; no partial draft or
saved records were accepted. They count against the end-to-end returned-entry
score, not as silently omitted rows in a successful draft. Natural omission
recall is still **unmeasured** because no accepted draft naturally missed a row.
These are small, development-tuned synthetic probes, not independent human-gold,
held-out or clinical-quality results.

The first fix set fixed per-stage output ceilings of 16,000 for extraction,
6,000 for verification and 12,000 for inventory, without adding retries. That
pass returned all 66 entries, but 32 dense-report excerpts omitted their printed
range/specimen/method lines. One narrative inventory also marked itself limited;
that partial result is retained. A second pass included the context lines but
exposed another issue: layout-mode PDF text interleaved adjacent columns, causing
32 exact-excerpt checks to fail. The local checker now also retains the original
PDF's content-stream text order. A passage must occur wholly in one ordering on
its cited page; no concatenation, fuzzy repair, cross-page rescue or OCR promotion
is allowed. Both transcriptions count toward the existing text bounds.

The final live pass returned all 66 entries and had **zero local excerpt
mismatches**. Dates, ranges, specimen, methods, repeated values and qualified
results matched the frozen labels. Scanned-image evidence still lacks independent
native-text support, and separate date linkage still requires review. An exact
text occurrence does not prove the model's interpretation or completeness.

All four rounds are retained: **46 real requests** (10 baseline, then three
12-call passes), 160,759 input and 70,990 output tokens. The estimated Standard
cost was **$0.50265625**, treating input as uncached at
[Meta's published rates](https://dev.meta.ai/docs/pricing-rate-limits). This is
session usage, not a provider invoice or account total. The $2 session cap was
not reached; the session was closed and its credential removed. Private artifacts
retain raw responses, request IDs, latency, hashes, failed imports and intermediate
checks. No protected evaluation or held-out files were accessed or modified.

The browser reopened the final cached draft without another model call, checked
and saved its 32 fields, opened its orbit satellite and downloaded the original
bytes unchanged. Asking “When was my MPV 9.8 fL?” initially revealed an offline
unit-parser gap. Literal blood-count units now work without conversion or dropping
unsupported conditions. The same browser question returned **2024-03-12** with
the page-2 excerpt, collection-date passage, lab range, specimen and method.

`python scripts/check_service.py`: **1,406 backend passed, 2 skipped; 221 frontend
passed; production build passed**. New regressions cover dense output, truncation
at every stage, multiline columns, non-stitching/page boundaries, OCR status,
combined text bounds, exact blood-count units and retained restrictions. The
existing Starlette/httpx deprecation warning remains. All **39 read-only service
checks** passed after save and restart, including historical availability,
unchanged originals, exact offline Ask, served build identity and unchanged
normal-workspace history. The orbit design is unchanged.

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
