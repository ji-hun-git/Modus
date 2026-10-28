# Modus service design v7 — 28 October 2026

The owner supplied four interface images and requested this design direction. They are visual references; no image assets, source code or numerical examples were copied into the application. The prior request for everyday names remains: Average blood sugar (HbA1c), Kidney filtering (eGFR), Cholesterol (LDL). Original values, units and source text are unchanged.

## Composition

Charcoal canvas, graphite cards, darker inset charts, quiet borders, monospaced measurements and restrained mint points. A compact top navigation replaces the desktop sidebar; phone bottom navigation remains. The upload strip leads to the existing per-file review flow. Measurement counts sit beside their section; dates and All history remain reachable. Recent files and the assistant share the lower grid. Files, Measurements, Replay, Activity, source dialogs and review controls use the same palette.

Two engineering/design agents contributed the chart implementation and an independent visual review. Review refinements reduced space above the cards, added inset plot surfaces and strengthened the disagreement legend. This is a design review, not a user study or proof of improved usability.

## Chart contract

Every point derives from an eligible observation in the current captured view. X positions use elapsed dates, not equal spacing. Values are not converted or smoothed; no threshold, risk category, predicted value or inferred missing measurement is drawn. Separate units have separate scales. Same-day differing values remain separate amber diamond markers and break adjoining lines; lines also stop across incompatible-unit records. Matching date/value/unit points retain every source. Clicking or pressing Enter opens source details, and closing returns focus. The full dated text history remains available. These are compact factual plots, not a clinical trend interpretation.

The three seed histories are sparse. The interface deliberately contains no decorative heatmap, percentile distribution, completeness ring or fabricated density. The supplied business-dashboard figures do not become Modus data.

## Verification and delivery

Eight new geometry tests cover elapsed time, conflicts, backend conflict flags, duplicate provenance, unit separation, invalid values/dates, a single date and precision. Existing queue tests remain. Actual browser evidence and full gate results are recorded in eval/reference-v7-browser.json and release/reference-v7-gate.log after verification. Test results do not establish real model quality.

Backend contracts, frozen baselines and private held-out sets are unchanged. No live provider call is made in this revision. The previous consumer-v6 public candidate/ZIP remain frozen; a fresh allowlisted v7 candidate is prepared separately. No license decision, commit, publication or contest eligibility conclusion follows from this design revision.
