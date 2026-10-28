# A usable record handoff

This milestone turns selected records into a dated, reviewable brief. It preserves the larger lifelong-history goal while giving the current service a concrete output: records someone can inspect before choosing to share. The brief is a factual compilation, not an assessment of health, a recommended care plan or an AI decision about which records a doctor needs.

## Experience

1. Open More, then Brief. Home keeps the essential results, Ask bar and Add records action.
2. Choose reviewed facts, grouped by original document. Search names/text or filter a record type. Nothing is selected automatically. Original evidence remains available while choosing.
3. Set a title and, optionally, a separately labelled personal note. Preview the dated records, partial dates, sources and any unresolved differences. Selecting a disputed fact includes the other records in that dispute, with the added sources explicitly shown.
4. Review the complete brief and confirm before downloading. Changing selection, note, title or date scope invalidates the prior review. Accepted record values remain unchanged; the brief editor changes selection and owner text only.
5. Download a self-contained HTML document with internal evidence references, or its structured JSON. Open HTML in a browser and use Print to save a PDF. No original source files are embedded or automatically sent.

The canonical preview identity binds the exact selected content and temporal bounds. Export cannot silently pick up later records or discard conflicts. Dates mean what the source records; unknown precision is retained. Historical prescriptions are not a statement of current medication use. All record views still honor the two separate clocks.

## Demonstration inputs

`data/synthetic/brief-demo/` contains four newly authored, fictional CSV records spanning childhood entries, a visit, a past prescription, imaging-report text and laboratory copies. They exercise all eight record types. Import files 01–03, prepare a brief, then review/import file 04 and make a new brief. The two Ferritin values remain separate; neither is declared correct. Old availability views keep their original records.

The demo does not touch the private held-out suites or frozen baseline. Software and browser checks establish implementation behavior; they do not establish that a person will save time or use the output.

## First user-value experiment

Proposed audience: people assembling records from more than one institution before a new-doctor appointment. Begin with 3–5 participants using these synthetic examples, with task order counterbalanced between Modus and a folder/notes workflow. No participants have been recruited and no study has run.

Use the same task and authored source set: prepare a brief containing specified recorded events, preserve the partial vaccination date, show both laboratory copies, identify the historical prescription without asserting current use, and verify selected statements against their sources. Measure total task time including upload/review/correction, important factual errors and omissions against the authored task key, verification time, assistance required and whether the person can explain the unresolved difference. Ask which output they would use and why. Do not turn that preference into a measured adoption or willingness-to-pay result.

A later, protected real-history pilot would need to measure record-collection effort, actual use in the intended situation and return use. Current storage/session/retention protections are incomplete; the synthetic study cannot answer those questions. Decide quantitative promotion targets before that experiment, rather than choosing a threshold after seeing results.

## Deliberate limits

The brief is session-scoped, with no saved brief archive or durable reload recovery. It does not make clinical relevance judgments, infer diagnoses, reconcile prescription use or interpret genetic/image content. Current discrepancy detection covers measurements, not contradictions in arbitrary narrative reports. The record source and original excerpt remain authority for factual content; the owner note remains a separate contribution. Anatomy navigation and genetics expansion stay future hypotheses until they improve a defined task.
