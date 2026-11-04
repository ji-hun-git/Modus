# Contributions and provenance

**Entry:** Indie Developer · Build for Your World. **Team and submitter:** Jihun
Chae (solo). The owner selected the MIT license on 4 November 2026; it applies
to first-party Modus source, with third-party notices retained.

The team has declared the first-party Modus source to have been created after
the 26 October 2026 kickoff, within the 26 October–4 November event period.
Git commits retain their actual creation dates; imported source is not presented
as a reconstructed earlier history. The first public import, `9be6b70`, is dated
28 October. This is the team's provenance declaration plus its actual commit
record, not a claim that timestamps independently establish eligibility.

AI coding assistance contributed to implementation, design and testing. Human
review controls saved records and release decisions. Third-party packages,
fonts, reference metadata and model assets keep their own licenses and notices.
No claim is made that dependencies or foundation models were created by Modus.

## Event-built contribution map

| Team-built behavior | Source to inspect | What a demonstration can show |
| --- | --- | --- |
| Structured Muse document reading, a verification pass and a separate source-only inventory | [Extraction](../../backend/modus/record_extraction.py), [row inventory](../../backend/modus/record_row_inventory.py) | Actual proposed fields, verification disagreements and possible omitted rows before human review. Reading does not save records. |
| Reviewed imports and append-only corrections | [Record store](../../backend/modus/record_store.py), [amendments](../../backend/modus/record_amendments.py) | Corrected saved values alongside unchanged original bytes and earlier versions. |
| Occurrence and availability replay | [History projection](../../backend/modus/record_history_view.py) | A late-arriving old report changes the current view while an earlier knowledge view stays unchanged. |
| Bounded history questions and checked numerical findings | [Query planner](../../backend/modus_entry/history_query_plan.py), [executor](../../backend/modus_entry/history_query_executor.py), [Muse planning boundary](../../backend/modus_entry/history_query_muse.py) | Clarify ambiguous numbers, return dated recorded facts and open their supporting excerpts. |
| Context-aware report comparison and reviewed summaries | [Report summary](../../backend/modus_entry/report_summary.py), [brief contract](RECORD_BRIEF.md) | Literal units, lab context, conflicts, uncertainty and original evidence stay attached. |
| Cross-report Muse investigation with checked discrepancies | [Bounded loop](../../backend/modus_entry/investigation.py), [tools](../../backend/modus_entry/report_investigation_tools.py) | A same-number method difference, both originals, no model write, and stale-answer invalidation after a reviewed correction. |
| File-orbit Home and evidence navigation | [Frontend source](../frontend/src) | Select a file, inspect its readings, scrub dates and open original evidence. |
| Local access and encrypted persistence | [Access boundary](../../backend/modus_entry/local_access.py), [encryption](../../backend/modus/record_crypto.py), [verified migration](../../backend/modus/record_encryption_migration.py) | Owner access, preserved history across restart and exact original downloads. Cryptographic primitives are supplied by SQLCipher, not invented here. |
| Repeatable isolated rehearsal | [Checked launcher](../../scripts/serve_service.py) | A new take without resetting the owner's normal workspace or spending model credits. |

## Materials that are not team inventions

Meta foundation models, Python/React/FastAPI/SQLite/SQLCipher, OS credential
services, dependency libraries, Inter, LOINC names and reused garak test payloads
pre-exist this project. Their terms and notices are retained separately. Synthetic
demo reports and the Modus application logic are the team's authored materials.
Private design references, training research and third-party model checkpoints
are not represented as newly invented or bundled contest functionality.

## Demonstration claim boundary

Show only event-built Modus behavior in the submitted video. Identify the new
application work at the start and credit reused components. The video must use
the submitted source revision, with any later change called out rather than
silently borrowing an older result. Current offline computation and reopened
saved Muse drafts must remain labelled as such; neither is a new live call.

Live development probes are described in [VERIFICATION.md](VERIFICATION.md).
They use authored examples and do not establish clinical accuracy, general
omission recall, state-of-the-art superiority or final release qualification.
The current entry does not demonstrate hosted SAM, Prompt Guard/Llama Guard,
Voice, a medical fine-tune or the cross-provider evaluation jury. Do not imply
that these planned/research capabilities are part of the shown product.

The contest scope is record integrity: no diagnosis, medical interpretation,
risk scoring, treatment advice or nutrition/mental-health coaching. The proposed
theme is **Build for Your World**, in the **Indie Developer** track. Jihun Chae
is the sole team member and designated submitter. This scope is an implementation boundary, not an
organizer ruling on eligibility.

Public source is not a contest submission or an eligibility confirmation.
First-party source uses the [MIT License](../../LICENSE). See
[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) for dependency terms.
