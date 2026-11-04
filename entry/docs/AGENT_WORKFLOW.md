# Agent workflow

```text
Supported source file
  → bounded local text parsing or explicitly selected Meta extraction
  → schema-checked proposal with original evidence
  → source-only row inventory; possible omissions flagged separately
  → explicit human review
  → transactional reviewed records
  → captured occurrence and availability scope
  → validated read-only operation
  → deterministic findings and checked claims
  → original source inspection
```

## Model authority

Muse Spark is the only hosted model in the product path. Extraction and its
verification pass propose fields; neither commits records. Agent tools are
allowlisted reads. Arguments cannot select another owner, widen captured scope,
write SQL/code, choose an arbitrary endpoint or modify records.

A third source-only Muse reading inventories recorded rows without seeing the
proposal. Code compares that inventory against the draft and flags possible
omissions with original-page excerpts. The candidates become facts only after
explicit owner selection and review through the omission commit contract.
Original inventory evidence is immutable; corrections are stored separately.
A failed, limited or empty inventory cannot establish completeness.
The same model can miss rows in both readings; offline injected responses verify
the software contract, not live omission-detection quality.

Offline parsers and numerical tools are ordinary software, explicitly labelled
as such. Failed model calls are retained as failures; an offline result is never
silently presented as a model response. Actual provider identity, timing and
usage are distinct from injected test transport metadata.

## Evidence and comparison

Retrieval uses controlled medical-name aliases and literal saved labels/text.
It is not a comprehensive medical ontology or a clinically validated semantic
model. Typed tools determine numerical findings. Comparison requires exact
units, suitable date precision and compatible recorded lab context. Qualified
values, conflicts and missing context can prevent calculation.

Claims bind saved facts, source identity, revisions and captured scope. Original
excerpts can differ from reviewed corrections; both remain visible. Referencing
a source ID alone never establishes support for arbitrary model prose.

Cross-report investigation binds two files to one captured view before calling
Muse. `compare_selected_reports` checks every visible reviewed item in the pair;
`inspect_report_discrepancies` checks matching measurement names and full recorded
dates across related files in that view. Exact vocabulary aliases are allowed.
It checks both recorded values and known lab metadata, including same-number
method, specimen, reference-range and facility differences. Missing metadata is
review context, not a contradiction. Decimal spelling, equivalent bound glyphs
and whitespace alone do not create value conflicts; original evidence is never
normalized in storage. Qualified results never become numerical deltas.
The two reads accept empty arguments, must run in that order, and precede exact
claim selection. Tool-computed changes, conflicts and context limitations remain
in the answer even if the model selects only a subset. Conflicts appear first.
No model prose, winning value, clinical explanation or record write is accepted.

The same two reads run without a model offline. Source excerpts, versions and
both time bounds remain inspectable. A new correction invalidates the displayed
explanation, including corrections to a related third file. At most 48 pair
records and 64 total evidence records are investigated; larger results are
rejected before provider access instead of silently truncated. The paged report
comparison remains available. This checks recorded values, units and metadata,
not arbitrary semantic contradictions throughout report prose.

## Verification

The offline regression runner strips credentials, blocks external backend
networking and excludes protected evaluation inputs. Browser checks exercise
actual review, correction, questions, source navigation and exports. These
checks establish tested software behavior, not clinical accuracy or superiority
over other model workflows. [API contract](API_CONTRACT.md) ·
[Verification](VERIFICATION.md) · [Historical measurements](../../SCOREBOARD.md).
