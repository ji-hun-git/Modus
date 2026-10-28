# Modus Records API v1

Implementation contract for the independent entry. All dates/times are strings; instants require a timezone. JSON requests forbid extra fields. No broad assessment, medication, genetics or reference routes exist.

`ScopeRequest = {as_of: YYYY-MM-DD, known_at?: timestamp|null, compare_from?: timestamp|null}`. Null/omitted known_at captures current server time. A non-null compare_from requests a comparison from that availability bound to known_at, keeping as_of fixed. Both views derive from one frozen capture. Future instants are capped at that capture; reversed resolved comparison bounds are rejected.

`Scope = {as_of, known_at, captured_at, scope_id}`. The UI uses resolved bounds for subsequent questions, originals and exports. `scope_id` identifies the scoped records and algorithm bundle; it is not an authorization token.

`Observation = {id, metric, value, unit, date, source_id, source_span, source_span_withheld, page, reviewed_fields, reported_at, reported_at_raw, available_at, availability_basis, fhir_provenance?}`. Metric is hba1c, egfr or ldl. Unknown optional fields are null, except absent structured source provenance is omitted for compatibility. The shared type can retain bounded original FHIR metadata and a catalog resolution, but this entry does not accept FHIR uploads. If the source contains later measurements, the historical projection withholds its excerpt and structured source metadata as well as its full text/original; full scope restores them. No unit conversion or reference-range assessment.

`Source = {id,title,provider,date,type,content,synthetic,original_available,available_at,availability_basis,ingested_at?,sha256?,extraction_mode?}`. Content is untrusted source text. Historical projections withhold full source content/original if that document also contains later observations.

`Conflict = {id,metric,date,reason,observations: Observation[]}`. Differing same-day values/units are preserved. Their specimen equivalence is unknown; no source is automatically declared wrong.

`View = {scope,observations: Observation[],sources: Source[],counts:{measurements,documents,disagreements},conflicts: Conflict[]}`.

`Comparison = {before:View,after:View,captured_at,added:Observation[],unchanged_count,new_conflicts:Conflict[]}`.

Routes:

- `GET /api/health`: `{application:"modus-records",release,bundle_id,synthetic_only:true,provider:{mode,requested_mode,key_configured,model,live_verified:false},local_ocr:{available,mode,model?,revision?,reason?}}`. Local OCR availability is an installation probe, not proof of a successful inference; checkpoint integrity is verified before each worker execution.
- `GET /api/records/view?as_of=...&known_at=...`: View. as_of required.
- `POST /api/records/compare`: `{as_of,before_known_at,after_known_at?:null}` → Comparison.
- `POST /api/imports/preview`: multipart file, synthetic_confirmed=true, use_meta=false and use_local_ocr=false by default → `{id,source,observations,warnings,extraction_mode,already_committed}`. CSV/text/text-PDF deterministic extraction; opted-in PDF/PNG/JPEG uses either Meta or the separately installed local TeleOCR model. Selecting both is rejected. Local OCR runs in a fixed worker without provider credentials, accepts bounded complete page transcription only, and still requires explicit review before commit. Mode `local-teleocr` is a real local model result, never labelled deterministic text or Meta. There is no alternate-provider fallback. Local OCR permits one lower-resolution retry only for verified truncation/layout-format failure; both attempts and verified usage are retained. Completed empty extraction and missing fields never trigger this retry. JSON/FHIR import is excluded from this first entry.
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

Preview may now include `facts`, with server-owned IDs, original quotes/page/region and editable `kind`, `label`, `value`, `unit`, `occurred_on`, `facility`. Plain CSV columns describe arbitrary recorded names; unfamiliar text remains text. The existing observations projection remains for compatible clients. New clients use one commit route per draft.

`POST /api/history/commit` requires `{draft_id, synthetic_confirmed:true, reviewed_facts:[{id,kind,label,value,unit,occurred_on,facility}]}`. Unknown nullable fields must be null; original source, reviewer and availability cannot be supplied by the client. Return receipt includes inserted/duplicate, fact_ids, observation_ids, source_id and immutable available_at. Compatible old measurements are bridged atomically; no generic fact is counted twice. Changed retries reject; identical retries preserve the receipt. A previously committed legacy draft cannot be silently augmented with new facts.

`GET /api/history/view?as_of=YYYY-MM-DD&known_at=<offset-time>` captures one snapshot and returns facts, undated_facts, sources, conflicts, counts, profile and scope. Omit as_of for all recorded dates; availability still applies. Withheld values are null with `value_withheld:true`; quotes/regions are also withheld when a source falls outside the date scope. Original downloads use `GET /api/history/sources/{id}/original` with required known_at and optional as_of, matching that exact scope.

`GET /api/profile?known_at=...` returns a local profile revision. `PUT /api/profile` takes only `{date_of_birth: YYYY-MM-DD|null}` and stamps its revision server-side. Profile data is not added to provider extraction or question prompts. Age markers are computed only from exact dates.

Meta preview now uses text/image preparation and extract-then-verify. Every result is still a review proposal. Unknown/failed verification and uncalibrated model confidence never authorize a commit. Successful/partial runs expose sanitized per-call traces in `/api/changes`; duplicate uploads reopen existing reviews before any provider call.

