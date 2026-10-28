"""Deterministic drafts for a whole record, with verbatim text as the fallback.

This does not infer clinical facts from prose. Explicit CSV fields can describe
any supported record kind; other text remains editable, source-linked text.
"""
import csv
from collections import Counter
from hashlib import sha256
import io
from pathlib import Path

from pypdf import PdfReader

from .ingest import make_draft, parse_text, metric_key, NoObservationsError, validate_document
from .record_document_input import _has_page_images

KINDS = {'measurement', 'encounter', 'recorded_diagnosis', 'procedure',
         'prescription', 'vaccination', 'imaging_text', 'recorded_text'}
MAX_FACTS = 200


def empty_draft(filename, raw, mode='local-text'):
    digest = sha256(raw).hexdigest()
    sid = 'import-' + digest[:20]
    return {'id': sid, 'subject_id': None, 'source': {
        'id': sid, 'title': filename[:120], 'provider': 'Imported synthetic document',
        'date': '', 'type': 'Document', 'synthetic': True, 'content': '',
        'sha256': digest, 'extraction_mode': mode}, 'observations': [],
        'warnings': [], 'extraction_mode': mode}


def fact(label, value, *, kind='recorded_text', unit=None, occurred_on=None,
         facility=None, quote, page=None, extractor='local-text'):
    if kind not in KINDS:
        raise ValueError('Unsupported recorded fact kind')
    for text, limit in ((label, 200), (value, 800), (quote, 800)):
        if not isinstance(text, str) or not text.strip() or len(text) > limit:
            raise ValueError('A recorded field exceeds the draft limits')
    for text, limit in ((unit, 80), (occurred_on, 100), (facility, 200)):
        if text is not None and (not isinstance(text, str) or not text.strip() or len(text) > limit):
            raise ValueError('Use a bounded value or leave the field unknown')
    return {'kind': kind, 'label': label, 'value': value, 'unit': unit,
        'occurred_on': occurred_on, 'facility': facility, 'source_quote': quote,
        'page': page, 'bbox': None, 'model_confidence': None,
        'extractor': extractor, 'review_reasons': []}


def _text_facts(pages, extractor):
    facts = []
    for page in pages:
        number, text = page['page'], page['text']
        if len(text) > 100000:
            raise ValueError('Page text exceeds the local reader limit')
        # Existing narrow grammar is explicit and tested. Everything else is
        # retained as text, not guessed from a name or a clinical keyword.
        recognized = parse_text(text)
        parsed_counts = Counter(row['source_span'] for row in recognized)
        lines = text.splitlines(keepends=True)
        line_counts = Counter(line.strip() for line in lines)
        for row in recognized:
            facts.append(fact(row['metric'], row['value'], kind='measurement',
                unit=row['unit'], occurred_on=row['date'], quote=row['source_span'],
                page=number, extractor=extractor))
            if len(facts) > MAX_FACTS:
                raise ValueError('Split this document into batches of at most 200 fields')
        # If the same row also appears in a reference/instruction section, keep
        # all its text occurrences rather than deleting an ambiguous occurrence.
        remaining = ''.join(line for line in lines if not (
            parsed_counts[line.strip()] and parsed_counts[line.strip()] == line_counts[line.strip()]))
        # Split by exact character offsets. No page content is silently omitted.
        for offset in range(0, len(remaining), 800):
            chunk = remaining[offset:offset + 800]
            if chunk.strip():
                facts.append(fact(f'Page {number} text' if number else 'Document text', chunk,
                    quote=chunk, page=number, extractor=extractor))
                if len(facts) > MAX_FACTS:
                    raise ValueError('Split this document into batches of at most 200 fields')
    return facts


def _csv_facts(raw):
    text = raw.decode('utf-8-sig')
    stream = io.StringIO(text, newline='')
    reader = csv.DictReader(stream)
    if reader.fieldnames and len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError('CSV column names must be distinct')
    known_columns = {'kind', 'label', 'metric', 'value', 'unit', 'occurred_on', 'date', 'facility', 'reported_at', 'available_at'}
    if not reader.fieldnames or not {'value'} <= set(reader.fieldnames) or not {'label', 'metric'} & set(reader.fieldnames):
        # An unfamiliar table remains a document rather than a guessed panel.
        return _text_facts([{'page': None, 'text': text}], 'local-csv-text')
    if set(reader.fieldnames) - known_columns:
        return _text_facts([{'page': None, 'text': text}], 'local-csv-text')
    lines = text.splitlines(keepends=True)
    last_line = 1
    facts = []
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError('CSV rows must match their header')
        for left, right in (('label', 'metric'), ('occurred_on', 'date')):
            if row.get(left) and row.get(right) and row[left] != row[right]:
                raise ValueError('CSV alias columns disagree; keep one unambiguous value')
        quote = ''.join(lines[last_line:reader.line_num]).rstrip('\r\n')
        last_line = reader.line_num
        facts.append(fact(row.get('label') or row.get('metric'), row['value'],
            kind=row.get('kind') or 'measurement', unit=row.get('unit') or None,
            occurred_on=row.get('occurred_on') or row.get('date') or None,
            facility=row.get('facility') or None, quote=quote, extractor='local-csv'))
        facts[-1]['reported_at_raw'] = row.get('reported_at') or None
        if len(facts) > MAX_FACTS:
            raise ValueError('Split this document into batches of at most 200 fields')
    return facts


def attach_facts(draft, facts):
    if not facts or len(facts) > MAX_FACTS:
        raise ValueError('Use a document with 1 to 200 reviewable fields or text excerpts')
    draft['facts'] = [{**row, 'id': f"{draft['id']}-fact-{index}"} for index, row in enumerate(facts)]
    return draft


def make_history_draft(filename, raw, *, ocr_pages=None):
    validate_document(raw, filename)
    suffix = Path(filename).suffix.lower()
    mode = 'local-teleocr' if ocr_pages is not None else 'local'
    if ocr_pages is not None:
        facts = _text_facts(ocr_pages, 'local-teleocr')
    elif suffix == '.csv':
        facts = _csv_facts(raw)
    elif suffix == '.txt':
        facts = _text_facts([{'page': None, 'text': raw.decode('utf-8-sig')}], 'local-text')
    elif suffix == '.pdf':
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted or len(reader.pages) > 30:
            raise ValueError('Use an unencrypted PDF with at most 30 pages')
        if any(_has_page_images(page) for page in reader.pages):
            raise ValueError('This PDF includes images. Choose local OCR or Meta to retain all page content.')
        pages = [{'page': n, 'text': p.extract_text(extraction_mode='layout', layout_mode_space_vertically=False) or ''}
                 for n, p in enumerate(reader.pages, 1)]
        if any(not p['text'].strip() for p in pages):
            raise ValueError('This PDF has pages without readable text. Choose local OCR or Meta to retain every page.')
        facts = _text_facts(pages, 'local-pdf-text')
    else:
        raise ValueError('Use CSV, text, PDF, or an available image reader')
    draft = empty_draft(filename, raw, mode)
    # Preserve the legacy projection for old clients; the current UI commits all
    # generic facts in one transaction, never both endpoints for one draft.
    rows = []
    for row in facts:
        if row['kind'] == 'measurement' and metric_key(row['label']):
            rows.append({'metric': row['label'], 'value': row['value'], 'unit': row['unit'],
                'date': row['occurred_on'], 'source_span': row['source_quote'], 'page': row['page'],
                'reported_at': row.get('reported_at_raw')})
    if rows:
        try:
            legacy = make_draft(filename, raw, rows, extraction_mode='local-teleocr')
            draft.update(observations=legacy['observations'])
            draft['source'].update(date=legacy['source']['date'])
        except NoObservationsError:
            pass
    return attach_facts(draft, facts)
