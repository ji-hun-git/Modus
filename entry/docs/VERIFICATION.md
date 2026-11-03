# Verification

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
