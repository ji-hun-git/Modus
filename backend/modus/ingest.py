import csv
import io
import json
import hashlib
import re
from datetime import date, datetime
from pypdf import PdfReader
from .record_models import Observation, METRICS, FHIRCodeableConcept, FHIRQuantity, FHIRProvenance
from .ontology import MODUS_METRIC_CODE_SYSTEM, exact_concept, resolve_codings, qualify_source_metadata
from .temporal import instant

MAX_BYTES = 8 * 1024 * 1024

class NoObservationsError(ValueError):
    """No usable rows is distinct from parser/transport failure in evaluations."""


class _FHIRRow(dict):
    """Internal marker: only parsed source FHIR may attach source semantics."""

def validate_document(raw, filename):
    if len(raw) > MAX_BYTES:
        raise ValueError('Maximum file size is 8 MB')
    if filename.lower().endswith('.pdf'):
        reader = PdfReader(io.BytesIO(raw))
        if len(reader.pages) > 30:
            raise ValueError('This prototype accepts PDF documents up to 30 pages')
ALIASES = {"hba1c": "hba1c", "hb a1c": "hba1c", "a1c": "hba1c", "4548-4": "hba1c", "17856-6": "hba1c", "egfr": "egfr", "33914-3": "egfr", "62238-1": "egfr", "98979-8": "egfr", "ldl": "ldl", "ldl cholesterol": "ldl", "13457-7": "ldl", "18262-6": "ldl"}

def metric_key(value):
    return exact_concept(value)

def canonical_unit(metric, unit):
    # Only aliases, never silently convert an assay's value or infer a missing unit.
    if metric == "egfr" and unit in ("mL/min/1.73 m2", "mL/min/{1.73_m2}", "mL/min/1.73m²"):
        return METRICS[metric]["unit"]
    return str(unit)

def parse_fhir(data):
    entries = [e.get("resource", {}) for e in data.get("entry", [])]
    subjects = {str(r.get("subject", {}).get("reference")) for r in entries if r.get("resourceType") == "Observation" and r.get("subject", {}).get("reference")}
    if len(subjects) > 1:
        raise ValueError("Import one synthetic person's FHIR records at a time")
    rows, warnings = [], []
    for r in entries:
        if r.get("resourceType") != "Observation":
            continue
        if r.get("status") in ("entered-in-error", "cancelled", "preliminary"):
            warnings.append(f"Skipped non-final observation {r.get('id', '')}")
            continue
        try:
            code = FHIRCodeableConcept.model_validate(r.get('code', {}))
            quantity = FHIRQuantity.model_validate(r.get('valueQuantity', {}))
        except (ValueError, TypeError):
            warnings.append(f"Skipped malformed or oversized FHIR metadata for observation {r.get('id', '')}")
            continue
        q = quantity.model_dump(exclude_none=True)
        resolution = resolve_codings([c.model_dump(exclude_none=True) for c in code.coding], q)
        metric = resolution['metric']
        if not metric:
            warnings.append(f"Skipped unsupported observation {r.get('id', '')}")
            warnings.extend(resolution['issues'])
            continue
        if q.get("comparator"):
            warnings.append(f"Skipped censored value {r.get('id', '')}; inequalities are not point measurements")
            continue
        resolution = qualify_source_metadata(resolution, r.get('method'), r.get('specimen'))
        warnings.extend(resolution['issues'])
        unit = (q.get('code') if q.get('system') == 'http://unitsofmeasure.org' else None) or q.get('unit') or q.get('code') or ''
        rows.append(_FHIRRow({"metric": metric, "value": q["value"], "unit": unit,
            "date": str(r.get("effectiveDateTime", ""))[:10], "reported_at": r.get('issued'),
            "source_span": json.dumps(r, ensure_ascii=False)[:780],
            '_fhir_source': {'original_code': code.model_dump(exclude_none=True),
                'original_quantity': q, 'original_status': r.get('status'),
                'original_method': r.get('method'), 'original_specimen': r.get('specimen'),
                'original_effective_date_time': r.get('effectiveDateTime', ''),
                'original_issued': r.get('issued'), 'resolution': resolution}}))
    return rows, warnings

def make_draft(filename, raw, extracted=None, *, extraction_mode="meta"):
    validate_document(raw, filename)
    digest = hashlib.sha256(raw).hexdigest()
    sid = f"import-{digest[:20]}"
    extension = filename.rsplit(".", 1)[-1].lower()
    warnings, text = [], ""
    subject_id = None
    if extracted is not None:
        if extraction_mode not in ("meta", "local-teleocr"):
            raise ValueError("Unknown extraction identity")
        rows = extracted
        label = "Local TeleOCR" if extraction_mode == "local-teleocr" else "Meta"
        text = f"{label} model-extracted document. Review each field before importing.\n" + "\n".join(str(r.get("source_span", "")) for r in rows)
        mode = extraction_mode
    elif extension in ("csv", "json", "txt"):
        text = raw.decode("utf-8-sig")
        if extension == "csv":
            rows = list(csv.DictReader(io.StringIO(text)))
        elif extension == "json":
            data = json.loads(text)
            if isinstance(data, dict) and data.get("resourceType") == "Bundle":
                people = [e.get("resource", {}).get("id") for e in data.get("entry", []) if e.get("resource", {}).get("resourceType") == "Patient"]
                subjects = [e.get("resource", {}).get("subject", {}).get("reference", "") for e in data.get("entry", []) if e.get("resource", {}).get("resourceType") == "Observation"]
                identities = {str(p) for p in people if p} | {s.rsplit('/',1)[-1].removeprefix('urn:uuid:') for s in subjects if s}
                if len(identities) > 1:
                    raise ValueError("FHIR subject identifiers disagree; do not merge different people's histories")
                subject_id = next(iter(identities), None)
                rows, warnings = parse_fhir(data)
            else:
                rows = data.get("observations", []) if isinstance(data, dict) else data
        else:
            rows = parse_text(text)
        mode = "local"
    elif extension == "pdf":
        reader = PdfReader(io.BytesIO(raw))
        if len(reader.pages) > 30:
            raise ValueError("This prototype accepts PDF documents up to 30 pages")
        rows = []
        for page_no, page in enumerate(reader.pages, 1):
            # Geometric layout keeps separately drawn table cells on their row.
            # Never flatten all whitespace: it can join an incomplete result to
            # another row's unit/date or to a document/reference date.
            page_text = page.extract_text(extraction_mode="layout", layout_mode_space_vertically=False) or ""
            text += page_text + "\n"
            rows.extend([{**r, "page": page_no} for r in parse_text(page_text)])
        mode = "local-pdf-text"
        warnings.append("Local text extraction supports explicit metric/value/unit/date rows. Scans require the Meta document adapter.")
    else:
        raise ValueError("Use CSV, FHIR JSON, text or a text-based PDF. Image extraction requires the live Meta adapter.")
    if not isinstance(rows, list) or len(rows) > 1000:
        raise ValueError("A document must contain at most 1,000 observation rows")
    observations = []
    for i, r in enumerate(rows):
        try:
            m = metric_key(r.get("metric", ""))
            if not m:
                warnings.append(f"Row {i+1}: unsupported metric; not imported")
                continue
            unit = canonical_unit(m, r.get("unit", ""))
            span = str(r.get("source_span") or f"{r.get('metric')}, {r.get('value')}, {r.get('unit')}, {r.get('date')}")[:800]
            o = Observation(id=f"{sid}-{i}", metric=m, value=r["value"], unit=unit, date=r["date"], source_id=sid, source_span=span, page=r.get("page"))
            issued = r.get('reported_at')
            if issued:
                o.reported_at_raw = str(issued)[:120]
                try:
                    o.reported_at = datetime.fromisoformat(instant(issued).replace("Z", "+00:00"))
                    if datetime.fromisoformat(str(issued).replace('Z', '+00:00')).date() < o.date:
                        warnings.append(f'Row {i+1}: report issue date appears earlier than the measurement date; retained for review')
                except (ValueError, TypeError):
                    warnings.append(f'Row {i+1}: report issue time lacks a valid offset-aware timestamp; original text retained, time unknown')
            if r.get('available_at'):
                warnings.append(f'Row {i+1}: uploaded availability is not authority; Modus stamps availability at review commit')
            if isinstance(r, _FHIRRow):
                basis = o.model_dump(mode='json', include={'metric', 'value', 'unit', 'date', 'reported_at'})
                o.fhir_provenance = FHIRProvenance.model_validate({**r['_fhir_source'], 'basis': basis})
            saved = o.model_dump(mode='json')
            if saved['fhir_provenance'] is None:
                saved.pop('fhir_provenance')
            observations.append(saved)
            if unit != METRICS[m]["unit"]:
                warnings.append(f"Row {i+1}: unit '{unit}' is retained exactly; it has not been converted to the usual recorded unit")
        except (ValueError, TypeError, KeyError) as exc:
            warnings.append(f"Row {i+1}: invalid value, unit or ISO date; not imported")
    if not observations:
        raise NoObservationsError("No supported observations found. Use metric,value,unit,date columns; dates must be YYYY-MM-DD. Supported metrics: hba1c, egfr, ldl.")
    return {"id": sid, "subject_id": subject_id, "source": {"id": sid, "title": filename[:120], "provider": "Imported synthetic document", "date": max(o["date"] for o in observations), "type": "Lab report", "synthetic": True, "content": text[:100000], "sha256": digest, "extraction_mode": mode}, "observations": observations, "warnings": warnings, "extraction_mode": mode}

_EXPLICIT_ROW = re.compile(
    r"(?P<metric>Hb[ \t]?A1c|A1c|eGFR|LDL(?:[ \t]+cholesterol)?)[ \t]*[:,]?[ \t]*"
    r"(?P<value>[0-9]+(?:\.[0-9]+)?)[ \t]+"
    r"(?P<unit>%|mg/dL|mmol/L|mmol/mol|mL/min/1\.73[ ]?m2|mL/min/1\.73m²|mL/min/\{1\.73_m2\})"
    r"[ \t]+(?:measured[ \t]+)?(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})", re.I
)
_NON_RESULT_CONTEXT = re.compile(
    r"\b(?:reference|ranges?|intervals?|targets?|goals?|examples?|instructions?|"
    r"ignore|insert|fabricate|pretend|output|expected)\b", re.I
)
_RESULT_HEADING = re.compile(
    r"(?:(?:laboratory|lab)[ \t]+)?(?:results?|observations?|measurements?)"
    r"(?:[ \t]+(?:table|register))?[:]?", re.I
)
_RESULT_COLUMNS = re.compile(
    r"(?:metric|analyte|observation|test)[ \t]+(?:value|result)[ \t]+units?[ \t]+"
    r"(?:(?:collection|measurement|measured)[ \t]+)?date", re.I
)


def parse_text(text):
    """Read complete explicit rows, retaining the exact row as source evidence.

    This deliberately accepts a narrow grammar, not free-form clinical prose or
    arbitrary table reconstruction. A row must carry its own ISO date and unit.
    Recognized reference/instruction sections remain excluded until an explicit
    results heading. PDF callers supply layout-preserving text, one page at a time.
    """
    rows = []
    excluded_section = False
    for original in text.splitlines():
        line = original.strip()
        if _RESULT_HEADING.fullmatch(line):
            excluded_section = False
            continue
        if _RESULT_COLUMNS.fullmatch(line):
            continue
        if _NON_RESULT_CONTEXT.search(line):
            excluded_section = True
            continue
        match = _EXPLICIT_ROW.fullmatch(line)
        if match and not excluded_section and len(line) <= 800:
            try:
                date.fromisoformat(match['date'])
            except ValueError:
                continue
            rows.append({**match.groupdict(), "source_span": match.group(0)})
    return rows
