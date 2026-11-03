# Agent workflow

```text
Supported source file
  → bounded local parsing/OCR or explicitly selected Meta extraction
  → schema-checked proposal with original evidence
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

## Verification

The offline regression runner strips credentials, blocks external backend
networking and excludes protected evaluation inputs. Browser checks exercise
actual review, correction, questions, source navigation and exports. These
checks establish tested software behavior, not clinical accuracy or superiority
over other model workflows. [API contract](API_CONTRACT.md) ·
[Verification](VERIFICATION.md) · [Historical measurements](../../SCOREBOARD.md).
