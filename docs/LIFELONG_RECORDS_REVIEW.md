# Lifelong record core — 28 October 2026

The product value is one inspectable history owned by the person: collect scattered records, find an earlier event, compare recorded changes and open the source. A main-screen anatomy illustration is not needed for those jobs. Keep the reference card language, a daily overview and a useful timeline; a body-based navigator is only worth adding if it helps people find a record.

## Working scope

Eight reviewed fact kinds now persist: measurements (including arbitrary lab names and vitals), visits, provider-recorded diagnoses, procedures, prescriptions, vaccinations, imaging report text and other recorded text. Values and original-language labels remain strings; nothing converts a provider's wording into a generated diagnosis. Unknown names are retained without invented LOINC codes.

The current entry accepts CSV, text, PDF, PNG and JPEG, up to ten files in a review queue. Explicit CSV columns can describe all eight kinds. The local text reader recognizes its existing explicit lab grammar and preserves other content as source-linked text for review. PDFs with images require OCR or the Meta path so a selectable header cannot conceal a scan. Local OCR retains all transcription pages; Spark's structured path now passes one authored image/PDF smoke; broad document accuracy remains unmeasured.

Each accepted fact keeps original evidence, original and reviewed values, page/proposed region, extractor, review identity/time and server-owned availability. Exact dates, year/month dates, unresolved dates and unknown dates stay distinct. Two clocks apply to facts, source downloads, profile revisions and answers. Historical views withhold content whose date scope cannot be established; the explicit All recorded dates option keeps the availability cutoff while showing partial/unknown dates.

One transaction saves selected facts, compatible legacy measurement projections and a receipt. Repeated identical reviews return the original receipt; changed retries reject. Exact decimals that would round in a legacy float chart remain in the generic timeline only. Same-label/day disagreements preserve all values; different units stay unresolved. No winner or clinical meaning is inferred.

Height, weight and temperature use documented rational conversions, preserving printed values and units. Repeating decimal displays are marked rounded while exact fractions remain stored. General mass/amount conversions and HbA1c standardization conversions remain disabled. [Unit contract and sources](RECORD_UNIT_RULES.md).

## Service UI

Timeline and Files now include the broader facts, with type/facility filters, source excerpts, original downloads and explicit date controls. Local birth-date settings provide age markers only for exact recorded dates; profile changes do not silently advance an existing historical view. Home's existing three charts are labelled Featured measurements and link to the whole history.

The generic editor supports inclusion/exclusion, exact values, raw dates, facilities and restoration of the original proposal. Retry after an uncertain save preserves the exact reviewed payload. The design uses the existing charcoal cards and recessed panels. A compact editor for very large panels is further screen work; this milestone does not claim a finished native application.

## Evidence and limits

Full verification and final browser evidence are recorded in PROGRESS.md and `eval/step-b-browser.json`. Initial audit failures are retained: ambiguous CSV headers, reference text accidentally removed, legacy field compatibility, historical text exposure, decimal rounding and filtered UI counts were addressed. These are authored regression cases, not held-out performance results.

All data used for implementation and browser checks is authored synthetic data. No person's medical history was uploaded. Live Meta verification now records 16 requests, including 14 successful completions and two retained HTTP 400 failures; see C1_C2_REVIEW.md. Frozen baseline results remain unchanged and held-out inputs/labels/generators/previews remain untouched. No SOTA or clinical-validation claim follows from software tests.

Remaining product work: automated accuracy across broad scanned reports, generalized agent question tools, folder/ZIP intake, durable queue recovery, broad-record visit packets, and the planned native shell/Today screen. Clinical interpretation is outside this record-only scope. The broad-model question agent still uses the existing bounded measurement tools; the new timeline is not a claim of general medical question answering.

Project license, public commit/push, owner gold-label review and broad live qualification remain pending. The local B core changed no checklist item; the subsequent live smoke adds one, bringing the checklist to 7/17. No demo/video work was done.
