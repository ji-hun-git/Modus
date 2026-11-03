# Data provenance

The clean starter database contains three authored synthetic documents and nine
measurements: HbA1c, eGFR and LDL across three dates. These examples are invented;
they are not a real person's history or Synthea output. Counts shown in the app
come from the scoped database, including reviewed additions.

CSV/text/PDF/image examples used for software regressions are authored fixtures.
They test preservation, parsing, temporal boundaries, conflicts and recovery.
They are not representative clinical distributions or independent accuracy
labels. A synthetic-data confirmation is an assertion, not an identifier detector.

## Source and reviewed record are distinct

The original bytes, excerpt, page/region evidence and printed wording are kept.
Reviewed facts preserve values, units, date precision, lab range, specimen and
test method when provided. Availability is assigned by the server when review
commits. Corrections create new versions rather than rewriting originals.

## What leaves the device

Local deterministic processing makes no model request. Optional local OCR uses
a separately installed model. Explicit Meta processing sends the selected
supported document or permitted request context to the configured service.
Credentials remain server-side. Original documents may contain identifiers;
the current prototype does not claim automatic anonymization or zero retention.

The distributed service does not connect to hospitals, ingest raw DNA, or use
credentialed patient datasets. Broader private training preparations are not
part of the shipped product. Historical evaluation reports describe their own
data and revision limits; protected corpora must not be opened during ordinary
software checks.
