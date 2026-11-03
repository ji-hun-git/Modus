# Modus Records API v1

## Literal-value history questions — 3 November 2026

For an already resolved history request, its hosted read tool accepts only `{}`.
The server inserts its previously validated filters; the model selects the
permitted operation and returned claim IDs without retyping fixed arguments.
The entire returned batch is checked before any read executes. Any model-supplied
filter is rejected, including the string `"null"`. No coercion, fallback answer,
new tool, additional request or record-write authority is introduced. Unresolved
investigations retain their separately bounded planning protocol.

`POST /api/history/chat` recognizes questions such as “When was my Ferritin
30 ng/mL?” as exact numerical equality without requiring the word “exactly”.
This shorthand requires one resolved test, an adjacent literal value and an
explicit unit. Unqualified numbers, extra conditions, negation and unsupported
source/method restrictions still require clarification. Recorded-date bounds,
earliest/latest selection and captured availability remain binding; units are
not converted. The same anchored plan is required of any optional Muse planner.
No endpoint, authority or model call is added.

## Report row inventory — 3 November 2026

Historical tables inventory each result cell with its unchanged printed test
name. Dates and column headings may not be appended to labels. All duplicate
entries retain the existing literal, one-to-one matching requirements.

`completeness_check.disagreements` additionally retains a unit disagreement
when exactly one unmatched inventory row and one unmatched field have the same
page, literal label/value and entire whitespace-normalized source passage, and
exactly one reading omitted the unit. Two different non-empty units are never
paired: they may represent separate printed results, even with a shared passage.
Exact matches take priority; ambiguous repeats and different passages remain
possible omissions. Neither value nor unit is converted or overwritten. The
inventory row retains `matched_field_id:null`, `related_field_id` and
`reason:unit_disagreement`; it cannot be submitted as a reviewed omission.
The existing field gets `inventory_check.status:unit_disagreement` with
`proposed_unit` and a visible review reason. The owner corrects that field using
the existing review editor. Disagreements continue to restrict dated source
disclosure, and both original proposals remain immutable. Older drafts are not
rewritten or re-extracted automatically. This adds no model call or write authority.

The separate reading now checks disagreement in both directions. An extracted
field absent from a readable, non-truncated inventory page gains a visible
review reason; it is never silently removed. The immutable extraction proposal
retains `inventory_check.status: matched|unmatched|unavailable` per field.
Failed, limited or truncated inventory pages cannot establish an unmatched
field. Matching is still literal, page-scoped and one-to-one. No additional
provider call or commit authority is introduced. Prompts distinguish report
boilerplate from person-specific recorded statements, including negative findings.

Explicit Meta PDF/image reading adds a third, source-only `InventoryReportRows`
request for each page group. It receives the same original pages without the
extracted fields or verifier results. Each response must cover exactly that
group's original page numbers, with bounded verbatim rows, proposed regions,
readability and truncation flags. The extraction/source-check passes are unchanged.
The maximum is now 12 provider requests for 12 pages (three per group); an empty
extraction skips field verification but still runs the inventory. No automatic
retry, repair, alternative provider or model-authorized write is added.

`extraction_review.completeness_check` is additive: version
`report-row-inventory-v1`, `status:completed|partial|unavailable`, fixed
`completeness:not_established`, `review_required:true`, `inventory_rows`,
`matched_rows`, `pages` and `omissions`. Every omission includes a server ID,
original page, literal label/value/unit, excerpt, proposed bbox,
`local_support:matched_text|mismatch|unavailable`, null `matched_field_id` and
`reason:not_in_proposal|source_unconfirmed`. Page entries retain checked/unavailable
status, model readability, truncation and independent text availability.

Code compares rows one-to-one using the same original page, exact label/value/unit
and overlapping contiguous excerpts. It does not merge aliases, convert units,
coerce numerical spelling or drop repeated rows. Unsupported text remains a
flag requiring source review. Image/OCR agreement never becomes independent text
support. Inventory failure preserves the extracted draft with an unavailable
check; partial/unreadable/truncated pages remain visible. Zero flags never prove
complete extraction. This is a same-model second reading, not an independent
model-quality measurement.

Inventory candidates never become facts automatically. The owner can explicitly
select a flagged row, edit its fields, and save through the separate reviewed
omission contract below. A candidate ID is still invalid in `reviewed_facts`.
Flags remain unchanged in the stored draft and on re-opening, without
re-extraction or extra calls. Original bytes and page evidence remain unchanged.
The review UI shows at most six flagged rows at once, with paging and an original
download. Existing cached drafts are not retroactively inventoried. Offline
readers do not claim to run this model check.
Possible omissions and unavailable/partial inventories have unreviewed dates.
After commit, the full original remains available in the unbounded recorded-date
view, but a dated view withholds the whole document/excerpts using the existing
partial-source rules. Extracted dates cannot authorize disclosure of omitted rows.

### Explicit review of flagged rows

`POST /api/history/commit` adds optional `reviewed_omissions: ReviewedFact[]`
(maximum 400). `reviewed_facts` may be empty only when omissions are selected.
The initial import saves both selections atomically. Omission IDs must come from
this stored draft's immutable inventory; duplicates, foreign IDs and client
source/provenance/timestamp fields are rejected. There is no automatic date,
facility, test-kind or lab-context inference. The editor begins with recorded
text and unknown date; the owner supplies corrections and confirms by saving.

`POST /api/history/omissions/commit` accepts `{draft_id,synthetic_confirmed:true,
reviewed_omissions:[ReviewedFact]}` for an already saved report. It appends new
facts with server-owned availability and `availability_basis:reviewed_row_addition`.
It preserves the original source, draft, extraction proposal, bytes, initial
commit receipt and earlier facts. Original inventory label/value/unit remain in
`source_proposal`; `row_inventory` retains candidate identity/support/reason.
The source quote/page/proposed region are copied only from the stored candidate.
Saved entries use the existing correction/version mechanism thereafter.

Identical batches return their original receipt with `duplicate:true,inserted:0`.
A changed batch containing a previously saved candidate returns 409; duplicates
are never silently overwritten or partially accepted. Original receipt fields
are retained, with additive `omission_ids`. Row inserts, audit and receipts share
one transaction. Initial upload review remains the route for unsaved sources.
Preview re-opening adds `omission_reviews:[{candidate_id,fact_id,available_at}]`
and nullable `saved_available_at` without another model call. UI saves preserve
an uncertain payload in tab memory for exact retry; reloading loses unsaved edits.

Both generic history and legacy measurement snapshots filter individual added
rows by availability. Existing captured views stay unchanged. Saving flagged
rows does not certify that the inventory is complete or remove dated-document
restrictions: unreadable, missed or undated source material can still exist.

Fresh demo stores include an authored open-label checkup. Re-uploading that
exact file returns its existing proposal with `already_committed:true` and
`extraction_mode:"authored_seed"`, even if Meta reading was requested. No model
request or owner review is implied; the warning identifies authored demo data.
Existing stores are not reseeded. All uploaded additions still require review.
Fresh stores also include seven authored archive checkups (56 fields across
12 test labels). Their recorded dates span 2010–2025; their explicitly authored
archive availability is 2026-11-02T12:00:00Z. Ordinary reviewed uploads always use
actual server commit availability. The supplied archive files never alter an
existing store merely because the application restarts.

## Longitudinal evidence series

`GET /api/history/series?snapshot_id=<capture>&fact_id=<measurement>&offset=0&limit=50`
returns the selected test across a captured history. `snapshot_id` is the existing
32-character lower-case hexadecimal history capture; `fact_id` is a visible
measurement (1–160 characters). Offset is 0–100000; limit is 1–50. Unknown or
repeated parameters are rejected with 422. Missing/out-of-scope anchors return
422; expired captures, including tokens from a previous process, return 409.

The response format is `modus-longitudinal-series-v1`: `scope`, `policy_version`,
`anchor_id`, `label`, chronological `observations` with date precision,
`plot_points`, `observation_notes`, `edges`, `history_evidence`, `page`, `counts`
and `limitations`. Dates, units, excerpts and revision identities remain literal.
Matching uses existing exact test aliases, never fuzzy assay-name merging.

Plot only returned points, separated by their exact units. A point contains
`fact_id`, a full `date`, finite `value` and `unit`; values that would lose
recorded precision remain in the evidence list. Connect only edges whose
`connectable` is true. Edges bind adjacent dated observations on this page and
return comparison status, exact-string difference (later minus earlier),
reason codes and notes. Neither pagination nor the chart may invent a connection
across pages or a missing observation.

`history_evidence` includes the page, its anchor and complete related conflict
companions. It is limited to 120 facts and the whole response to 2 MB; overflow
returns 422 with a smaller-page instruction instead of silently truncating.
An offset beyond the last row returns an empty observation/plot/edge page with
anchor evidence. Counts describe the whole matching series in the capture.

Existing captures retain their reviewed versions after a correction or late
upload. Obtain a new history capture for current values; after restart obtain
a new capture before requesting the series. This operation is read-only and
uses no model calls or unit conversion. Source download and correction continue
through the existing scoped endpoints.

## Reviewed two-report export — 2 November 2026 (T28)

Comparison policy `record-comparison-2026-11-03.1` compares narrative rows only
as literal recorded wording. These rows have no numerical difference and no
missing lab-unit/specimen/method warnings. Scope, date, ties and facility notes
remain visible. Measurement comparisons retain all existing lab-context checks.

`POST /api/briefs/report-preview` accepts `{snapshot_id,selected_source_id,
comparison_source_id,title?,owner_note?}`. It compiles the two-report summary and
all its visible facts through the existing brief builder, including related
conflict records from other files. Two reports must fit the 120-record summary
limit; the brief including conflict companions must also fit 120 records and
2 MB. Nothing is silently truncated. The existing manual 80-selection brief
request remains unchanged.

The response is `modus-record-brief-v1` with an additive `comparison` object:
the exact summary metadata, rows, claims, policy, counts and limitations, without
duplicating `history_evidence`. The preview digest binds this comparison,
included evidence, both time bounds, title and owner note.

`POST /api/briefs/report-export` takes the same selection plus `preview_id`,
literal `reviewed:true` and `format:"html"|"json"`. A changed selection/content,
expired capture or record-store revision returns 409 and requires a fresh
capture/review. A fresh historical capture remains usable after corrections;
it still displays the original historical values. Extra client claims, scope
overrides and nonliteral confirmation are rejected with 422.

HTML has internal citations from each comparison to its recorded evidence and
source list, with escaped original passages and a restrictive CSP. JSON retains
the structured claims/proofs. Neither route calls a model, changes records,
embeds original files or makes clinical interpretations. Sources and excerpts
hidden by date scope remain hidden in both formats. Downloads use `no-store`.

## Separate date evidence — 2 November 2026 (T26)

Meta extraction proposals may include nullable `date_evidence:{value,source_quote,page,bbox}`.
`value` must exactly equal the proposed `occurred_on`. The date passage stays separate
from the result's `source_quote`; both use original 1-based pages from the supplied
page group. Malformed geometry, forged check fields, inconsistent dates and pages
outside that group reject the extraction. The model is instructed to distinguish
collection/measurement dates from issue/print/birth dates and leave ambiguous linkage unknown.

The server adds `check:{status,issues}` and `relation:"requires_review"` to the
date evidence. Exact text matching only verifies the value and passage on that
page; it never proves the date belongs to a particular row. OCR/images remain
without independent text support. `local_support.status` may now be
`review_required`, with a specific date-link review reason. Same-model verification
cannot remove this requirement. The existing explicit reviewed-fact transaction
is unchanged; there is no extra confirmation checkbox.

`date_evidence` is server-owned provenance. Commit and correction request schemas
still reject it. Saved facts, Ask evidence, revisions, comparison proofs and Brief
JSON retain it; HTML export and source inspectors show the separate passage. A
date correction preserves the original date proposal. Any view withholding the
source excerpt also withholds `date_evidence`, including revision views. Existing
records without it remain readable and are not rewritten or silently re-extracted.

## Conversation continuations — 2 November 2026

`POST /api/history/chat` adds optional `continuation_token` (strict string, 1–100 characters). A supported answer may return `continuation:{token,subject,before_date,expires_in_seconds,suggested_question,supported_questions}`. `before_date` is null unless the answer identifies one fully dated result group. `supported_questions` lists the supported follow-ups for that answer; it does not grant new tool permissions.

“What about the one before that?” retains the original metric, numerical condition, exact unit and date restrictions, adding a strict earlier-date boundary. It returns the previous matching dated group, not the previous overall value or an arbitrary record within a day. Same-day ties, conflicts and incomplete-date limitations remain visible. “Show matching history” (or “Show its history”) retains the same predicate and original bounds while removing the navigation-only cutoff. A source follow-up, “Where did this value come from?”, requires exactly one unambiguous selected fact; otherwise it clarifies instead of choosing between tied or conflicting evidence. A source answer retains the original navigation context. These responses add `followup.operation: previous|source|history`.

Context is opaque, random, app-local memory: at most 256 entries, 30-minute TTL, lost on restart. It is bound to exact occurrence/availability scope and cannot change record kinds, quoted/source qualifiers or the captured history. It is not authentication or durable personal memory. Missing, expired, changed-scope or modified follow-ups return a fixed `history_followup` clarification without a model/read call. New full questions are independent. Continuations execute the existing typed read in deterministic mode even if the initial answer used Meta; execution labels reflect that.

An explicit correction action can reopen current history and rerun the original full question. It creates a new availability view and fresh continuation; it does not mutate the earlier answer or silently move an old token to a newer view. Following a previous-record answer, this action reruns the original subject question, not the prior ordinal position.

## T9 natural whole-history retrieval — 30 October

`POST /api/history/chat` accepts bounded conversational openings and latest-by-kind questions across eight kinds. `latest_history_match` retains `{query,kind?,limit?:1..8}`: a grammar-only query requires an explicitly owner-requested kind; otherwise named/literal constraints remain mandatory. Quoted/source restrictions stay binding. Numerical/date conditions use the typed query contract below; they are not silently discarded by the legacy matcher. Ordinary offline answers explicitly include `provider_requests_made:0`.

`search_history_evidence` and recognized-topic paged searches add influenza-vaccine, MRI, CT, X-ray and ECG topics matched on eligible saved labels/kinds. Retrieval method is `literal_medical_aliases_and_record_topics_v3`; additive mapping metadata includes `concept_id:"topic:<id>"`, `match_scope:"saved_label_and_kind"`, `record_kinds`, `requested_terms`, `matched_labels`, `catalog_version` and the existing static reference fields. Measurement aliases retain their prior exact-label contracts. A narrative mention alone cannot satisfy a new topic. Source values such as declined/planned remain verbatim; existence is not inferred. Links explain names, not personal findings. No new endpoint, database mutation or model permission is introduced.

## Medical terminology retrieval — 30 October 2026

Whole-history search uses `literal_and_medical_aliases_v2`, with the code-owned catalog `record-terms-2026-10-30.1`. It covers 24 local concepts and selected English/Korean aliases; no LOINC/SNOMED code, method equivalence, unit conversion or clinical interpretation is assigned. Exact recognized measurement labels can match through aliases. Other fact kinds remain literal. Quoted terms and `source:"title"` remain literal; year/date/kind and unknown-word qualifiers are not dropped. Unknown labels remain searchable.

`search_history_evidence` and `latest_history_match` return additive `retrieval` metadata: `method`, `catalog_version`, `status` and `mappings`. Each mapping has `concept_id`, `medical_name`, `display_name`, `requested_terms`, `matched_labels`, `catalog_version`, `mapping_review`, and a static `reference` (`publisher`, `title`, `url`, `checked_on`). These are authored terminology mappings, not clinical conclusions or confidence scores. References explain naming; only original record evidence supports a personal finding. The model must retain the owner's original query and cannot generate synonyms or reference URLs.

`POST /api/history/chat` exposes `terminology` only from selected tool findings. Ambiguous blood-sugar/cholesterol/kidney-test/liver-test terms instead return zero claims/read calls/provider calls and `clarification.kind: "medical_term"`, with `question` and `{label,message}` choices. Each choice preserves the request's other constraints. Selecting a choice is a new request under the same captured temporal bounds. Neither choices nor reference links imply a record exists.

`GET /api/history/page` also returns optional `retrieval` metadata for search. Recognized concepts use the same matcher before paging; fields retain their original names and are not merged. A query requiring clarification has zero matching rows and `retrieval.status: "clarify"` with `retrieval.clarification`. Unrecognized queries keep existing substring behavior. Literal/unknown modifiers never acquire clinical semantics. Complete captured counts remain separate from query/page counts.

Reference links are fixed server-owned HTTPS addresses on NIDDK/MedlinePlus, contain no owner data and are not fetched automatically. UI links suppress referrers and reject unexpected origins/credentials/query strings. Source buttons/downloads remain separate and preserve existing availability/partial-document restrictions. No new write tool, external-reference API or medical-advice route is added. See [scope and offline verification](VERIFICATION.md).

## Paginated whole history — 30 October 2026

`GET /api/history/page` is the interactive browsing API. The legacy `/api/history/view` and comparison response remain complete for compatibility and explicit exports. Ask still searches its complete captured history independently of the visible page.

First request supplies optional `as_of` (inclusive recorded date) and `known_at` (timezone-aware availability cutoff), with the same semantics as `/history/view`. Omitted `as_of` includes partial/unknown dates. Continue with the returned opaque `page.snapshot_id`; both temporal bounds then stay fixed. If explicit bounds accompany a token they must match its capture or the response is `422`. Filters may change within the same capture; restart offset at zero when changing filters.

Parameters:

| Name | Values / limits | Meaning |
| --- | --- | --- |
| `section` | `facts` (default), `sources`, `fields` | Which collection is paginated |
| `offset`, `limit` | 0–100000; 1–50 (default 50) | Replace the visible page; do not accumulate every page in the DOM |
| `kind`, `label`, `facility`, `source_id` | Exact filters; label/facility ≤200 characters, source ID ≤160 | Intersect filters over the full capture |
| `query` | Case-insensitive literal substring, ≤2000 characters | Match label, value, unit, facility, occurrence text or source title; field-catalog search additionally matches the label |
| `order` | `newest` (default), `oldest` | Fact chronology; source catalog stays newest-first and field catalog alphabetical |
| `through` | Inclusive recorded date | Exact-date facts on/before the bound; excludes partial/unknown dates |
| `conflict_id`, `conflicts_only` | Group ID; boolean | Reach conflict companions outside the current page |

Response retains `scope`, full-capture `counts` and `profile`. `facts` plus `undated_facts` contain only the selected fact page; `sources` contains the page's source metadata (or the selected source page). `fields` contains `{kind,label,count}` when requesting that section. Source summaries add `fact_count`, `first_date`, `latest_date`, `has_undated`, `display_label`. Date extrema use exact recorded dates only; flags preserve partial-date/unknown status. `conflicts` contains complete group metadata for selected facts and may reference companion IDs outside the page.

`page` contains `snapshot_id`, `section`, `offset`, `limit`, `returned`, `total` (filtered collection count), `matched_sources`, and nullable `next_offset`/`previous_offset`. `facets` contains full-capture kinds, first 200 facility names plus `facilities_truncated`, and exact `date_bounds`. A facility outside those first 200 remains queryable by its full name. Global counts are not page counts.

Snapshots are process-local and immutable, with a 600-second lifetime, at most four captures and an approximate 48 MiB encoded-record budget (not a resident-memory guarantee). Unknown/expired/evicted tokens return `410` with an explicit refresh message. Reconstruct from the displayed bounds when reopening a historical view; do not silently replace it with latest history. A single capture exceeding the budget returns `422` asking for an earlier date cutoff. Initial projection/filtering is still whole-capture work; this is not SQL keyset pagination.

History writes increment a transactional generation counter; new lookups see committed changes, while existing tokens retain their captured versions. Audit writes do not invalidate history. Original downloads continue to require the captured temporal bounds and existing partial-document restrictions. The model gains no write tool. See [verification and limits](VERIFICATION.md).

## Correction recovery and contention — 30 October 2026

Amendment requests/receipts retain their schema and idempotency. The frontend keeps the exact reviewed pending request in tab memory across evidence-dialog unmounts and workspace navigation; checking an uncertain result resends that identical request. It never automatically retries or persists medical text to browser storage. Reload/crash recovery is not provided. Read-only revision lists remain scope-bound; resuming a latest-version edit from another historical scope requires explicit owner action.

SQLite BUSY/LOCKED errors return HTTP `503`, `Retry-After: 1`, and `{"detail":"Your records are busy. Please try again shortly."}`. A correction client must retain the identical pending body on this response, as it does for other uncertain outcomes. Definitive non-timeout/non-rate-limit 4xx rejections invalidate the preview and require review again. History snapshots still capture clock/rows in one transaction; decoding/projection and offline Ask work run outside database locks/event-loop work respectively. See the [verification report](VERIFICATION.md).

Implementation contract for the independent entry. All dates/times are strings; instants require a timezone. JSON requests forbid extra fields. No broad assessment, medication, genetics or reference routes exist.

The product's only remote provider is Meta. Server configuration prefers `MODUS_META_KEY`, falling back to `MODEL_API_KEY` only when the preferred variable is empty. `/api/health` exposes only whether a Meta credential is configured, never its value. Evaluation-only provider credentials do not activate the product or provide a fallback. Ordinary pytest, offline check/build subprocesses and CI clear model credentials and disable dotenv loading; explicitly authorized live evaluation is separate.

The current schema extractor and bounded entry tool/claim selector explicitly request `reasoning_effort:"minimal"`. Extraction keeps a 4,000-token completion cap per pass; tool selection keeps the 1,600-token policy cap per request. This is the 29 October candidate configuration after a capped live extraction ended with `finish_reason:length`; it is not evidence of improved quality or a reason to discard that failure. There is no automatic retry, cap expansion or model substitution. The preserved legacy extraction comparator retains its original request settings.

`ScopeRequest = {as_of: YYYY-MM-DD, known_at?: timestamp|null, compare_from?: timestamp|null}`. Null/omitted known_at captures current server time. A non-null compare_from requests a comparison from that availability bound to known_at, keeping as_of fixed. Both views derive from one frozen capture. Future instants are capped at that capture; reversed resolved comparison bounds are rejected.

`Scope = {as_of, known_at, captured_at, scope_id}`. The UI uses resolved bounds for subsequent questions, originals and exports. `scope_id` identifies the scoped records and algorithm bundle; it is not an authorization token.

`Observation = {id, metric, value, unit, date, source_id, source_span, source_span_withheld, page, reviewed_fields, reported_at, reported_at_raw, available_at, availability_basis, fhir_provenance?}`. Metric is hba1c, egfr or ldl. Unknown optional fields are null, except absent structured source provenance is omitted for compatibility. The shared type can retain bounded original FHIR metadata and a catalog resolution, but this entry does not accept FHIR uploads. If the source contains later measurements, the historical projection withholds its excerpt and structured source metadata as well as its full text/original; full scope restores them. No unit conversion or reference-range assessment.

`Source = {id,title,provider,date,type,content,synthetic,original_available,available_at,availability_basis,ingested_at?,sha256?,extraction_mode?}`. Content is untrusted source text. Historical projections withhold full source content/original if that document also contains later observations.

`Conflict = {id,metric,date,reason,observations: Observation[]}`. Differing same-day values/units are preserved. Their specimen equivalence is unknown; no source is automatically declared wrong.

`View = {scope,observations: Observation[],sources: Source[],counts:{measurements,documents,disagreements},conflicts: Conflict[]}`.

`Comparison = {before:View,after:View,captured_at,added:Observation[],unchanged_count,new_conflicts:Conflict[]}`.

Routes:

- `GET /api/health`: `{application:"modus-records",release,bundle_id,synthetic_only:true,provider:{mode,requested_mode,key_configured,model,live_verified:false},local_ocr:{available:false,mode:"disabled",reason}}`. Since 29 October, local OCR is retired from the contest entry; this route neither probes nor loads a local OCR model.
- `GET /api/records/view?as_of=...&known_at=...`: View. as_of required.
- `POST /api/records/compare`: `{as_of,before_known_at,after_known_at?:null}` → Comparison.
- `POST /api/imports/preview`: multipart file, synthetic_confirmed=true and use_meta=false by default → `{id,source,observations,warnings,extraction_mode,already_committed}`. CSV/text/text-PDF deterministic extraction remains available without a model. Explicitly opted-in PDF/PNG/JPEG extraction uses Meta for the schema-constrained proposal and separate source check. Local OCR is disabled during Meta document preparation even when a research OCR installation exists. A stale client sending `use_local_ocr=true` receives 422 before parsing or inference. There is no alternate-model fallback or automatic retry. Both paths require explicit review before commit. JSON/FHIR import is excluded from this first entry.
- `GET /api/drafts/{draft_id}/original`: original attachment for an uncommitted draft only.
- `POST /api/imports/commit`: `{draft_id,synthetic_confirmed:true,reviewed_observations:[{id,metric,value,unit,date}]}`. Nonempty explicit selection required. Returns `{draft_id,source_id,inserted,duplicate,available_at,observation_ids,bundle_id}`. A repeated commit returns the original identity/time and inserted=0. No unrestricted before/after attribution.
- `GET /api/records/{source_id}/original?as_of=...&known_at=...`: both resolved scope parameters required. Rejects unavailable or partially visible documents.
- `POST /api/agent/chat`: ScopeRequest plus `message`. Returns `{mode,answer,claims,trace,execution,telemetry?,scope,comparison?}`. Claims are exact typed-tool sentences, each `{id,text,evidence_ids,tool_name,status}`. Trace has name, arguments, result, status, duration_ms, executor. Model free text never becomes a finding.
- `GET /api/changes?known_at=...`: `{changes:[{id,created_at,kind,status,draft_id?,source_id?,available_at?,observation_ids?,scope?,comparison?,message?,answer?,mode?,error?,execution?,telemetry?}]}`. kind is import/question/extraction_failure; failures retain sanitized metadata. Comparison questions retain both original scopes. Nested metadata is allowlisted; no arbitrary stored JSON passthrough. Import change events are persisted in the same transaction as the records and idempotent receipt.

Provider call telemetry adds bounded optional `response_id`, `request_id`, `http_status`, `finish_reason` and sanitized `error_kind`, alongside model, status, latency and actual reported usage. Unknown fields stay unknown. Explicit refusal/interruption is a failed validation, even if the returned content is syntactically valid. The Changes projection retains only these permitted metadata fields; no raw headers, response bodies or exception text are exposed. These fields do not establish a successful live run by themselves.
- `POST /api/records/export`: ScopeRequest → attachment `{format:"modus-record-export-v1",synthetic:true,bundle_id,kind:"snapshot"|"comparison",data:View|Comparison}`. Required displayed as_of and non-null known_at; optional compare_from. No source original bytes in JSON export.

Errors use `{detail:string|validation errors}` and non-2xx status. Live failures do not fall back to local success. A stale view must disable source/question/export controls until refreshed. Close/reopen can retain reviews in the same tab; durable reload recovery is not claimed.

The multi-file frontend queue reuses the same single-file preview and reviewed commit contracts. Selecting a batch sends no request. Each explicit read/commit applies to one file; each saved file has its own receipt and availability timestamp. There is no atomic batch commit or automatic model invocation. An uncertain commit is retried with the identical draft ID and reviewed payload before another file can advance. Queue state remains in the open tab, not in a durable server queue. Supported extraction concepts and routes are unchanged.

Agent read tools accept an optional `metric: "hba1c"|"egfr"|"ldl"|null` for `record_inventory`, `record_conflicts` and `compare_record_snapshots`. Omitted/null means all supported measurements. Inventory also accepts bounded `offset` and `limit`. Comparison requires a server-bound `compare_from`; its filtered result narrows `added`, `unchanged_count` and `new_conflicts` while preserving the original `before`/`after` views and their scopes. Filtering never changes either time bound or the captured context. Metric-specific arrival claim IDs include the metric; the unfiltered `arrival-count` ID remains unchanged. The `/api/records/compare` and export routes continue to return complete scoped comparisons.

`search_record_evidence = {query: string(1..2000), limit?: integer(1..8)}` is a read-only agent tool, default limit 5. It returns `{scope, query, limit, method, ontology_version, constraints, hits, conflict_context, warnings, empty_reason, truncated, claims}`. Hits retain observation/source IDs, raw recorded fields, a permitted source excerpt, retrieval score and match context. It uses BM25 over eligible rows with bounded English/Korean ontology terms. Exact code/method qualifiers require qualified original coding. Source content is never an instruction. Explicit source/phrase filters exclude nonmatching companions from answer hits; those companions are retained in `conflict_context` (at most eight observations total), with bounded omission warnings. Conflict-only searches restrict to backend conflict membership. Empty results do not imply missing care. See [terminology and retrieval](TERMINOLOGY_RETRIEVAL.md).

Offline routing recognizes bounded record inventory, disagreement, availability-comparison and record-search expressions. It abstains on multiple concepts, combined independent tasks, ambiguous method constraints, unsupported requests or an arrival question without a bound comparison. Search may narrow matches by explicit dates/years or quoted phrases but cannot change either captured scope boundary. Relative/range date language is unsupported. Count/conflict/arrival tools do not silently discard source/date/method/unit qualifiers they cannot apply. All displayed claims/counts come from typed tools. This remains deterministic execution with no model call; the Meta loop may select the same read tool and exact returned claims.


## Reviewed commit payload

A preview observation is an evidence record, not a commit request. Project each included, explicitly reviewed row to `id`, `metric`, `value`, `unit` and `date`. The server rejects extra fields such as `source_span`, `available_at`, source IDs or model provenance; those stay server-owned. A 422 rejection leaves the draft available and creates no committed record. Do not resolve this error by dropping the server's strict field validation.

`synthetic_confirmed: true` is required independently on preview and commit, as defense at each endpoint. The service asks for one confirmation for the selected queue, then carries it through the explicit read/review/save actions; these are two endpoint checks, not two user prompts.

The answer text is now composed from the selected typed claims, without the prior generic success sentence. Negative conflict findings carry their measured/availability scope and count. The UI displays the answer's captured dates and offers an explicit **Use latest files** action. Historical queries never silently gain later records. Frozen evaluation prose contracts require an explicit compatible grader version; earlier development results are not scores for this revised output format.
# Whole-history extension (28 October 2026)

Preview includes `facts`, with server-owned IDs, original quotes/page/region and editable `kind`, `label`, `value`, `unit`, `occurred_on`, `facility`. Plain CSV columns describe arbitrary recorded names; unfamiliar text remains text. The existing observations projection remains for compatible clients. The active import UI reviews and commits `facts` through `/api/history/commit` for every draft.

T2 (29 October): reopening a stored legacy observation draft supplies an in-memory fact projection with the same IDs and original spans; it does not re-extract, invoke a model, or rewrite the stored proposal or original bytes. Review may change the recorded name beyond the three legacy metric IDs. Numeric spelling lost by an older float-based draft cannot be recovered; its original source remains intact. An empty proposal never falls back to observations. T3 permits an empty whole-report draft with a validated processing ledger to open for original inspection; it cannot be committed.

Trends reads `/api/history/view` with the displayed occurrence and availability bounds. Record-type and field selectors come from current source-backed facts of all eight kinds, including unknown measurement names. Labels and kinds stay distinct; plots separate exact units and retain same-date disagreements. Only finite scalar numeric values with complete dates can form points. Qualified values such as `<5`, paired values such as `100/65`, text, and partial/unknown dates remain readable, source-linked entries without invented points. Narrative records retain their wording. Every source inspector and download uses the same scope; a filtered-out file or value cannot reappear through Trends. The original three-metric observation/tool API remains a compatibility surface, not the active Trends or review schema.

The downloadable `whole-history.csv` is an authored example covering all eight kinds and six additional measurement names. This change establishes generic review, storage and browsing, not automatic understanding of every medical file. Local free-form text may remain unstructured; scans still require explicit Meta extraction. No live extraction quality claim is added by this offline verification.

`POST /api/history/commit` requires `{draft_id, synthetic_confirmed:true, reviewed_facts:[{id,kind,label,value,unit,occurred_on,facility}]}`. Unknown nullable fields must be null; original source, reviewer and availability cannot be supplied by the client. Return receipt includes inserted/duplicate, fact_ids, observation_ids, source_id and immutable available_at. Compatible old measurements are bridged atomically; no generic fact is counted twice. Changed retries reject; identical retries preserve the receipt. A previously committed legacy draft cannot be silently augmented with new facts.

`GET /api/history/view?as_of=YYYY-MM-DD&known_at=<offset-time>` captures one snapshot and returns facts, undated_facts, sources, conflicts, counts, profile and scope. Omit as_of for all recorded dates; availability still applies. Withheld values are null with `value_withheld:true`; quotes/regions are also withheld when a source falls outside the date scope. Original downloads use `GET /api/history/sources/{id}/original` with required known_at and optional as_of, matching that exact scope.

`POST /api/history/compare` takes `{as_of?: YYYY-MM-DD|null, before_known_at: aware timestamp, after_known_at?: aware timestamp|null}`. It returns `{format:"modus-history-comparison-v1",before,after,added,added_counts:{total,dated,undated},unchanged_count,new_conflicts,captured_at}` across all eight record kinds. Both safe history views use the same event cutoff, SQLite capture and clock; null after_known_at means that capture time. Availability accepts ISO timestamps with seconds, an explicit timezone and at most six fractional digits; numeric epochs and excess precision reject instead of silently changing a boundary. Accepted timestamps retain their full precision, future bounds clamp to capture, and reversed resolved bounds reject. Preserve the displayed pre-commit `scope.known_at` as the before bound; a commit receipt's availability time is already inclusive of that saved record.

Each side contains `scope,facts,undated_facts,sources,conflicts,counts`. Exact values, units, original permitted quotes and reviewed-field markers remain separate. Profile, DOB, age, reviewer identity and original proposals are excluded. Partial and unknown event dates remain in `undated_facts`; existing historical value/quote withholding still applies. `added` means newly available record IDs, not a new health event or a change in the person's condition. `new_conflicts` includes both newly detected measurement discrepancies and existing groups with newly added members; no winner is selected. Narrative kinds have no implemented conflict detector. Source inspection and original downloads must use the selected side's exact scope. This endpoint invokes no model and writes no records or activity. More than 2,000 facts per side or a 4 MB serialized response rejects with 422 instead of returning an incomplete comparison.

`GET /api/profile?known_at=...` returns a local profile revision. `PUT /api/profile` takes only `{date_of_birth: YYYY-MM-DD|null}` and stamps its revision server-side. Profile data is not added to provider extraction or question prompts. Age markers are computed only from exact dates.

Meta preview now uses text/image preparation and extract-then-verify. Every result is still a review proposal. Unknown/failed verification and uncalibrated model confidence never authorize a commit. Successful/partial runs expose sanitized per-call traces in `/api/changes`; duplicate uploads reopen existing reviews before any provider call.

29 October guard extension: prepared document text is screened for known instruction patterns before extraction. Guard metadata identifies its deterministic method, version, coverage and matched rule IDs; original source bytes and draft facts are preserved. Image pixels are not classified by this text screen. Ask requests and retrieved text are screened before model/tool reuse; a blocked request returns an explicit abstention with a timed guard trace and no model or record-tool execution. This is not Prompt Guard, Llama Guard or proof of complete injection detection. Source crops from SAM remain an unintegrated feasibility experiment.

Server Meta authentication prefers `MODUS_META_KEY`; `MODEL_API_KEY` remains a compatibility fallback. Claude and OpenAI keys/adapters are used only by the separate evaluation jury. They are not part of this API or its tool capabilities. Test and check subprocesses strip all four key variables and disable dotenv loading.

## Saved-record corrections

`GET /api/history/facts/{fact_id}/revisions?known_at=...&as_of=...` returns the original saved version followed by append-only corrections admitted by that availability cutoff. The optional exact event-date filter applies to each version; original text/value withholding still applies. Correction reasons are omitted from date-filtered history. Unknown/unavailable facts return 404. At most 1,000 versions are returned; larger histories reject explicitly. `local-owner` is a local review label, not authenticated identity.

`POST /api/history/amendments/preview` accepts exactly `{expected_revision_id, corrected: ReviewedFact, reason}`. `corrected.id` is the stable saved fact ID. It returns a content-bound `preview_id`, current saved record, proposed editable fields and exact before/after changes. Only kind, label, value, unit, occurrence date and facility are editable. Source file, quotation, page, original proposal, availability and actor are server-owned. No-op/unknown/invalid edits reject. Stale revisions return 409. Preview is read-only and invokes no model.

`POST /api/history/amendments/commit` takes the identical payload plus `{preview_id, reviewed:true}` (actual boolean). It validates the current revision inside a SQLite write transaction, then appends a revision and activity event atomically. Server time must strictly follow the preceding revision. The original source, document bytes, draft, original fact and original observation rows are unchanged. Retries of the identical correction return its original receipt, even after later amendments; changed retries or stale previews reject. The hash binds content; it is not authentication or proof a human read the preview.

Current facts retain their stable `id`, a `revision_id`, `previous_revision_id` when amended, and `first_available_at`. `available_at` is the admission time of the selected version. Both generic and legacy measurement tools select the revision available at their frozen cutoff. Incompatible legacy projections disappear only from current measurement views; the exact generic fact and earlier chart version remain available. Original source dates/availability never change.

History comparison now includes `updated:[{before,after}]` and `removed_from_scope:[fact]`; `unchanged_count` excludes corrected records. A corrected occurrence date can move a record outside the selected scope without deleting it. Briefs and Ask use the same versioned projection. Historical briefs remain valid for their original bounds. Correction reasons and reviewer identities do not enter model tools. The model has no amendment tool.

Source details offers latest-version editing, a required reason, before/after review and explicit save. Choosing to edit latest is separate from inspecting a historical version. Saving preserves the open historical view; **Open updated history** explicitly loads current records. An unconfirmed save retries the exact body. General retractions, erasure, authentication and production privacy remain unimplemented.

## Whole-history questions

### Exact last blood-pressure match (29 October)

`POST /api/history/chat` recognizes “When did I last have blood pressure of 100?” and returns `clarification:{kind:"blood_pressure_component",question,choices:[{label,message}]}` with no claims, tools or provider calls. The UI submits the chosen self-contained message with the same captured occurrence and availability bounds. There is no implicit conversation memory. Explicit systolic/top-number or diastolic/bottom-number wording routes to `last_recorded_blood_pressure({component:"systolic"|"diastolic",value:decimal_string})`. Extra filters, authority fields, inequalities and unsupported phrasing do not become an exact last-match query.

The read tool uses reviewed measurement facts, a bounded exact label allowlist and explicit `mmHg`, `mm Hg` or `mm[Hg]` units. Separate component values and `systolic/diastolic` pairs compare as decimals, never substrings. It ranks complete occurrence dates, never arrival times; excludes dates beyond the captured UTC date or selected occurrence cutoff; retains same-date ties and unlike readings, partial/unknown-date matches, unsupported formats/units and truncation caveats. No unit conversion, physiological range inference or elapsed-years estimate is performed. Corrections use the revision available in the captured view; the original quote and scoped original-file link stay unchanged. A missing match is never stated as “never happened.”

The model may only invoke the exact bound request and select typed claims. Selecting any BP finding requires the complete bounded answer and evidence claims, so it cannot discard a discrepancy or correction. Empty selection remains an abstention. Clarifications return `provider_requests_made:0` in both modes. Actual live requests are distinct from deterministic/mocked verification.

### Shared history contract

`POST /api/history/chat` takes `{message: string(1..2000), as_of?: YYYY-MM-DD|null, known_at?: aware timestamp|null, compare_from?: aware timestamp|null}`. Null occurrence cutoff means all recorded dates. The server captures one clock and SQLite transaction for both availability views, caps future availability at that capture and rejects reversed resolved bounds. Extra authority fields are rejected. This route reads reviewed facts of all eight kinds, including arbitrary measurement names; it does not change the legacy three-metric `/api/agent/chat` contract. Trends independently reads the same whole-history snapshot API.

Response is `{mode,answer,claims,trace,execution,telemetry?,scope,history_evidence,history_comparison?}`. `history_evidence` is a bounded, selected-answer projection with the same scope, facts/undated_facts/sources/conflicts/counts, `projection:"selected_answer_evidence"` and `truncated`. It includes selected facts and conflict companions, at most 64 facts. It excludes profile, DOB, age, reviewer identity and unreviewed proposals. It is not a complete history inventory. `history_comparison` contains only the server-captured `before` and `after` scopes. Evidence originals require the same occurrence/availability bounds as the answer. Whole-history questions are recorded in Changes using the existing sanitized question-event projection.

Read tools: `history_inventory({kind?,label?,offset?:0..100000,limit?:1..8})`, `search_history_evidence({query,kind?,limit?:1..8})`, `history_conflicts({kind?,label?})` and `compare_history_snapshots({kind?,label?})`. Kind uses the eight-value fact enum; label is exact case-insensitive text. Inventory/search default to five records. Search requires literal terms/quoted phrases, optionally a recorded year/month/day or `source:"title"`; no medical synonym expansion or semantic inference. A missing match does not establish missing care. Counts distinguish all matches from the displayed page. Large values are omitted explicitly from the model payload; the source inspector retains their full permitted text. Discrepancy detection remains same-label/day measurement comparison, not contradictions in clinical narratives.

Simple questions retain a single code-bound read and exact claim selection. T3 adds the bounded investigation described below for eligible compound or latest-record questions. Neither path can alter scope, profile, URLs or records. Mandatory tool limitation claims are retained even if the model omits them. Unsupported/mixed advice requests return no claims or tools before provider access (`mode:"request_guard"`, `provider_requests_made:0` in live configuration). Offline supported answers use `mode:"offline"`, never a model label. Live transport/validation failure returns 502 and records sanitized telemetry, with no offline fallback. Arbitrary model prose is never rendered as an answer.

Home, Records and Documents send their displayed history bounds to this route. Example chips only fill the question. Only explicit Submit invokes it. Comparison requires an explicitly chosen date. Changing bounds cancels/drops stale answers and closes evidence; all-date and historical views stay distinct. This extends record access; it does not assert current medication use, diagnose, interpret imaging/genetics or recommend care.

## T3 whole-report reading and investigation (29 October)

Explicit Meta extraction groups up to 12 prepared PDF pages into consecutive groups of three. Each group receives schema-constrained extraction, a source-check pass when fields exist, and a source-only row inventory. The hard ceiling is twelve provider requests, 100 extracted fields per group and 200 extracted fields per report. Inventory is separately bounded to 100 rows per group. Existing 8 MB input, text/image preparation and per-pass token limits remain. No automatic retry occurs. Global page numbers, original bytes, original quotations and numeric spelling are preserved. Failure of any extraction group rejects the entire proposal; successful earlier groups are not silently accepted. A failed verification pass leaves its fields unconfirmed for owner review; a failed inventory keeps an explicit unavailable completeness check.

Successful previews add `extraction_review.coverage:{version:"whole-report-v1",status:"completed",completeness:"not_established",page_count,processed_pages,pages_per_group:3,max_provider_calls:8,request_count,pages}`. Each page has `{page,status:"not_run"|"processed"|"no_fields"|"failed",field_count,verification_status:"not_run"|"completed"|"unavailable",readability:"text_available"|"image_only"|"unreadable",text_available,vision_supplied}`. This records processing, not extraction recall or medical completeness. A report with no fields retains its original and page ledger in review but cannot save an empty history transaction.

When extraction fails after a ledger exists, the 422/502 response uses `detail:{message,report_coverage}` instead of a detail string. Other errors retain string details. The frontend handles both. The same allowlisted ledger appears in Changes telemetry. Provider error bodies, raw text and arbitrary ledger fields are excluded. Field concerns appear next to the editable values; the full checks list is collapsed by default, and flagged original excerpts are open.

Eligible compound questions may use inventory, literal search, conflicts, an already-bound availability comparison, or `latest_history_match({query,kind?,limit?:1..8})`. Muse has at most three read calls and four model responses. The runtime validates every call against the owner's explicit record types, names, quantities and source qualifiers. It requires coverage of every requested subject/task combination, rejects duplicate calls/JSON keys and invented filters, and accepts only exact tool-generated claim IDs. Requests that exceed this bounded scope clarify rather than return an incomplete answer. Guard screening runs before model reuse of untrusted tool output. No write, clinical interpretation or free-form answer capability is added.

`latest_history_match` identifies the latest fully dated literal record match; same-date ties, partial/unknown dates, future-date exclusions and truncation remain explicit. Generic numeric latest queries clarify until a typed comparator exists; the separately implemented exact blood-pressure route is unchanged. This is not an arbitrary numeric query engine or semantic medical search.

Responses may add `investigation:{method:"bounded_record_investigation_v1"|"deterministic_record_investigation_v1",status,read_calls,max_read_calls:3,max_model_responses}` and `clarification:{kind:"record_investigation",reason,question,choices:[]}`. Clear offline combinations use the same typed reads with zero model responses. Evidence is selected through the existing scoped history projection and original-file links. Injected-transport tests identify themselves as tests; they establish contract behavior, not live Muse quality. No live call or evaluation-set execution was performed for T3.

## Reviewed record brief

`POST /api/briefs/preview` accepts `{as_of?: YYYY-MM-DD|null, known_at: aware timestamp, selected_fact_ids: string[1..80], title?: string(1..100), owner_note?: string(0..1200)}`. Defaults are `Record brief` and an empty owner note. Extra fields, duplicates, unknown IDs and selected facts unavailable/withheld in that scope reject. No model is invoked. The server resolves exact reviewed facts and includes every visible member of a selected measurement discrepancy; the expanded selection must remain within 120 records and the 2 MB canonical-content limit. Oversized or incomplete discrepancy evidence rejects instead of truncating.

The response is `{format:"modus-record-brief-v1",bundle_id,preview_id,title,owner_note,scope,generated_at,reviewed:false,entries,sources,conflicts,warnings,counts,history_evidence}`. Entries carry the scoped recorded fields plus `citation` (R1...), `source_citation` (S1...), `selected_by_owner` and `added_for_conflict`. Counts distinguish `selected`, `conflict_companions`, `total` and `sources`. The evidence view excludes profile/DOB/age/reviewer/proposals and contains the exact selected/companion records only. Exact dated entries are chronological; partial and unknown dates remain separate. The owner note is explicit free text, never presented as a source-recorded fact or model finding.

`POST /api/briefs/export` takes the same fields plus `preview_id`, `reviewed:true` (actual boolean) and `format:"html"|"json"` (default html). It recomputes the brief and compares the canonical SHA-256 binding of title/note, resolved time bounds, selected entries/quotes, sources, conflicts, warnings and algorithm bundle. A changed brief returns 409 and requires a new preview/review. Capture timestamps and volatile scope IDs are excluded so a later download of unchanged, identically scoped content succeeds. This digest is content integrity, not authentication or proof of clinical accuracy. Export adds `reviewed:true` and `reviewed_at`; neither preview nor export writes records or persists a brief.

HTML is a standalone readable document with print styles, escaped source text, internal record/source citation anchors and excerpts. It contains no scripts, remote assets, active external links or original files. Browser Print may save it as PDF; the server does not generate a PDF. JSON retains the structured brief. Downloads use attachment disposition, no-store, nosniff and a restrictive CSP. Both formats retain selected-history limits, historical-prescription attribution and unresolved differences. A brief stays local until the owner separately chooses to share it. No sending or third-party sharing endpoint is added.

# Lab context and checkup comparison — 2 November 2026

Generic reviewed facts and proposed extraction fields add nullable verbatim strings: `reference_range` (maximum 400 characters), `specimen` and `test_method` (200 each). Null means unknown; empty strings are rejected. CSV accepts these exact column names. Model proposals must support context in the same quoted passage. No reference ranges are inferred from external thresholds.

Review/commit and amendment clients must include context keys when the draft/current fact has context; omission is rejected to prevent silent loss. Explicit null is a reviewed removal. Corrections remain append-only and preserve original bytes, source quote and `source_proposal`. Legacy missing optional fields project as null; legacy receipt hashes exclude null optional context. When a temporal projection withholds a fact's value, these fields are also null.

`GET /api/history/page` accepts optional `compare_fact_id` (maximum 160 characters). The fact must be a visible, non-withheld measurement within the captured scope. Response adds `checkup_comparison`: `current`, `previous` (up to 50 facts), `previous_count`, `difference` (decimal string or null), `unit`, `notes`, `sources`, and `basis`. Existing snapshot, event-date and availability rules apply. Comparison uses the full captured view before paging, so changing page size does not change its answer.

Tests match by an existing exact medical alias or normalized recorded label. Previous means the latest full date strictly before the selected date. Same-day prior ties remain separate; incomplete dates and multiple results on the selected date are disclosed. Numeric difference is selected minus previous, and is withheld for ties, date uncertainty, qualified/non-numeric values, absent/different units/specimens/methods or other comparison notes. Range/facility differences produce notes. This is recorded-value arithmetic, not a clinical comparability assessment; no conversion, diagnosis or range classification occurs. Sources retain normal scoped-original access controls.

# Two-report summary — 2 November 2026

`POST /api/history/report-summary` is a deterministic, read-only operation. Body: `snapshot_id` (32-character token returned by `/history/page`), `selected_source_id`, `comparison_source_id`. Exactly two distinct visible sources are required. Extra fields, model-written facts, free-form claims and caller-supplied scope overrides are rejected. An expired capture returns 409; invalid selections or resource limits return 422. The source picker continues to use `/history/page?section=sources&snapshot_id=...&limit=12&offset=...` (expired page token: 410).

The response format is `modus-report-summary-v1`: original snapshot/scope, policy version, both source identities, grouped rows, checked claims, complete eligible evidence and counts/limitations. Each row retains every matching fact ID on both sides. Fixed exact-name aliases can group measurements; qualifiers and record kinds remain binding. Multiple matching results in either report are not arbitrarily paired. One-sided entries do not establish absent testing or care.

Numerical differences require unique, fully dated, chronologically ordered measurements, supported test-name matching, exact units/specimen/method, matching printed range/facility context, unqualified finite numbers and no same-date ties or unknown-date ordering ambiguity in the captured history. Generic glucose collection context remains unresolved. No conversion or clinical-equivalence claim is made. Reason codes and text explain every withheld difference. The existing per-test `checkup_comparison` now adds `status`, `policy_version` and `reason_codes` using the same policy.

Claims bind exact captured facts, revisions, source IDs/excerpts/page/geometry, saved values/context and scope. The verifier regenerates record statements and independently recalculates proposed differences from the captured view. It reports `SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE` or `OUT_OF_SCOPE`. A source ID or content hash alone cannot establish support. Missing/withheld excerpts suppress generated claims and differences. Reviewed corrections may differ from the original excerpt; support means consistency with the reviewed version, not a claim that the original printed the corrected value or that the medical finding is true.

Limits: 120 records total across both source files before filtering and 2 MB serialized response. Limits reject the complete request rather than silently truncate. UI renders ten groups at a time, hides stale results on selection changes, rejects mismatched response identities, and invalidates the displayed summary after a confirmed correction. Existing captured views remain reproducible; opening updated history creates the revised comparison. No model call, export, save, appointment action or clinical interpretation is introduced by this endpoint.

# Typed Ask queries — 3 November 2026

`POST /api/history/chat` keeps its existing request schema. Clients cannot submit
plans, provider routes, SQL, code, subject IDs or scope overrides. The server's
captured occurrence/availability view remains the authority.

New numerical/history responses add:

- `query_plan`: strict `record-query-plan-v1` operation, resolved measurement
  token, optional `{operator: lt|lte|gt|gte|eq, value: decimal-string, unit}`,
  `selection: latest|earliest|count|all`, optional inclusive start/end dates or
  exclusive before/after dates, and `evidence_required: true`.
- `query_result`: `answered`, `no_match`, `insufficient_evidence`,
  `clarification`, `not_understood`, `unsupported` or `planner_unavailable`;
  selected observations, match count, exclusions, material limitations, and
  checked first-to-last comparison when supported. A no-match result concerns
  available reviewed records; it does not establish that an event never happened.
- `planner`: version, deterministic/validated/failure status, actual model-call
  count and `answer_composition: deterministic_verified_records`.

Supported operations include threshold searches, first/latest matching results,
counts, ordered history, first/last differences, explicit two-file comparison and
source inspection. The existing latest/follow-up and literal/alias search paths
retain their contracts. Full dates or `in YYYY` narrow occurrence scope; they
cannot widen the captured availability. Relative/ambiguous dates, multiple
selectors, unknown source/method filters and unresolved tests clarify instead of
silently dropping conditions. Generic glucose and fasting glucose are not merged.

Thresholds use exact Decimal values and literal units. An omitted unit can be
resolved only when the eligible test records share one explicit unit. There is
no unit conversion or clinical threshold knowledge. Qualified/text values,
unknown dates and conflicts remain evidence and may prevent definitive ordering.
Complete selected evidence plus conflict companions is bounded to 48 records and
200 KB; exceeding the bound asks for narrower dates, without a partial count.

Recorded facts and differences pass the existing exact proof verifier.
Comparators and aggregate selections are calculated by the read-only executor,
never generated by a model. Ask now retains printed lab ranges, specimen and
method; these were previously lost from its safe projection. Original bytes,
amendments and source-download scope rules are unchanged.

If explicitly running in Meta mode, one optional Muse `plan_history_query` call
can confirm a safely anchored conversational paraphrase or abstain. It receives
the question and code-owned plan, not original documents or recorded values.
Every returned field must equal the validated anchors before execution; arbitrary
model prose is ignored. Timeouts, refusals, malformed or changed plans return a
fixed failure/clarification response and execute no record tools. The new model
path is verified with injected transports only in this sprint, not live calls.

