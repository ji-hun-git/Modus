# Data provenance

The clean starter database contains four authored synthetic documents and 17
measurements across 11 distinct test labels. Three older examples retain HbA1c,
eGFR and LDL; the October 2026 checkup adds glucose, hemoglobin, white blood
cells, platelets, ferritin, TSH, vitamin D and ALT with printed lab context and
an original CSV. Its occurrence date is October 22; its authored availability
is October 23. No human or model review is claimed for starter fixtures.

These examples and their printed ranges are invented, not a real person's
history, clinical guidance or Synthea output. Existing databases are never
reseeded during startup. The same checkup is available in Add records for an
explicit review and import into an existing demo. Counts shown in the app come
from the scoped database, including reviewed additions.

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
