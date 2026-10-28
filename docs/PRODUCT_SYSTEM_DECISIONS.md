# Product and system decisions — 28 October 2026

## Product we are building

Modus turns personally held medical files into a lifetime history that the owner can inspect, correct and carry forward. The unit of the experience is a source file: one cube, one file. Its face shows actual recorded content and dates; opening it shows accepted facts, the original excerpt/page and the original file when that file is permitted in the selected date scope. The cubes accumulate into a useful collection. There is no generated health score or decorative anatomy on the main screen.

The broader product goal remains lifelong health understanding. The current contest candidate stays within record handling: facts as recorded, explicit review, differences, provenance and availability replay. An original diagnosis or prescription can be retained verbatim; this is not permission to generate medical advice. The owner's participant rules exclude AI medical/health advice, and organizer approval of this bounded entry remains unresolved.

Current implementation: eight fact kinds in Timeline/Files, reviewed transactional saves, local profile/date support, source preservation and bounded real Spark extraction/record-tool probes. Current assistant tools still cover the three featured measurement families. Folder/ZIP import, broad source-location accuracy, generic-fact questions, a useful visit packet, encryption/session security/deletion and native delivery remain incomplete. An uploaded file is not automatically a complete or medically correct history.

## The comment we received

The comment is useful about standards and evaluation, but its claims that nobody has built similar personal records, or that chatbots cannot maintain histories, are unsupported. A review commit establishes when a fact entered Modus's reviewed history; it does not establish when the person or clinician first knew it. Preserve occurrence, report issuance, receipt/import and review/availability separately wherever available. Owner edits remain attributed edits, not medical truth.

See research/COMPETITIVE_REVIEW_2026-10-28.md for primary sources. HealthEx announced a Meta Muse connection on 8 September 2026 and ten startup integrations on 27 October 2026. Guava, PicnicHealth, Apple Health Records, HealthEx Wallet and 나의건강기록 already establish much of the aggregation, timeline and grounded-assistant baseline. Function's financing is an adjacent commercial signal, not proof of accuracy or a direct feature target. Public product descriptions cannot establish the absence of a competitor's internal capability.

## Architecture decision

Use a fixed document workflow and one bounded read-only question agent. Development designer/reviewer agents are separate from the product runtime. No framework, vector store, model council or protocol earns a place merely by being fashionable.

1. Local source handling owns bytes, type checks, hashes, identifiers and extraction limits.
2. A parser/OCR route remains available without a provider. Explicit Spark processing produces a schema-validated proposal and separate source check.
3. Owner review creates a transactional receipt; originals, proposals and edits remain separate. Imported text and model arguments cannot authorize writes.
4. Scoped retrieval first restricts records to the captured availability and occurrence bounds. Typed tools produce numerical statements. The model selects permitted tools and supported claim IDs.
5. The file cube exposes the same source/fact relationship the backend enforces. It does not invent findings, clinical meaning or hidden source precision.
6. Release gates bind tested source/build identity. Actual API traces record requested/returned model, failures, usage and latency. Model aliases remain mutable; tests do not establish broad model accuracy.

The supplied Agent Building Kit has materially shaped specification, tool authority, failure tests, stack freshness and release identity. It has not completed production identity, durable review recovery, cancellation, undo, encrypted storage, redacted telemetry or deletion. The real HTTP 400 tool-choice failure demonstrates why code and fresh live evidence must outrank a remembered API contract. See docs/AGENT_KIT_ADOPTION.md and research/ARCHITECTURE_PRIVACY_AUDIT_2026-10-28.md.

## Technical contribution we can defend

Bitemporal databases, provenance, human review, OCR/VLM extraction and citation grounding are established methods. We have no evidence of a new foundation model, new database algorithm, first-ever product or SOTA extraction accuracy. The research proposition is an evaluated system combining owner review, source-preserving conflict handling, historical evidence constraints and selective disclosure, exposed through a file-based interface that makes verification fast.

| Experiment | Comparison | What would establish value |
|---|---|---|
| Temporal evidence | Event-date-only vs occurrence + Modus availability | Unavailable evidence leaks, correctly withheld sources, and successful historical tasks; count both over-disclosure and over-withholding. |
| Extraction workflow | Local parser/OCR vs Spark vs Spark + source check | Exact label/value/unit/date/page coverage, invented fields, abstention, owner corrections, review time, latency and reported usage. A second model pass must earn its cost. |
| Evidence interface | Ordinary file list vs file cubes with adjacent evidence | Correct source-finding, correction and disagreement tasks; task time/clicks and owner comprehension. Visual preference alone is insufficient. |
| Selective disclosure (planned) | Whole document vs locally prepared minimal context | Identifiers exposed, bytes/pages/tokens transmitted, supported-answer quality and cases where masking destroys useful context. |

Use separately reviewed development cases for iteration. Keep current held-out sets sealed. Build and freeze broader cases without reading existing held-out inputs, labels or generators. Human gold review and an explicitly authorized evaluation protocol precede held-out scoring. No current software-test count substitutes for these experiments.

## Privacy without removing usefulness

The target is a local encrypted vault with cloud help chosen per task, not a promise that blacked-out names make medical histories anonymous. Today the prototype uses plain SQLite and has no authenticated owner session or complete deletion flow. Continue with synthetic examples until real-data controls are implemented and qualified.

Proposed data path:

Original file -> encrypted local vault -> local text/region extraction and identifier detection -> owner-visible disclosure preview -> only selected masked text or irreversibly redacted image regions sent to the configured Standard provider -> typed draft -> local restoration of private identifiers -> owner review -> local history.

- Keep the identifier/token map, full originals, birth date and keys on the device. Use a per-profile encryption key protected by Windows credential protection or macOS Keychain; protect temporary files, caches and backups too.
- Apply name/contact/account/record-number masking to text AND actual pixels before transmission. Remove metadata, barcodes/QR codes, embedded text and thumbnails; a visible rectangle over a PDF is not sufficient redaction. Bound decoder work and isolate parsing.
- Preserve exact dates and units locally. Ask the cloud only for needed content; compute time comparisons locally. Date shifting is an optional task-specific method with a local mapping, not a blanket privacy guarantee. Rare events and retained dates can still identify someone.
- Let the owner inspect the exact outgoing payload, change it, cancel or use the local path. Do not silently send a whole lifetime record to improve a single answer. Local masking failure should stop cloud submission rather than silently fall back to raw content.
- Authenticate the local application session; validate origin/CSRF boundaries, limit request sizes and remove raw content from default diagnostics. Record disclosure receipts with minimal metadata. Provide deletion for sources, derived facts, temporary files, indexes and backups with an honest retention contract.
- Standard Meta API content is not used for model training, but Standard does not mean zero retention. Meta says ZDR requires separate organization-level enablement and has feature/exception limits. This account's ZDR status is not verified. Do not claim anonymous, end-to-end private cloud inference, HIPAA compliance or zero retention.

Sources checked 28 October: https://dev.meta.ai/legal/terms-of-service and https://dev.meta.ai/help/policies-and-privacy/zero-data-retention . Architecture choices are proposals; account and regulatory qualification are separate work.

## Hackathon evidence priorities

The rendered official rules were rechecked on 28 October: Impact 30%, Meta tooling 25%, Technical Depth & Execution 20%, Demo 25%. The owner-supplied FAQ's equal weighting remains a discrepancy; the participant health-advice exclusion remains a working constraint. Official rules: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver . Submission deadline remains 5 November 2026, 11:00 KST; internal buffer 4 November, 18:00 KST.

| Criterion | Concrete work |
|---|---|
| Impact | Show a person finding/correcting an old record and preparing relevant history faster; interview people before claiming daily demand or willingness to pay. |
| Meta tooling | Demonstrate real multimodal reading, source verification and bounded tools. Probe SAM source regions only if reliable geometry improves evidence inspection; model count is not success. |
| Execution | Preserve all file content and conflicts, enforce time scope/review, recover failures, qualify privacy boundaries and ship measured clean builds. |
| Demo | One coherent sequence: files become cubes -> inspect a source -> correct/save -> add a late conflicting file -> replay earlier availability. No video work is authorized in this expansion phase; the final required video remains outstanding. |

We should compete on this specific owner workflow. We have not demonstrated that Modus beats these companies overall. The file-cube evidence interaction is now implemented and browser-verified. Next build priorities: generalize bounded fact tools and cited exports; implement the local privacy boundary; run reviewed development comparisons. Keep source and eligibility claims exact.
