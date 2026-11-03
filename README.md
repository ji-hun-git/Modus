# Modus Records

[![Offline service checks](https://github.com/ji-hun-git/Modus/actions/workflows/verify.yml/badge.svg)](https://github.com/ji-hun-git/Modus/actions/workflows/verify.yml)

**Ask your history. See the original. Keep every correction.**

Modus brings medical records from different years and files into an inspectable
personal history. Upload a supported report, review the proposed fields, and
follow each saved result back to its source.

## What it does

- Imports CSV, text, PDF and images through supported local or explicitly selected Meta reading paths.
- Requires review before saving. Original files, printed units, dates, lab ranges, specimen and method stay attached to reviewed records.
- Reopens a previously read scan for review while offline, without another model call.
- Lets you review and correct rows flagged by Muse, including additions to an already saved report. Earlier views and original evidence remain intact.
- Finds recorded facts across measurements, visits, prescriptions, vaccinations, procedures, diagnoses as recorded, imaging text and other source text.
- Keeps corrections as new versions. Original excerpts and earlier availability views remain preserved.
- Displays conflicting values without choosing a winner.
- Compares checkups and exports a human-reviewed summary with source evidence.
- Shows dated measurements alongside clickable original evidence in the file-orbit workspace.

Ask supports exact numeric conditions, earliest/latest matching results, counts,
source-backed histories and recorded differences. Follow-up questions retain
the original condition, units and temporal view.

## Run locally

Requires Python 3.11+ and Node.js 20.19+ or 22.12+, with an unlocked native OS
credential store (Windows Credential Manager, macOS Keychain, or Linux Secret Service).

```sh
python scripts/setup_entry.py
python scripts/check_service.py
python scripts/serve_service.py --port 8011
```

Open **http://127.0.0.1:8011/**. This checked development preview verifies the
source and frontend build, strips model credentials and runs offline. Saved data
stays in the ignored SQLCipher-encrypted local database across restarts. Its
random 256-bit key stays in the OS credential store, separate from the browser's
access file. Tests use isolated disposable keys and real encrypted databases.

For an existing plaintext database, stop its service first, then run:

```sh
python scripts/encrypt_records.py release/offline-service/records.db --execute
```

The explicit migration verifies every stored value and original file before
replacing the database, and leaves an independently verified encrypted recovery
copy. It refuses active locks or outstanding journals. The app will not silently
open plaintext storage, replace missing history, or generate a replacement for
a missing key. Keep the database's `.modus-vault.json` metadata with the database;
recovery also requires the original OS credential entry. Copying files alone to
another computer is insufficient. See [storage and recovery](entry/docs/API_CONTRACT.md#encrypted-local-storage--4-november-2026).

Choose **Open access file** and select the `Modus-8011.modus-access` file at
the location printed by the launcher. Keep it private. Restarting replaces it;
reloading the browser requires opening it again. **More → Lock records** locks
every session. Sessions expire after 30 minutes without activity or 8 hours total.

The checked launcher restricts its data directory and access file to the OS
owner. Record APIs, originals and exports require a short-lived local session.
Session credentials stay in memory, outside browser storage, cookies and URLs.
The API also blocks cross-origin browser requests, requires an explicit header for
writes, bounds uploads before parsing and prevents browser caching of responses.
Errors omit raw validation input, and request URLs are not written to access
logs. These [local protections](entry/docs/API_CONTRACT.md#local-privacy-boundary--3-november-2026)
preserve original evidence and complement encrypted storage. They are not
multi-user authentication.

For Vite development, start the checked backend with `--port 8011 --ui-port 5174`,
then run `npm run dev` in `entry/frontend` and open `http://127.0.0.1:5174`.
Use the generated `Modus-5174.modus-access` file. Access is bound to that proxy
origin; the backend's direct browser origin cannot unlock the same session.

The starter records and supplied examples are authored synthetic data. They are
not a real person's history or evidence of clinical validation.

## Models and evidence

Meta Muse Spark is the only hosted model in the product path. Explicit model
reading proposes structured fields for review; permitted agent reads operate on
captured history. Deterministic tools compute authoritative numbers. A model
cannot execute SQL or shell commands, fetch arbitrary URLs, write records or
change permissions.

Model execution and offline computation are labelled separately. Credentials
belong only in server environment variables, never browser code, Git or CI.
Test transports are not live-model evidence. [Workflow](entry/docs/AGENT_WORKFLOW.md)
and [verification boundaries](entry/docs/VERIFICATION.md) describe the contracts.

A small live development probe exercised report extraction, explicit review and
bounded Ask, exposing and fixing boilerplate extraction and fixed-filter tool-call
failures. Its [results and limitations](entry/docs/VERIFICATION.md#live-report-reading-and-bounded-ask--3-november-2026)
are separate from protected evaluations and do not establish general accuracy.
A [harder six-report follow-up](entry/docs/VERIFICATION.md#harder-live-report-probes--3-november-2026)
reports exact row errors, false omission flags and unresolved date-label ambiguity.
A [dense-report follow-up](entry/docs/VERIFICATION.md#dense-reports-and-multiline-evidence--3-november-2026)
fixes truncated drafts and multiline source evidence, with all 66 authored entries
returned in the final live pass. These remain development results, not general accuracy.
A [scanned-report probe](entry/docs/VERIFICATION.md#scanned-reports-and-offline-review-recovery--3-november-2026)
returned 84/84 authored results in both live passes with no false omission flags.
Controlled deletion checks detected 84/84 removed rows in each pass; natural
omission recall remains unmeasured. The probe also fixed scan consistency checks
and exposed an offline draft-recovery issue, now covered by browser verification.

## Limits

This is a local, single-owner record-integrity prototype. It does not generate
diagnoses, clinical interpretation, risk scores or treatment advice. Recorded
dates and missing data do not establish whether care occurred. Unknown units,
incomplete dates and incompatible lab context can prevent a numerical comparison.

Production accounts, portable key recovery, verified masking/deletion and
durable personal conversational memory are unfinished. Encryption covers the
record database, its saved originals and database journals; it does not encrypt
files you upload from elsewhere or exports you download. Migration does not
securely erase old disk blocks, snapshots or earlier copies. The service has
not been qualified for real-history production use.

The offline service check is a software regression gate, not a model-quality
evaluation or final release qualification. Historical measured results remain
version-specific in [SCOREBOARD.md](SCOREBOARD.md); they must not be generalized
to later code or broader medical tasks.

## Documentation

- [Product flow](entry/docs/PRODUCT.md)
- [API contract](entry/docs/API_CONTRACT.md)
- [Data provenance](entry/docs/DATA.md)
- [Record terminology](entry/docs/TERMINOLOGY_RETRIEVAL.md)
- [Reviewed summaries](entry/docs/RECORD_BRIEF.md)
- [Contributions](entry/docs/CONTRIBUTIONS.md)

First-party license selection is pending; public visibility does not grant an
open-source license. Dependency terms remain in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
