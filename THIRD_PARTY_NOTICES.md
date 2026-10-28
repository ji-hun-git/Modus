# Third-party materials in Modus Records

Application dependencies retain their own licenses. Locked runtime/build/test versions are in backend/requirements.lock.txt and entry/frontend/package-lock.json. The inventory in entry/docs/DEPENDENCIES.json records declared metadata and available notice hashes; corresponding texts are under data/licenses/dependencies. Uninstalled optional platform packages are explicitly identified. This inventory is not a legal compatibility determination.

This entry uses authored synthetic records. It does not bundle Synthea exports, medical reference datasets, private supplied design documents, model weights, a trained adapter or the separate TeleOCR research environment. The full private Modus workspace preserves the wider research and provenance.

The optional local OCR adapter uses the separately installed XingChen-AGI/TeleOCR checkpoint pinned in config/teleocr.json, whose upstream model card declares Apache-2.0. Weights and its isolated environment are not part of the source package. scripts/requirements-ocr.lock.txt records that environment's dependencies; their own licenses apply. Optional OCR runtime qualification does not establish unrestricted production-upload suitability.

The owner has not selected a project-wide open-source license. No unsolicited license grant for the owner's code is made here. Dependency licenses and the competition's organizer agreement are separate matters.

## Record terminology

The small catalog associates nine LOINC codes with their official short names, checked on 28 October 2026. The [required LOINC notice](LOINC_short_license.txt) and [LOINC license](https://loinc.org/license) apply to those materials. The catalog's version is a Modus revision, not a claimed complete LOINC release. Local concept associations, retrieval aliases (including Korean) and qualification rules are Modus-authored annotations. No full terminology database, linguistic-variant dataset, SNOMED mapping or endorsement is included.

The bounded unit lookup recognizes a few recorded identities and references [UCUM](https://ucum.org/ucum), copyright Regenstrief Institute, Inc. See its [copyright notice, license and warranty terms](https://ucum.org/license). The specification/database is not redistributed. This lookup is not a general UCUM parser, conversion engine or conformance certification.
