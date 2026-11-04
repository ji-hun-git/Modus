# Open-source components

Modus combines existing libraries with application code for reviewed records,
history scope and evidence checks. First-party source is [MIT licensed](../../LICENSE).
Dependency versions, licenses, model terms and retained notices are listed in
[Third-party notices](../../THIRD_PARTY_NOTICES.md) and the
[dependency inventory](DEPENDENCIES.json).

## garak regression fixtures

The backend reuses 26 upstream strings from
[NVIDIA garak](https://github.com/NVIDIA/garak), pinned at
`b1681c5bf8ff71971f83848fe245c6c1550aff08`. They exercise SQL injection,
Python execution and browser-script input against the document and record
boundaries. Their [notice](../../backend/tests/fixtures/garak/NOTICE.md) and
[Apache license](../../backend/tests/fixtures/garak/LICENSE) accompany the fixtures.

These tests check that strings remain literal document content, cannot save
themselves, retain source evidence and do not render as executable browser markup.
The integration uses test data, not garak's scanner or models. It does not measure
Muse jailbreak resistance or constitute a general security audit.

## Research scope

NeMo Retriever, Data Designer, Curator, Anonymizer and Guardrails were reviewed
as possible research tools but are not installed product integrations. The
application uses Meta Muse Spark when model processing is selected. Its offline
parser and document guard are deterministic software. Planned tooling is not
included in the demonstrated feature set.
