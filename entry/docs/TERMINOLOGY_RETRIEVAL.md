# Terminology and record retrieval

## Current history retrieval

The history tools use `literal_and_medical_aliases_v2`: 24 local medical concepts,
selected English, Korean and everyday aliases, fixed NIDDK/MedlinePlus reference
links, and ambiguity clarification. Records, Documents, Trends and Summary use
the same alias matcher before pagination. The model cannot invent aliases;
source values, names, units and revisions remain unchanged. Retrieval respects
both recorded-date and availability bounds. See the
[API contract](API_CONTRACT.md#medical-terminology-retrieval--30-october-2026)
and [verification](VERIFICATION.md).

These concept IDs are local vocabulary entries, not standardized clinical coding
or a complete medical ontology. There is no embedding model or external
clinical-reference retrieval pipeline in this path.

## Legacy three-metric retrieval

The remaining sections document the separate HbA1c, eGFR and LDL implementation.
Its nine LOINC variants, BM25 scoring and development scores apply to that path;
they do not qualify the current whole-history tools. Both paths preserve source
evidence and restrict tools to read-only access within a captured history.

## Scope

The versioned catalog covers HbA1c, eGFR and LDL cholesterol, with bounded English/Korean aliases and nine exact LOINC variants. It distinguishes known method, specimen, property and unit identity without converting values or inferring disease. This is a small record terminology layer, not a complete medical ontology or terminology server.

`search_record_evidence` takes a query and a limit from 1 to 8. It ranks eligible recorded rows using BM25 with catalog lookup terms, preserves exact values/units/dates/source excerpts, and returns typed fact sentences. Explicit code/method qualifiers require qualified source coding. A generic LDL label never establishes a direct or calculated assay. Scores order search results; they are not confidence estimates or medical significance.

Only already-visible rows and their source metadata participate. Full document text is not indexed. A partly visible historical document has its excerpt and FHIR source metadata withheld. Source and row availability are checked again inside retrieval. Imported text and quoted passages remain untrusted data.

Same-day disagreements remain unresolved. Matching companion values are included where the result limit allows. For a source-specific search, nonmatching companion values stay in separate bounded context, with an explicit warning; they do not become matching answer hits. Empty retrieval establishes only that the scoped search returned no supported match. It cannot establish that care or a measurement never occurred. Unsupported negated filters and relative date ranges abstain instead of reversing or simplifying the request.

The offline path performs deterministic retrieval and sentence construction with no model call. The Meta path may choose this read tool and select exact returned claim IDs. Model prose does not become an authoritative finding. Both model comparison methods receive access to the same query-specific retrieval evidence within the shared tool budget.

## Source semantics

The shared ingestion library can preserve bounded original FHIR coding, quantity, status, method, specimen and timestamps separately from its normalized record. Precise semantic matching is invalidated by incompatible units, conflicting codes, contradictory source metadata or edits to the normalized basis. This does not add JSON/FHIR uploads or a FHIR export to the contest entry; those remain part of the broader research application.

The entry still accepts only its existing supported document types and explicitly reviewed rows. Unknown method/coding stays unknown. Missing source coding is not repaired from a source ID, metric label or free-text excerpt.

## Evidence boundary

The new comparison uses separately authored synthetic **development** cases and a source snapshot frozen before implementation. Its inputs and grading contract are frozen before candidate execution. The existing frozen routing/parser comparison is retained separately. Neither comparison opens the held-out sets; neither establishes clinical validity, generalization or an end-to-end state-of-the-art result.

Dense embeddings, a neural reranker, external clinical RAG, ontology-wide reasoning and live Meta performance are not implemented or measured by this change. The simple lexical/terminology candidate must demonstrate a useful improvement before adding those dependencies. See the root `docs/ONTOLOGY_RAG_EVALUATION.md` and measured report for actual denominators and remaining failures.
