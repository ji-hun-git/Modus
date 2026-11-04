# Product guide

Modus connects reviewed medical records across time while keeping the original
sources inspectable. The person using it owns the history and approves every
saved change. The application retrieves and compares recorded facts; it does
not provide clinical interpretation or health advice.

## Navigate the workspace

| Destination | Use it to |
| --- | --- |
| Home | Select a source file, inspect readings and their history, ask a question or add records. |
| Records | Browse recorded events on the timeline. |
| More → Ask | Search the captured history and continue supported questions. |
| More → Summary | Select records, review their evidence and download a summary. |
| More → Trends | Explore compatible recorded measurements over time. |
| More → Documents | Browse saved source files. |
| More → Replay | Compare historical views using recorded and availability dates. |
| More → Changes | Inspect record activity. |

Home's orbit represents source files owned by the person at its center. Each
file opens actual evidence; the connecting lines do not imply medical
relationships. The selected report initially shows four readings. Larger
reports use expandable, paginated lists, and every chart point opens its source.

The timeline controls recorded dates. **More history tools** exposes both date
bounds; **Today** restores the current view. Evidence remains unavailable while
a changed view loads, so a previous answer cannot appear to describe the new
selection. Appearance supports light, dark and system settings. Orbit motion
can be paused and respects reduced-motion preferences.

## Add and review records

1. Choose **Add records** and a supported synthetic document. Local parsing and
   Meta reading are separate, labelled modes. Failures remain visible.
2. Review each proposed entry beside its source excerpt. Edit or exclude fields
   before saving. Meta reading includes a separate source-only row inventory
   that can flag possible omissions; it does not establish completeness.
3. Review any flagged row you want to include. Its original proposal remains
   intact beside your edits. Navigation preserves the draft, and save validation
   checks all included entries, including those on another page.
4. Save the explicitly selected rows as one transaction. If the response is lost,
   retry the same reviewed payload to recover its receipt without duplication.
5. Inspect the updated history. Importing does not silently replace a historical
   view you already selected.

An unfinished import changes Home's action to **Continue review**. Drafts remain
in the current tab and are not restored after reload. Reopening a saved report
can recover remaining flagged rows for a new review; additions receive their
actual save time without rewriting the original file or earlier views.

## Inspect and correct evidence

The source inspector places the saved value, recorded date and availability
date beside the original passage and printed lab context. Entry navigation stays
within that source and history scope. Closing the inspector returns keyboard
focus to the control that opened it.

**Correct saved record** creates a reviewed amendment with a reason. It preserves
the original bytes, excerpt and earlier saved versions. A correction refreshes
the current history and invalidates explanations that used the changed record.
Conflicting sources remain separate; no value is automatically declared correct.

Original downloads respect the same history bounds as the selected evidence.
A document containing later records cannot expose those records through an
earlier view. Display aliases never rewrite a saved test name, convert its units
or supply clinical meaning.

## Ask, compare and export

[Ask](WHOLE_HISTORY_AGENT.md) returns recorded facts, uncertainty and clickable
evidence. Follow-ups remain attached to the captured history; expired or changed
context requires a new question.

**Compare reports → Explain changes and discrepancies** investigates a selected
pair and related records in the same view. Conflicting same-day results appear
first, including copies in a third file. Typed tools calculate compatible
changes and explain when units, specimen, method or source support prevent a
numerical comparison. Each finding opens its exact records and original excerpts.

**Prepare a summary** lets you choose records, inspect their sources and review
the full preview before downloading HTML or JSON. Opening the preview exports
nothing. See [Reviewed summaries](RECORD_BRIEF.md) for the selection and recovery
limits, and [Data provenance](DATA.md) for storage and external processing.

[Run locally](../../README.md#run-locally) ·
[Try the sample records](../demo/longitudinal/README.md) ·
[API contract](API_CONTRACT.md) · [Verification](VERIFICATION.md)
