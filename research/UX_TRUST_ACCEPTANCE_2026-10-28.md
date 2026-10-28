# Record UX trust acceptance — 28 October 2026

Scope: independent source-code review of the contest frontend and generic history projection, informed by the owner's Korean review attachment. This is not a visual/browser audit, accessibility certification, medical validation, or production privacy assessment. No provider requests, credentials, held-out sets, or public Git were accessed.

## Display terms verified against primary sources

| Result title | Separate short explanation | Boundary |
| --- | --- | --- |
| HbA1c | A blood test that reflects average blood sugar over about 3 months. | The reported percentage is HbA1c, not a glucose concentration or an automatically calculated estimated average glucose. |
| eGFR | An estimate of how well your kidneys filter blood. | The number is not a health score or percentage. Keep the printed unit; do not infer a diagnosis or clinical stage. |
| LDL cholesterol | Cholesterol carried in the blood by low-density lipoproteins. | Do not rename unspecified cholesterol as LDL or infer a clinical interpretation from the value. |

Sources, checked 28 October 2026: [NIDDK A1C test](https://www.niddk.nih.gov/health-information/diagnostic-tests/a1c-test), [National Kidney Foundation eGFR](https://www.kidney.org/kidney-topics/estimated-glomerular-filtration-rate-egfr), [MedlinePlus LDL](https://medlineplus.gov/ldlthebadcholesterol.html). These support general definitions, not personalized findings. Clinical ranges and advice from those pages are outside this UI patch.

The test name should remain visible while the explanation appears directly beneath it or in an accessible disclosure. Replacing one unexplained acronym with another is insufficient. Explicit aliases can receive a consistent display name; qualified or unfamiliar labels retain the source wording.

## Verified contracts that the design must preserve

- `record_history_models.date_information` accepts only a real ISO calendar date as an exact day. Year/month/unknown/unresolved dates remain separate. A file's commit availability is a different timestamp from its measurement date.
- `history_view` freezes availability with `known_at`, filters exact facts by `as_of`, and withholds unsupported text/originals under historical date filters. Showing all recorded dates must retain `known_at`.
- Generic facts store string values and original units; qualifiers and textual findings must remain strings. Legacy numeric observation projections cannot reconstruct original precision already lost to floats. Original excerpts remain the evidence for those older records.
- Generic conflicts are based on the same exact label and day, then different numeric values or printed units. The server explicitly marks specimen equivalence unknown. Absence of a detected conflict is not proof that every source agrees.
- `SourceCubeEvidence` and `TimelineFact` original download links carry the captured `known_at` and optional `as_of`. A comparison must use the current view's fact IDs, not a fresh latest-data request.
- `MeasurementsWorkspace` covers only HbA1c, eGFR and LDL. During this patch the parent added the existing plot with connections disabled and retained the chronological table. Navigation and questions must not imply all generic measurement or record-type support.

## P0 findings and acceptance checks

1. **Do not manufacture a calendar date.** The new presentation helper initially formatted `2020-02-30` as `1 Mar 2020` and `approximately 2019` as `31 Dec 2018`. Parent corrected its parser to require explicit formats and validate the calendar day. Regression assertions now include approximate and seasonal text. `node --test tests/recordPresentation.test.mjs`: **7 passed** after the correction. Year `2012` stays `2012`; month `2012-04` shows `Apr 2012`; unresolved text stays verbatim.
2. **Do not pick a winning latest value by array order.** If two entries share the latest recorded date and differ, show both or a clear comparison entry point. Keep date, original unit, source, and unknown specimen relationship visible. Do not average them, overwrite one, or describe one as corrected without source evidence.
3. **Keep a comparison inside its captured scope.** With a late conflicting record, the older `known_at` view must contain only the earlier record; the current view may show the disagreement. Going from Home to comparison/original must not silently advance either cutoff. Hidden value, hidden source quote and unavailable original states must remain consistent.
4. **Do not turn generic facts into numbers.** Test `<5`, `>90`, `0.00`, `negative`, `not detected`, long imaging text and unknown unit strings. Text values must not become zero, infinity, a chart point, or a health verdict. Missing units are unknown, not defaults. Typography may render an explicitly known unit spelling more legibly; the raw unit remains available.
5. **Keep measurement and availability dates distinct.** Test an old measurement uploaded today, a late report with an earlier measured date, and three metrics last measured in different years. Home orders clinical records by their validated occurrence dates; document management may offer added-date order. Every latest value carries its own measured date.

## P1 acceptance matrix for the redesigned Home

| Input or action | Required result |
| --- | --- |
| Vaccination, encounter, diagnosis-as-recorded, prescription and imaging text | Remain readable as their own record types; do not count all as lab results or imply current treatment/diagnosis status. |
| Exact date plus year/month/unknown dates | Exact events appear in chronological groups; incomplete dates have a visible separate group and no invented day. |
| Same latest day, different values | No single winning value selected through ID order; comparison exposes both scoped sources. |
| Same day, different units | State that printed units differ; no automatic conversion/comparability claim or clinical warning. |
| Source contains facts after historical cutoff | No unavailable excerpt/original appears through a Home or comparison shortcut. |
| Record title absent or ambiguous | Use a neutral title supported by facts; do not invent hospital, report type or diagnosis. Filename remains in source details. |
| Evidence from CSV or image with no page | Omit page-specific filler; source metadata should match actual format. |
| Value edited during review | Show reviewed fact and original excerpt as distinct, without rewriting the source quote. |
| Unknown or qualified metric name | Keep source label. Do not infer mapping by a broad substring. |
| Keyboard and narrow viewport | Value, unit, date, review text and source action remain available; state never relies on color alone. Browser verification still required. |

The owner attachment also raises accounts, sharing, deletion, multi-person separation and remote processing. Those are separate product readiness questions. This inspection does not establish that they are complete or that they are missing; the UI patch should not advertise them without verified evidence.

## Independent review of the new implementation

Static review of `HealthRecordOverview`, `overviewRecords`, `LatestResultCard`, `SourceCubeEvidence`, `RecordConflictComparison` and `sourceDisplay` found:

- Latest measurements are selected by the server-validated occurrence date, and all results on that latest date remain visible. Partial/unknown dates have a separate group. No averaging, automatic winner or clinical verdict was introduced.
- Conflict comparison resolves group IDs against the supplied scoped view, keeps original values and units, states that samples/methods may differ, and preserves the original-download cutoffs. Evidence also resolves requested IDs back to current scoped facts.
- Home is keyed by `scope_id`, resetting its retained detail state when the captured scope changes. The designer also added canonical resolution inside `OverviewRecordDetails`: retained objects supply IDs only; current facts supply the title, date, source, values and withholding state. Absent facts show unavailable. This was independently re-read after the fix.
- Evidence/Documents corrections are now present: an excerpt with unknown dates *may* fall outside a cutoff (it is not proven to do so), and an empty search says no documents match the search. Comparison close returns focus to the invoking button in code; browser confirmation is pending.
- The newly enabled measurement plot uses actual timestamp spacing, separates units, validates exact dates, keeps conflicting points and their source IDs, and disables connecting lines. It includes no clinical thresholds or verdicts. Recommended refinements sent to the parent: avoid saying only “different values” when different units also cause a warning, and make independently scaled y-axes clear. The chronological table remains the exact-value alternative.
- The visual result and keyboard behavior require the parent browser verification. This static audit does not substitute for that step.
