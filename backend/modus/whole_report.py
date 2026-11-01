"""Bounded page groups and processing coverage, never a completeness claim."""
from .record_document_input import MAX_PAGES
from .history_ingest import MAX_FACTS

PAGES_PER_GROUP = 3
MAX_PROVIDER_CALLS = 2 * ((MAX_PAGES + PAGES_PER_GROUP - 1) // PAGES_PER_GROUP)
MAX_REPORT_FIELDS = MAX_FACTS


def plan_report(prepared):
    pages = prepared['pages']
    numbers = [page['page'] for page in pages]
    if not 1 <= len(pages) <= MAX_PAGES or numbers != list(range(1, len(pages) + 1)):
        raise ValueError('Prepared report pages must be consecutive and bounded')
    if len(pages) <= PAGES_PER_GROUP:
        groups = [{'pages': numbers, 'parts': prepared['parts']}]
    else:
        page_parts = prepared.get('page_parts', [])
        if [item.get('page') for item in page_parts] != numbers:
            raise ValueError('Prepared report needs an exact part list for every page')
        if any(not isinstance(item.get('parts'), list) or not item['parts'] for item in page_parts):
            raise ValueError('Prepared report has missing page input')
        groups = [{'pages': numbers[offset:offset + PAGES_PER_GROUP],
                   'parts': [part for item in page_parts[offset:offset + PAGES_PER_GROUP]
                             for part in item['parts']]}
                  for offset in range(0, len(pages), PAGES_PER_GROUP)]
    metadata = {page['page']: page for page in prepared['metadata'].get('pages', [])}
    coverage = {'version': 'whole-report-v1', 'status': 'completed',
        'completeness': 'not_established', 'page_count': len(pages), 'processed_pages': 0,
        'pages_per_group': PAGES_PER_GROUP, 'max_provider_calls': MAX_PROVIDER_CALLS,
        'request_count': 0, 'groups': [], 'pages': []}
    for index, group in enumerate(groups, 1):
        coverage['groups'].append({'group': index, 'pages': group['pages'],
            'extraction_status': 'not_run', 'verification_status': 'not_run',
            'field_count': 0, 'error_kind': None})
    for page in pages:
        text = bool(page['text'].strip() or page.get('ocr_text', '').strip())
        image = metadata.get(page['page'], {}).get('vision_supplied', False) is True
        coverage['pages'].append({'page': page['page'], 'status': 'not_run',
            'text_available': text, 'vision_supplied': image,
            'readability': 'text_available' if text else 'image_only' if image else 'unreadable',
            'field_count': 0, 'verification_status': 'not_run'})
    return groups, coverage


def finish_group(coverage, group_index, fields, verification_status, error_kind=None):
    group = coverage['groups'][group_index]
    group.update(extraction_status='completed', verification_status=verification_status,
                 field_count=len(fields), error_kind=error_kind)
    for number in group['pages']:
        page = coverage['pages'][number - 1]
        count = sum(field['page'] == number for field in fields)
        page.update(status='processed' if count else 'no_fields', field_count=count,
                    verification_status=verification_status if count else 'not_run')
    coverage['processed_pages'] = sum(page['status'] in {'processed', 'no_fields'}
                                      for page in coverage['pages'])


def fail_group(coverage, group_index, kind):
    coverage['status'] = 'failed'
    group = coverage['groups'][group_index]
    group.update(extraction_status='failed', error_kind=kind)
    for number in group['pages']:
        coverage['pages'][number - 1]['status'] = 'failed'
