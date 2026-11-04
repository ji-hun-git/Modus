# Reviewed summaries

A summary compiles selected records, dates and source evidence into a document
you can inspect before downloading. It reports what the records say. It does
not assess health or decide which records a clinician needs.

## Prepare and download

1. Choose **Prepare a summary** on Home, or **More → Summary**.
2. Select reviewed facts, grouped by original document. Search names or text,
   filter by record type, and open evidence while choosing. Nothing is selected
   automatically.
3. Set a title and, optionally, add a separately labelled personal note. Preview
   the records, date precision, sources and unresolved differences. Selecting a
   disputed fact includes its conflicting records and identifies the added sources.
4. Review the full preview and confirm the download. Changing its selection,
   title, note or date scope invalidates that approval. Record corrections also
   require a new review.
5. Download self-contained HTML or structured JSON. Print the HTML from a browser
   to save a PDF. Original source files are not embedded or automatically sent.

The preview binds the selected content, saved revisions and both history cutoffs.
The download cannot silently pick up later records or drop a conflict. The summary
editor changes the selection and your note; it does not edit saved facts.

**Compare reports** is a separate flow for inspecting two files and their related
records. Its reviewed comparison export also binds the report identities, time
bounds and source evidence to the preview. [API contract](API_CONTRACT.md)

## Try the examples

[The brief examples](../../data/synthetic/brief-demo/README.md) contain four
fictional CSVs covering childhood records, a visit, a historical prescription,
imaging text and conflicting laboratory copies. Import and review files 01–03,
prepare a summary, then import file 04 and prepare another. Both Ferritin values
must remain visible; neither is declared correct. Earlier availability views
retain their original records.

For a longer report-to-report walkthrough, use the
[six-file demonstration](../demo/longitudinal/README.md).

## Limits

Summaries are session-scoped, with no saved summary archive or durable recovery
after reload. Downloaded files are not encrypted by Modus. Historical
prescriptions do not establish current use; missing records do not establish
missed care. Discrepancy detection covers measurements and their context, not
arbitrary contradictions in narrative reports.

Software and browser checks are recorded in [Verification](VERIFICATION.md).
No participant study has measured time saved, usefulness at appointments or
adoption. Those remain questions for a separate user study.
