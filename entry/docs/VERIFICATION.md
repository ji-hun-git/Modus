# Verification

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
