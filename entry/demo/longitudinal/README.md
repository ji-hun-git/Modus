# Explore one test across your records

These five CSVs are newly authored demonstration records, not real histories or
training/evaluation inputs. Values and printed intervals are fictional software
examples, not clinical reference guidance. See [provenance](provenance.json).

Use an isolated offline preview following the repository's setup/check/serve
instructions. Files are imported through the existing review flow; this folder
does not seed or overwrite a database automatically.

1. Add `2024-checkup.csv`, `2025-checkup.csv` and `2026-checkup.csv`. Review the
   dates, values, units, specimen, method and original excerpts before saving each.
2. On Home, choose `2026-checkup.csv` from the Orbit, then select Ferritin.
   The three dated values are **58.6 → 64.2 → 71.4 ng/mL**. Select a point or row
   to inspect that exact file and download its original.
3. Add and review `2025-conflicting-copy.csv`. Select TSH: both **2.5** and
   **2.9 mIU/L** on 15 March 2025 must remain visible. No winner is selected.
4. To exercise corrections, open Ferritin's 2024 evidence, expand
   **Corrections & saved versions**, and review a correction from **58.6** to
   **58.9** with a reason. Refresh the series. The saved value changes; the
   original excerpt and file still contain **58.6**.
5. Add and review `2019-late-arriving-checkup.csv`. Current history now includes
   **49.5 ng/mL** on 12 April 2019. A knowledge cutoff before this import must
   exclude it, even though its recorded date is earlier.
6. Open **Compare reports**, choose 2026 and 2025, inspect the original evidence,
   then review the comparison before downloading HTML or JSON. The additional
   TSH conflict must stay included in the evidence.

All numerical changes describe recorded values only. Missing records do not show
that a test or care never occurred. The app neither interprets these values nor
offers health advice.

The corresponding loopback HTTP flow and component rendering have been checked.
Actual browser interactions, keyboard behavior and responsive screenshots for
the new workspace remain an open acceptance item; these steps are not a claim
that that browser check has passed.
