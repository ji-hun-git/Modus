# Checkup and lab history focus

Owner selected this focus on 2 November 2026 KST.

## Product promise

Bring your medical reports together, follow each recorded result over time, and retrieve the original when you need it. Lead with checkups and lab results; retain visits, prescriptions, vaccinations and other reviewed records as context. Do not infer a diagnosis, causal medication effect, risk score or treatment recommendation.

## Implemented in this pass

Home uses medical-history language. The existing longer-report selector groups exact recognized names into blood sugar, cholesterol/triglycerides and kidney tests; other measurements and non-measurement kinds stay available. This is navigation, not a clinical classification or completeness assessment. No records are filtered out or rewritten.

A compact medical-name/reference disclosure beside the selected history uses the existing 24-concept authored vocabulary and fixed NIDDK/MedlinePlus references. It separates the saved name, medical name and general reference from personal source evidence. Unknown names, qualified assay labels and non-measurement records receive no inferred terminology. Links are explicit, HTTPS allowlisted and do not send a referrer. No remote reference fetch happens automatically.

Expanded HbA1c, eGFR, LDL and HDL names were checked on 2 November against [NIDDK A1C](https://www.niddk.nih.gov/health-information/diagnostic-tests/a1c-test), [MedlinePlus eGFR](https://medlineplus.gov/lab-tests/estimated-glomerular-filtration-rate-egfr-and-gfr-tests/) and [MedlinePlus cholesterol](https://medlineplus.gov/lab-tests/cholesterol-levels/). Other catalog references retain their existing 30 October provenance; no claim of a fresh full-catalog review.

## Next work that would deepen the niche

1. Review report-supplied reference intervals, specimen and method alongside each value. Preserve absent fields as unknown; do not supply population thresholds automatically.
2. Build a descriptive previous-checkup comparison that preserves incompatible units, changed methods and conflicting records.
3. Prepare a sourced visit summary that the owner can review and export, without medical recommendations.

These three items are product direction, not completed features or authorization to broaden the contest scope. Broader condition advice remains outside the competition app.

## Verification

Offline service check: 973 backend tests, 149 frontend tests and production build passed. New tests cover name/evidence separation, unknown and qualified names, non-measurement exclusions and lossless grouping. Browser: ten-field report retains all options under groups, HbA1c selection retains dated history, reference disclosure shows NIDDK, historical point opens its exact source excerpt. No model requests, evaluation/held-out access, or stored-record changes. Orbit visual identity retained.
