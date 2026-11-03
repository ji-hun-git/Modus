# Product flow

Modus connects a person's reviewed medical records across time while keeping
each original source inspectable. Address the person as the owner of their
history. The contest application is a record-integrity service, not a health
advisor.

## A simple Home, detail when requested

Home centers the owner in a source-file orbit, with four readings initially,
one Ask bar and one Add records action. "Show all" expands the selected report's
current page (at most 50 entries); larger reports retain pagination. Home uses
open-ended saved labels, including tests outside the legacy three-metric API.
File satellites open actual source evidence. Records, trends, replay, discrepancies and summaries remain
available through deeper navigation.

Home exposes the actual recorded-difference group count and a direct action to
prepare a source-backed summary. The single Add records action becomes Continue
review with the pending file count when this tab has unfinished imports. Empty
states show no invented differences or pending work. Precise time controls stay
under More history tools; both applied clocks and the scrubber remain visible.
Opening a summary does not export anything: selection, source review and an
explicit reviewed download are still required.

Dragging the history timeline updates its date immediately and requests the
matching records during the drag, at most once per 120 ms plus a final flush.
The control remains mounted; superseded requests are cancelled and cannot replace
the final selected view. Retained evidence is marked busy and non-interactive
until its requested occurrence/availability scope arrives. Today restores the
current view. File spokes mean ownership, not inferred clinical relationships.
Slow opacity-only orbit motion can be paused. System reduced motion is the
default, with a separate explicit choice to enable gentle motion in this app.

Use familiar descriptions beside original test names where supported. A display
alias never rewrites the saved label, changes units or supplies clinical meaning.
Charts connect observations only when the backend comparison policy permits it.

## Review and preserve

1. Add a supported synthetic document. Show the actual extraction mode and failures.
2. Review proposed fields beside the original. Edit, exclude or accept explicitly.
3. Save the selected rows as one idempotent transaction. Recover uncertain saves using the same reviewed payload.
4. Inspect the new history without silently replacing a chosen historical view.
5. Correct saved transcriptions through a reviewed amendment. Keep the original and earlier versions.
6. Compare selected reports and review a source-linked summary before downloading it.

Original-file downloads obey the same occurrence and availability scope as the
selected evidence. A source containing later records cannot bypass an earlier
view. Conflicting sources remain separate; no value is automatically declared
correct.

## Ask and continue

Questions return recorded facts, explicit uncertainty and clickable evidence.
No-match means no supported match in the available reviewed records, not that
an event never happened. Numerical comparison requires compatible saved context.
Temporary conversation tokens are scoped to the captured history; changed scope,
expiry or ambiguous references require a full question.

The assistant never diagnoses, recommends treatment, infers current medication
use, scores risk or interprets scan images. Original clinical statements can be
retained as source text with attribution. [API behavior](API_CONTRACT.md) defines
the exact supported operations and limits.
