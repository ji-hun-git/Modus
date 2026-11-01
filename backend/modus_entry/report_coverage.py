"""Public processing metadata, never document text or provider error payloads."""


def public_coverage(value):
    if not isinstance(value, dict) or value.get('version') != 'whole-report-v1':
        return None
    count = value.get('page_count')
    rows = value.get('pages')
    if type(count) is not int or not 1 <= count <= 12 or not isinstance(rows, list) or len(rows) != count:
        return None
    pages = []
    for number, row in enumerate(rows, 1):
        if not isinstance(row, dict) or type(row.get('page')) is not int or row['page'] != number:
            return None
        if not isinstance(row.get('status'), str) or row['status'] not in {'not_run', 'processed', 'no_fields', 'failed'}:
            return None
        if not isinstance(row.get('verification_status'), str) or row['verification_status'] not in {'not_run', 'completed', 'unavailable'}:
            return None
        if not isinstance(row.get('readability'), str) or row['readability'] not in {'text_available', 'image_only', 'unreadable'}:
            return None
        if type(row.get('field_count')) is not int or not 0 <= row['field_count'] <= 200:
            return None
        if any(type(row.get(key)) is not bool for key in ('text_available', 'vision_supplied')):
            return None
        pages.append({key: row[key] for key in ('page', 'status', 'field_count', 'verification_status',
                                               'readability', 'text_available', 'vision_supplied')})
    requests = value.get('request_count')
    status = value.get('status')
    if type(requests) is not int or not 0 <= requests <= 8 or not isinstance(status, str) or status not in {'completed', 'failed'}:
        return None
    processed = sum(row['status'] in {'processed', 'no_fields'} for row in pages)
    if status == 'completed' and processed != count:
        return None
    return {'version': 'whole-report-v1', 'status': status, 'completeness': 'not_established',
            'page_count': count, 'processed_pages': processed, 'pages_per_group': 3,
            'max_provider_calls': 8, 'request_count': requests, 'pages': pages}


def extraction_failure_detail(message, telemetry):
    coverage = public_coverage(telemetry.get('report_coverage'))
    return {'message': message, 'report_coverage': coverage} if coverage else message
