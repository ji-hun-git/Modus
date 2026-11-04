# Modus frontend

The React / TypeScript interface for the local record workspace. **Home** brings
source files, selected readings and Ask together. **Records** opens the timeline.
**More** contains Ask, Summary, Trends, Documents, Replay and Changes.

## Development

Install and check the application from the repository root using the
[setup instructions](../../README.md#run-locally). Start the checked backend:

```sh
python scripts/serve_service.py --port 8011 --ui-port 5174
```

In a second terminal, from `entry/frontend`:

```sh
npm run dev
```

Vite serves **http://127.0.0.1:5174/** and proxies `/api` to
**http://127.0.0.1:8011**. Open the launcher's access file when prompted. Keep
provider credentials on the server; they never belong in a Vite variable or bundle.

```sh
npm test
npm run build
```

The production server serves `entry/frontend/dist/`. After source changes,
rerun `python scripts/check_service.py` from the repository root and restart
the checked preview so its source and build hashes match.

## Interaction contracts

- **Review precedes writes.** Proposed fields stay beside their original evidence.
  Navigation preserves edits and exclusions. Validation covers every included
  row, including entries on another page.
- **Uncertain saves recover the same transaction.** A lost response preserves
  the submitted payload for identical retry. A duplicate receipt does not create
  another record or imply a new arrival.
- **Evidence follows the selected history.** Answers, original-file access and
  exports use the captured recorded-date and availability bounds. Pending or
  failed scope changes cannot display stale evidence as current.
- **Corrections preserve the source.** A reviewed amendment creates a saved
  version and invalidates affected explanations. The original file stays intact.
- **Findings come from checked tools.** Arbitrary model prose is not rendered as
  a finding. Offline and Meta execution are labelled separately.
- **Differences remain inspectable.** Conflicts retain their values, dates, units
  and source links. The interface never chooses the correct value.

Unsaved reviews remain in the current tab; a reload or process restart loses
them. The interface warns before leaving. Saved records persist in the encrypted
local store. Browser sessions are kept in memory, outside URLs and browser storage.

Supported behavior is defined in the [product guide](../docs/PRODUCT.md) and
[API contract](../docs/API_CONTRACT.md). Dated browser checks and their scope
are recorded in [Verification](../docs/VERIFICATION.md).
