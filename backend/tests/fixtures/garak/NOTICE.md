# NVIDIA garak test payloads

`sql_injection.json`, `python_code_execution.json` and `markdown_js.json` are
unmodified copies from `garak/data/payloads/` in
[NVIDIA/garak](https://github.com/NVIDIA/garak/tree/b1681c5bf8ff71971f83848fe245c6c1550aff08/garak/data/payloads),
commit `b1681c5bf8ff71971f83848fe245c6c1550aff08`, retrieved 3 November 2026.
The upstream Apache License 2.0 is included in `LICENSE`.

Modus uses these strings as inert, adversarial document content in offline
software regression tests. They must never be executed, followed as instructions
or sent to an external service by these tests. This is corpus reuse, not a run
of the garak scanner or evidence of model jailbreak resistance. No garak code
or model becomes a product dependency.
