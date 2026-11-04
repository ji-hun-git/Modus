# Contributions and provenance

| Entry | Detail |
| --- | --- |
| Entrant and submitter | Jihun Chae, solo. |
| Competition | Meta Global AI Developer Hackathon 2026. |
| Track and theme | Indie Developer / Build for Your World. |
| First-party license | [MIT](../../LICENSE), selected on 4 November 2026. |

The entrant declares that first-party Modus work was created after the
26 October kickoff, during the 26 October–4 November event period. The first
public import, `9be6b70`, is dated 28 October. Commits retain their actual dates;
the import is not presented as reconstructed development history. This is the
entrant's provenance declaration, not an independent eligibility ruling.

AI coding assistance contributed to implementation, design and testing.
The entrant owns the product and submission decisions. Every saved record change
requires human review. Synthetic reports are authored examples; they are not
real medical histories. Video narration is AI-generated locally, with its
model and runtime credited in [Third-party notices](../../THIRD_PARTY_NOTICES.md).

## Event-built application work

| Contribution | Implementation | Observable behavior |
| --- | --- | --- |
| Muse document reading and source checks | [Extraction](../../backend/modus/record_extraction.py), [row inventory](../../backend/modus/record_row_inventory.py) | Proposed fields, disagreements and possible omitted rows remain reviewable before saving. |
| Reviewed imports and corrections | [Record store](../../backend/modus/record_store.py), [amendments](../../backend/modus/record_amendments.py) | Corrected values retain original bytes and earlier saved versions. |
| Recorded-date and availability replay | [History projection](../../backend/modus/record_history_view.py) | A late report updates current history without rewriting an earlier availability view. |
| Scoped history questions | [Planner](../../backend/modus_entry/history_query_plan.py), [executor](../../backend/modus_entry/history_query_executor.py), [Muse boundary](../../backend/modus_entry/history_query_muse.py) | Ambiguous numerical questions can be clarified; findings open supporting records. |
| Cross-report investigation | [Bounded loop](../../backend/modus_entry/investigation.py), [tools](../../backend/modus_entry/report_investigation_tools.py) | Typed checks expose discrepancies in values and lab context, including related files. |
| Reviewed summaries | [Report summary](../../backend/modus_entry/report_summary.py), [summary contract](RECORD_BRIEF.md) | Downloaded records retain sources, time bounds, conflicts and uncertainty. |
| File navigation and evidence review | [Frontend](../frontend/src) | The orbit, timeline and source inspector connect each reading to its file. |
| Local access and encrypted persistence | [Sessions](../../backend/modus_entry/local_access.py), [encryption](../../backend/modus/record_crypto.py), [migration](../../backend/modus/record_encryption_migration.py) | Local access is authenticated; records persist with exact original downloads. |
| Isolated local rehearsal | [Checked launcher](../../scripts/serve_service.py) | Named workspaces keep separate persistent histories without resetting existing data. |

## Existing components and materials

Meta models, Python, React, FastAPI, SQLite, SQLCipher, OS credential services,
Inter, LOINC names and reused garak test strings predate Modus. The application
integrates them; it does not claim their models, standards or cryptographic
primitives as original work. Dependency terms and retained licenses are indexed
in [Third-party notices](../../THIRD_PARTY_NOTICES.md).

Private reference material, model checkpoints and broader training experiments
are excluded from the contest source. The source selection is recorded in
[`entry/config/source_manifest.json`](../config/source_manifest.json).

## Demonstration and evidence

The [2:46 demonstration](https://ji-hun-git.github.io/Modus/) records application
behavior at `9c6dc2c`. Its six actual Muse requests cover document extraction,
verification, row inventory and cross-report investigation. Ask and historical
replay sequences use labelled offline tools. [Inputs and call receipts](../demo/showcase/)
identify the recording evidence; later media and documentation edits do not
change that demonstrated application revision.

[Verification](VERIFICATION.md) separates software checks from live development
measurements. The latter use authored cases and do not establish independent
accuracy or clinical validation. The application does not supply diagnosis,
medical interpretation, risk scoring or treatment advice. Hosted SAM, Guard,
Voice, medical fine-tuning and the research evaluation jury are not demonstrated
product features. Publishing the repository is separate from portal submission.
