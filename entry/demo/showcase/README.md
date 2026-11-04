# Fresh Muse demonstration

These three first-party authored reports are demonstration inputs, not real
histories, clinical reference ranges or training/evaluation data.

- [November checkup image](November%20checkup.png): three printed lab rows.
- [July checkup](July%20checkup.csv): HbA1c 5.6%, HPLC.
- [July copy](July%20lab%20copy.csv): the same value and date, Immunoassay.

The 2:42 video uses application behavior at `9c6dc2c`. The two July CSVs were
read and saved through the offline import/review handlers in an isolated
synthetic workspace. The November image was uploaded through the real UI with
Meta selected. Three actual Muse requests extracted, verified and inventoried
the source. All three rows were present; the header date and specimen needed
explicit review completion. The source-check warning remains visible.

Selecting November and July, then **Explain changes and discrepancies**, made
three further real model requests. Bounded tools followed the related copy and
returned the method discrepancy with both sources. No model wrote records.
An explicitly reviewed, authored correction then demonstrated saved versions
and stale-answer invalidation; it does not establish which report is correct.

[Per-call model, usage, timing and estimated cost](recording-calls.json) are
separate from the earlier 14-case development measurement. These six recording
calls cost an estimated $0.04740125; this is not an invoice. Original downloads
were compared byte for byte. The recording server was stopped after capture.

The video's Ask and temporal replay use offline typed tools in a different
preserved synthetic workspace. Cuts are edited to narration, not a latency
measurement. [Video and full provenance](../longitudinal/README.md#recorded-demonstration).
