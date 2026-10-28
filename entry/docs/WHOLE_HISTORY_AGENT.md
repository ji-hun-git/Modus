# Whole-history record agent — 28 October 2026

The user value is finding a fact across years of reports and opening the exact record that supports it. The agent can now read measurements with arbitrary names, visits, diagnoses as recorded, procedures, prescriptions, vaccinations, imaging-report text and other recorded text. Upload, review and save still precede access. This milestone extends the existing eight-kind store to questions; it does not claim every medical file format is understood.

| Question | Result |
|---|---|
| Show my prescription records | Source-attributed historical prescriptions, without inferring current use |
| Find my vaccination records | Recorded entries with exact, partial or unknown dates preserved |
| Find my imaging reports | The report's recorded wording, without interpreting scan images |
| Find records mentioning "Height" | Literal matching across eligible reviewed facts |
| Which records became available between these views? | Additions between explicitly selected availability bounds |
| Show conflicting measurement records | Existing same-label/day discrepancies, with both values retained |

## Runtime and evidence

`history_views` captures one SQLite transaction and clock for both views. `history_tools` removes profile, age, reviewer and original proposals before tool access. Occurrence dates and availability timestamps remain separate. Historical projections withhold text/originals from mixed-period documents; excluded future rows cannot make a source appear safe.

The server parses a bounded factual request and fixes its tool name/arguments. Offline mode executes that tool directly. Live mode lets Muse Spark invoke that same bound tool and select exact returned claims through the shared validation loop. Material limitation claims remain mandatory. This is constrained orchestration, not autonomous clinical reasoning. Unknown tools, altered filters, invented claim IDs, refusals and failed requests cannot become a successful answer.

Retrieval is literal across reviewed labels, values, permitted quotes and source metadata. It supports quoted phrases and explicit dates; it does not infer medical synonyms or relationships. Results are paged/bounded and show omissions. Measurement discrepancy detection does not detect contradictions in prescriptions, diagnoses or free text. No prescription proves current use; no absent result proves missed care.

## Interface

Home keeps results and dates first. Home, Records and Documents include a question panel with concrete examples, optional availability comparison and source inspection. Each answer remains attached to the dates used to produce it. Scope changes invalidate answers and their dialogs. Exact original excerpts and downloads use those same bounds. Trends and the older Replay question interface retain their three-metric scope.

## Verification and remaining work

Fresh authored tests cover all kinds, exact decimals, unknown dates, late availability, source withholding, injection-like text, authority rejection, evidence privacy, live-path mock failures and stale-response handling. The separate development comparison uses the unchanged legacy three-metric agent as a capability reference on new authored cases. It is not a frozen held-out evaluation, clinical study or proof of SOTA quality. Existing frozen baselines and held-outs are untouched.

Real personal data remains outside this synthetic prototype. Profile omission is data minimization, not comprehensive de-identification: names or identifiers in record text are not automatically masked. Production access control, encryption/key management, redaction quality and deletion/retention controls require separate implementation and validation. The broader product goals remain in the project plan; anatomy navigation, appointment briefs and clinical interpretation are not delivered by this milestone.
