"""Independent linked-field/span extraction comparison; no API calls by default."""
import asyncio
import json
from benchmark_cli import arguments, plan_run
from benchmark_common import safe_path, verify_files
from benchmark_grading import grade_document
from benchmark_runner import execute_schedule
from modus.ingest import make_draft, NoObservationsError
from modus.extraction import extract_document
from modus_entry.runtime import execution_context


class UnsupportedFormat(ValueError):
    pass


async def main(argv=None):
    args = arguments('documents', ('local_parser', 'meta_direct', 'local_hybrid'), argv)
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
