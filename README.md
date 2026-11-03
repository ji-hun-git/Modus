# Modus Records

[![Offline service checks](https://github.com/ji-hun-git/Modus/actions/workflows/verify.yml/badge.svg)](https://github.com/ji-hun-git/Modus/actions/workflows/verify.yml)

**Ask your history. See the original. Keep every correction.**

Modus brings medical records from different years and files into an inspectable
personal history. Upload a supported report, review the proposed fields, and
follow each saved result back to its source.

## What it does

- Imports CSV, text, PDF and images through supported local or explicitly selected Meta reading paths.
- Requires review before saving. Original files, printed units, dates, lab ranges, specimen and method stay attached to reviewed records.
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

Requires Python 3.11+ and Node.js 20.19+ or 22.12+.

```sh
python scripts/setup_entry.py
python scripts/check_service.py
python scripts/serve_service.py --port 8011
```

Open **http://127.0.0.1:8011/**. This checked development preview verifies the
source and frontend build, strips model credentials and runs offline. Saved data
stays in the ignored local database across restarts.

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

## Limits

This is a local, single-owner record-integrity prototype. It does not generate
diagnoses, clinical interpretation, risk scores or treatment advice. Recorded
dates and missing data do not establish whether care occurred. Unknown units,
incomplete dates and incompatible lab context can prevent a numerical comparison.

Production accounts, encryption at rest, verified masking/deletion and durable
personal conversational memory are unfinished. The service has not been
qualified for real-history production use.

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
