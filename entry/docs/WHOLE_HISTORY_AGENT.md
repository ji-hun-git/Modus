# History questions

Ask searches reviewed records within the selected history and returns findings
that open their supporting evidence. It covers measurements, visits, recorded
diagnoses, procedures, prescriptions, vaccinations, imaging-report text and
other recorded text. Recorded clinical statements retain their source attribution;
Modus does not turn them into a new diagnosis or recommendation.

## Supported questions

| Example | Behavior |
| --- | --- |
| “What is my latest heart rate record?” | Find the latest dated group, including supported aliases such as Pulse. |
| “What about the one before that?” | Continue the same subject within the captured history; preserve ties and date limitations. |
| “When did I last have blood pressure of 100?” | Clarify which pressure component is intended, then retrieve matching recorded values. |
| “Show my prescription records.” | Return attributed historical entries without inferring current use. |
| “Find my vaccination records.” | Preserve exact, partial and unknown dates. |
| “Find my imaging reports.” | Retrieve recorded report text without interpreting scan images. |
| “Compare the latest two reports.” | Select an unambiguous pair by recorded date and investigate changes and discrepancies. |
| “Show conflicting measurement records.” | Return supported same-day discrepancies with the original sources. |

For a specific report pair, use **Compare reports → Explain changes and
discrepancies**, or name both exact filenames in quotes in Ask. Numerical
predicates outside supported query forms and ambiguous references may require
clarification. A no-match result describes the available records; it does not
establish that an event never occurred.

## Retrieval and model roles

The server captures the history scope before executing a request. Literal
matching and a controlled vocabulary of medical names support retrieval;
the model cannot invent aliases or widen access. See
[Terminology and record retrieval](TERMINOLOGY_RETRIEVAL.md).

Offline execution uses deterministic tools with no model call. With Meta
selected, Muse Spark requests permitted reads and selects exact tool-produced
claims. Unknown tools, changed filters, invented claim IDs and failed requests
cannot become successful answers. Actual provider identity and execution mode
remain visible.

Report investigation reads the selected pair and then checks related records
within the same captured history. Typed rules compare recorded values, units,
reference ranges, specimen, method and facility. Known differences and required
limitations remain in the answer even if the model selects fewer claims.
Missing metadata stays uncertain; it is not a contradiction by itself.

## Evidence and continuation

Every finding binds saved facts, revisions, source identity and both time bounds.
Opening a source uses the same scope as the answer. Text and original downloads
are withheld when a mixed-period document would expose records outside that view.
Corrections invalidate affected explanations, including those using a related
third file. Original excerpts can differ from corrected values; both stay visible.

Follow-ups use opaque server context, limited to 30 minutes, available capacity
and the current process lifetime. A changed view, expired context or ambiguous
reference requires a fresh question. This is temporary navigation context,
not persistent personal conversation memory.

## Limits and verification

Retrieval is bounded and supports controlled names, not a comprehensive medical
ontology. Discrepancy checks cover recorded measurements and metadata, not
arbitrary contradictions in narrative text. Clinical interpretation, treatment
advice, risk scoring and appointment management are outside the application.

Local access requires a session and stored records use encryption. These controls
do not establish production readiness or automatic anonymization; original text
can contain identifiers. [Data handling](DATA.md) ·
[API contract](API_CONTRACT.md) · [Agent workflow](AGENT_WORKFLOW.md)

[Verification](VERIFICATION.md) separates offline regressions, browser checks
and real Muse development runs. Authored fixtures and mocked provider failures
test software behavior; they do not measure independent model accuracy.
