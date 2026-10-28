# Meta workshop and Modus

Reviewed 28 October 2026 KST. The owner supplied an announcement for **Agents 101: Build a Multimodal AI Agent Pt. 1**. Its quoted $7 is the workshop organizer's estimate, not a measured Modus cost or hard spending cap. The announcement does not include its calendar date: noon–1 PM Eastern during October is 1–2 AM KST the following day. If it referred to October 27 ET, the session is October 28 KST.

The public [workshop repository](https://github.com/meta-models/legal-agent-workshop) resolved to commit `2a8efc86c70d9a42d76db0afb6ae1511e5a86d8e` (GitHub timestamp October 27, 15:23:40 UTC). Repository metadata returned no license. This review reads the documentation as design evidence; no workshop source was copied into Modus or executed. Its legal case, hidden evidence, solutions and ground truth were not opened. The announcement is not authorization to install tools, accept terms, submit keys or spend tokens.

## Useful engineering lessons

The workshop separates the model loop from source checks, tools and review. Its [agent guide](https://github.com/meta-models/legal-agent-workshop/blob/2a8efc86c70d9a42d76db0afb6ae1511e5a86d8e/agent/README.md) describes document reading, quote verification, saved progress and explicit requests for missing evidence. The [handbook](https://github.com/meta-models/legal-agent-workshop/blob/2a8efc86c70d9a42d76db0afb6ae1511e5a86d8e/HANDBOOK.md) distinguishes a first unverified result from subsequent independent checks. A genuine quote can still support the wrong conclusion; quote presence alone is not entailment.

| Workshop pattern | Modus application |
|---|---|
| Tools and verification outside model instructions | Keep typed tools, scope enforcement, exact supported claims and negative capability tests. |
| Evidence traced to documents | Retrieval returns the original observation/source IDs, values, units, dates and visible excerpt. Source IDs alone remain insufficient. |
| Explicit missing-evidence handling | Empty search is an absence in the selected record view, not proof that an event or care did not occur. |
| Evaluation materials outside agent workspace | Existing private held-out sets stay closed. New development cases are separately authored and frozen before measuring candidates. |
| Review and saved progress | Retain reviewed commit and honest same-tab recovery. The workshop's durable resume mechanism is a reference, not an implemented Modus feature. |
| Tool access matched to the job | Modus models remain read-only. Legal case writes, arbitrary filesystem tools and attorney sign-off do not transfer to the health-record entry. |

No published requirement says the workshop's exact architecture or every Meta model must be used in the contest. The current Modus work remains record integrity and retrieval, without personalized medical advice. The broader goals, contest boundary and eligibility uncertainty remain in [the continuity matrix](../entry/docs/GOALS_AND_PROMPTS.md).

## Windows and API preparation

The workshop uses a shell helper and `.venv/bin/python`; its handbook recommends macOS/Linux or WSL. The current [Muse Code documentation](https://dev.meta.ai/docs/muse-code) independently supports native Windows with PowerShell, while noting platform-specific feature gaps. Native Muse Code support does not verify the workshop's shell helper on Windows.

The workshop's setup helper installs its SDK/environment, seeds its local case and checks API model access. Therefore it is not a purely offline setup command. Jason continues to own access and authentication. Keep any eventual workshop checkout separate from Modus and its evaluation assets. This review did not install Muse Code/WSL, create a populated `.env`, check a key, run the legal agent or make a provider request.
