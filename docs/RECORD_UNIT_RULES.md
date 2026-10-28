# Recorded units — bounded normalization contract

Checked 28 October 2026. `backend/modus/record_units.py` adds server-owned arithmetic metadata alongside the exact original label, value text and unit. Existing three-metric types and their stored values are unchanged. No diagnosis, reference-range judgment or clinical comparability follows from a unit match.

| Explicit recorded concept | Accepted units | Normalized result |
| --- | --- | --- |
| Height; recumbent body length kept as a separate concept | `m`, `cm`, `mm` | `cm`, using exact decimal powers of ten |
| Body weight | `kg`, `g` | `kg`, exact factor 1 or 1/1000 |
| Body temperature | `Cel`, `°C`, `℃`, `[degF]`, `°F`, `℉` | Celsius; Fahrenheit uses exactly `(value − 32) × 5/9` |
| Heart rate; respiratory rate kept separate | Explicit configured per-minute spellings | `/min`, identity only |
| Systolic and diastolic blood pressure kept separate | `mm[Hg]`, `mmHg`, `mm Hg` | `mm[Hg]`, identity only |
| BMI as already recorded | `kg/m2`, `kg/m²`, `kg/m^2` | `kg/m2`, identity only; no BMI calculation |
| Established HbA1c, LDL and eGFR labels | Configured original unit identities | Same physical unit, spelling normalization only; no method conversion |

The metric powers follow [NIST's SI prefix definitions](https://www.nist.gov/pml/owm/metric-si-prefixes). The affine temperature rule follows [NIST SP 811, Appendix B.8](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8). [UCUM](https://ucum.org/ucum) supplies the unit notation and distinguishes temperature transformations from simple multiplicative units. The implementation is a closed list of rules, not a general UCUM parser. Case-sensitive symbols are preserved; unknown spellings remain unresolved.

Arithmetic uses exact rational numbers derived from decimal input strings. The normalized result includes a numerator and denominator. Finite decimal results are exact. A repeating result such as 99 °F becomes the exact fraction 335/9 °C plus a display decimal rounded to 34 significant digits with an explicit rounding label. Downstream equality must use the fraction, not rounded display text. Original precision and spacing remain available in `original`.

Inequalities, ranges, uncertainty intervals, combined blood-pressure values and ambiguous decimal/grouping separators remain verbatim and unnormalized. Explicit whole signed/scientific decimal values are accepted within bounded lengths. Unrecognized analytes receive no conversion merely because their unit looks familiar. A local concept name is not an assigned LOINC code, specimen, method or proof that two tests are clinically comparable.

HbA1c percentages and mmol/mol remain separate. [LOINC 4548-4](https://loinc.org/4548-4) and [59261-8](https://loinc.org/59261-8) distinguish standardization protocols; their relationship is not a generic fraction-unit rescaling. When a recorded label is itself one of the existing recognized LOINC codes, its unit must match the existing catalog's qualified semantics. An incompatible unit is left unresolved.

No mass-to-amount conversion is enabled in this slice. [CDC NHANES's LDL documentation](https://wwwn.cdc.gov/nchs/data/nhanes/public/2017/datafiles/p_trigly.htm) publishes 0.02586 for LDL cholesterol mg/dL to mmol/L. That analyte-specific protocol factor must not be applied to glucose, creatinine, triglycerides or an unknown analyte. A future conversion should explicitly distinguish a published rounded convention from an exact physical conversion, preserve its source/version, and test each analyte separately. The present module preserves both LDL unit families without converting between them.

Korean and English aliases are exact-label lookups. Body length and standing height are deliberately separate, as are systolic and diastolic pressure. Labels with additional qualifications remain unknown unless explicitly cataloged. Unknown originals can still be retained in the broader record model.
