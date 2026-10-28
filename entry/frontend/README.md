# Modus Records frontend

The independent record-review entry. Its primary destinations are **Replay**, **Records** and **Changes**. It does not load the broader Modus frontend or render clinical assessments, physiological charts, care plans, genetics or reference interpretations.

## Run and build

From this directory:

```sh
npm ci
npm run dev
npm run build
```

The development UI uses port **5174** and proxies `/api` to the isolated entry API at **127.0.0.1:8011**. The entry server can serve this directory's built `dist/`. See the entry's top-level instructions to launch that server. The package versions and lockfile come from the existing frontend; no new runtime dependency was introduced.

API shapes and request boundaries are defined in [the entry contract](../docs/API_CONTRACT.md). The browser never receives provider credentials. Static authored examples are in `public/examples/`; they contain synthetic records only.

## Interaction contracts

- Replay defaults to measurements through 31 December 2021, with records available by that day's end in UTC. Comparing with current records keeps the event cutoff and captures both availability bounds on the server.
- A response is displayed only beneath its matching requested scope. Pending/failed changed scopes hide evidence, source access, questions and exports. An answer from a previous scope is discarded.
- Snapshot/comparison exports, questions and committed-original links use the returned, resolved bounds. A source ID or scope ID does not substitute for those bounds.
- Review retains the immutable proposal beside editable fields. Closing/reopening keeps edits in the same tab. Adding requires explicit included rows. Busy close, backdrop and Escape are guarded.
- An explicit first-attempt 400/404/422 rejection permits correction. A lost response or server failure freezes the submitted draft and row payload for identical retry. A successful duplicate identifies the original commitment without implying another arrival.
- Adding a record preserves the existing replay. **View what changed** loads a fresh comparison; **Open updated view** captures current availability for the same measurement period.
- Questions render exact returned claim objects; model free text is never rendered as a finding. Local execution is labelled separately from Meta execution. Actual arguments/results are secondary disclosure.
- Conflicting values retain their individual dates, units and source links. The UI does not choose a correct value, infer specimen equivalence or convert units.

Unsaved reviews are not restored after a page reload or process restart. The interface states this and registers a page-leaving warning. There is no pretend cancellation or undo for a stored commitment. Live model execution remains unmeasured until separately verified with actual access.

## Verified on 27 October 2026

TypeScript and the production build passed. Headless Edge exercised the built UI against a separate entry database on port 8011; the full-product service and database were untouched.

The real workflow uploaded `delayed-history.csv`, inspected the draft original, changed a value to 83, closed/reopened the review, and restored the original 82. The server then committed one measurement. The test deliberately dropped that successful response to exercise uncertainty; an identical retry returned the existing commitment. The historical view and export remained **2 records / 6 measurements**. Comparing the same event period with current availability produced **3 records / 7 measurements**, preserving **82 and 96** in one disagreement group.

The rehearsal verified snapshot/comparison JSON exports, the committed original, historical-original rejection, removal of the draft-original bypass after commitment, an actual local record question and change history. The 390 px layout had no document overflow and the browser reported no JavaScript errors.

A separate read-only regression covered changed event/knowledge request failure and retry, comparison failure and retry, stale answer rejection, mobile navigation, modal focus containment/restoration and accurate measurement-date labels. Failure responses and the late answer were intercepted within that browser context. No real write request was forwarded by that second run.

Evidence lives in the entry's `demo/` directory: `replay-before.png`, `review-record.png`, `review-recovery.png`, `replay-comparison.png`, `evidence-three-dates.png`, `replay-mobile.png`, and the three `rehearsal-*.json` scoped exports. The recovery image shows the intentionally lost response after a real successful synthetic commit. These checks establish this local workflow, not clinical validation, production readiness, model performance or contest eligibility.
