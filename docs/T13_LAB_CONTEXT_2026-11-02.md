# T13 — Lab context and previous checkup

Local implementation, 2 November 2026 KST. Preview: http://127.0.0.1:8018/. This has not been pushed or qualified by the final competition release gate.

## Delivered

- Optional lab reference range, specimen and test method survive generic CSV ingestion, typed extraction proposals, review, save, export/projection, append-only corrections and original-evidence inspection. Null means unknown; ranges are not interpreted or generated from generic thresholds.
- Context supplied by a draft cannot silently disappear through an older review client. Explicit null is distinguishable from omission. Legacy receipts retain their original digest behavior.
- Muse extraction and verification schemas require source-supported context. This code was tested offline; no new live Muse extraction quality is claimed. Automatic PDF/OCR context extraction remains unproven.
- The selected Home reading can open a comparison to the previous fully dated matching test. It uses all records in the captured history, not just the rendered page. Existing exact terminology aliases can match labels; unknown names require normalized label equality.
- Same-date candidates stay separate. At most 50 prior candidates render, with the total disclosed. Unit, specimen, method, range/facility differences and incomplete dates produce notes. A numeric difference requires one prior result, unqualified numbers and no comparison notes. No conversions, normality classifications or advice are introduced.
- Each side opens original evidence using the same event and availability bounds. Corrections retain the original file, excerpt and proposed metadata. Context is withheld with values outside the visible temporal scope.
- Orbit layout retained; comparison is a disclosure within the existing result journey.

## Verification

`python scripts/check_service.py`: 985 selected backend tests, 152 frontend tests, production TypeScript/Vite build passed. One existing Starlette/httpx deprecation warning remains. The guarded service runner blocks external requests and protected evaluation paths. Full check/evaluate/package/release commands were deliberately not run because the user excluded evaluations and held-outs.

New regression coverage: import/review/commit retries; missing context protection; original-byte integrity; metadata corrections; unchanged captured historical snapshots; pre-availability rejection; undated metadata withholding; pagination-independent comparisons; changed units/methods/specimens; date ties; numeric qualifiers; exact long-decimal subtraction; proposed context evidence support; frontend payload/retry preservation and escaped/withheld rendering.

Actual browser verification on a private synthetic database: imported Example-checkup-2025.csv and Example-checkup-2026.csv; reviewed all three lab context fields; saved both; compared 90 and 98 mg/dL with different printed methods; observed the method note and no numeric difference; opened earlier evidence and downloaded its original. Download SHA-256 matches the uploaded fixture: `1439630f68a921cc812c6bcd907e32a93e2dfe49e2536389d9e7970b3d5262a9`.

Local evidence: `release/T13-lab-context/comparison.png`, `release/T13-lab-context/review.png`, and `release/service-check/report.json`. The example values and ranges are authored test data, not reference recommendations. No owner's medical records were used.

## Remaining work

Live multimodal extraction/verification qualification; genuine model-quality comparisons; independently reviewed training data; authorized local model provisioning and adapter training; release freeze and publication. The separate [medical adapter experiment](../research/medical_adapter/README.md) has data and a recipe, not a trained model or measured improvement. Public Synthea rows lack range/specimen/method and cannot validate those targets.
