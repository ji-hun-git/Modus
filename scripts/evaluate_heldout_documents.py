"""Independent linked-field/span extraction comparison; no API calls by default."""
import asyncio
from collections import Counter
import json
from benchmark_cli import arguments, plan_run
from benchmark_common import safe_path, verify_files
from benchmark_grading import grade_document
from benchmark_runner import execute_schedule
from modus.ingest import make_draft, NoObservationsError
from modus.extraction import extract_document
from modus.record_extraction import extract_record_document
from modus_entry.document_guard import screen_untrusted
from modus_entry.extraction_review import review_draft
from modus_entry.runtime import execution_context

METHODS = ('local_parser', 'meta_direct', 'meta_record_review', 'local_hybrid')


class UnsupportedFormat(ValueError):
    pass


async def meta_record_review(raw, filename, mime, model, request):
    """Current production producer, scored only on the legacy three-metric view.

    This calls the actual extraction and review projection, without a store,
    commit, human correction or hidden repair. Local OCR is deliberately disabled
    rather than environment-dependent. A failed verifier preserves its explicit
    unavailable status and original draft, just as production does.
    """
    telemetry = {'execution': execution_context('meta-extraction', model)}
    extracted = await extract_record_document(raw, filename, mime, telemetry,
        request=request, use_local_ocr=False, screen_document=screen_untrusted)
    draft = review_draft(filename, raw, extracted)
    fields = extracted['fields']
    return {'mode': 'meta-record-review', 'observations': draft['observations'],
        'telemetry': telemetry, 'verification': extracted['verification'],
        'fields': fields, 'extraction_review': draft['extraction_review'],
        'document_guard': extracted.get('document_guard'),
        'extraction': extracted['extraction'], 'warnings': draft.get('warnings', []),
        'benchmark_scope': {
            'scored_projection': 'compatible hba1c/egfr/ldl observations only',
            'generic_field_count': len(fields),
            'field_kinds': dict(Counter(field['kind'] for field in fields)),
            'fields_outside_scored_projection': sum(field['observation_index'] is None for field in fields),
            'verification_statuses': dict(Counter(field['verification']['status'] for field in fields)),
            'local_support_statuses': dict(Counter(field['local_support']['status'] for field in fields)),
            'max_provider_calls': 2, 'local_ocr_enabled': False,
            'review_required': True, 'human_review_performed': False, 'records_written': 0,
            'limitation': 'Generic fields and verification checks are retained but have no gold accuracy score in this legacy corpus.'}}


async def main(argv=None):
    args = arguments('documents', METHODS, argv)
    plan, data, folder, public_plan = plan_run(args, 'documents')
    if folder is None:
        print(json.dumps(public_plan, indent=2))
        return 0
    cases = {case['id']: case for case in data['cases']}
    async def execute(spec, request):
        case = cases[spec['case_id']]
        path = safe_path(args.suite, case['file'])
        if spec['method'] == 'local_parser' and case['mime'] != 'application/pdf':
            raise UnsupportedFormat('Local parser does not support this image format')
        if spec['method'] == 'meta_record_review':
            result = await meta_record_review(path.read_bytes(), path.name, case['mime'], plan['model'], request)
            grade = grade_document(case, result['observations'])
            grade['verification_status'] = result['verification']['status']
            grade['scored_projection'] = result['benchmark_scope']['scored_projection']
            return result, grade
        telemetry = {}
        rows = None
        if spec['method'] == 'local_hybrid' and case['mime'] != 'application/pdf':
            # Explicit opt-in local model; no provider call, no reuse of gold or
            # cached OCR output. Each scheduled trial performs actual inference.
            from modus.local_ocr import extract_document as local_extract
            extracted = await asyncio.to_thread(local_extract, path.read_bytes(), path.name)
            predicted = extracted['observations']
            return {'mode': 'local-teleocr', 'observations': predicted,
                'telemetry': extracted['telemetry']}, grade_document(case, predicted)
        if spec['method'] == 'meta_direct':
            telemetry['execution'] = execution_context('meta-extraction', plan['model'])
            rows = await extract_document(path.read_bytes(), path.name, case['mime'], telemetry, request=request)
        try:
            draft = make_draft(path.name, path.read_bytes(), rows)
            predicted = draft['observations']
        except NoObservationsError:
            predicted = []
        return {'mode': 'local deterministic parser' if spec['method'] in {'local_parser', 'local_hybrid'} else 'meta',
            'observations': predicted, 'telemetry': telemetry}, grade_document(case, predicted)
    report = await execute_schedule(plan, folder, execute, verify=lambda: verify_files(args.suite, plan['dataset_files_sha256']))
    print(json.dumps({'results': str(folder), **report}, indent=2))
    return 0 if report['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
