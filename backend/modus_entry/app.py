"""Independent record surface. Broad Modus app/tools/seed are never imported."""
import json
import os
import asyncio
from hashlib import sha256
from datetime import date
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import AwareDatetime
from modus.record_store import RecordStore
from modus.ingest import make_draft, MAX_BYTES, NoObservationsError
from modus.history_ingest import make_history_draft
from modus.record_history import commit_history, history_view, get_profile, update_profile
from modus.provider import provider_status
from modus.record_extraction import extract_record_document
from modus import local_ocr
from .models import RELEASE, CompareRequest, ChatRequest, HistoryChatRequest, ExportRequest, CommitRequest, HistoryCommitRequest, ProfileRequest
from .seed import initial_data
from .runtime import ROOT, BUNDLE_ID, ENVIRONMENT, execution_context
from .tools import capture, source, observation
from . import agent
from . import history_agent
from .history_tools import capture_history
from .extraction_review import review_draft

load_dotenv(ROOT / '.env')
CHANGE_FIELDS = {'id', 'created_at', 'kind', 'status', 'draft_id', 'source_id', 'available_at',
                 'observation_ids', 'fact_count', 'scope', 'comparison', 'message', 'answer', 'mode', 'error', 'execution', 'telemetry'}


def projection(value, fields):
    return {k: value[k] for k in fields if k in value and isinstance(value[k], (str, int, float, bool, type(None)))} if isinstance(value, dict) else {}


def projected_execution(value):
    clean = projection(value, ('run_id', 'bundle_id', 'config_id', 'started_at', 'mode', 'requested_model', 'model_version_basis'))
    if isinstance(value, dict) and isinstance(value.get('runtime'), dict):
        runtime = projection(value['runtime'], ('python', 'platform'))
        runtime['dependencies'] = projection(value['runtime'].get('dependencies'), ENVIRONMENT['dependencies'].keys())
        clean['runtime'] = runtime
    return clean


def projected_telemetry(value):
    if not isinstance(value, dict):
        return {}
    clean = {'execution': projected_execution(value.get('execution')), 'usage': projection(value.get('usage'), ('prompt_tokens', 'completion_tokens', 'total_tokens'))}
    clean['calls'] = []
    for call in value.get('calls', [])[:14] if isinstance(value.get('calls'), list) else []:
        item = projection(call, ('model', 'returned_model', 'status', 'duration_ms', 'run_id', 'bundle_id', 'config_id',
                                 'response_id', 'request_id', 'http_status', 'finish_reason', 'error_kind', 'stage', 'result_validation'))
        item['usage'] = projection(call.get('usage'), ('prompt_tokens', 'completion_tokens', 'total_tokens')) if isinstance(call, dict) and call.get('usage') is not None else None
        clean['calls'].append(item)
    if value.get('mode') == 'local-teleocr':
        clean.update(projection(value, ('mode', 'model', 'revision', 'status', 'input_tokens', 'output_tokens', 'usage_verified', 'duration_ms')))
        clean['local_attempts'] = []
        for attempt in value.get('attempts', [])[:2] if isinstance(value.get('attempts'), list) else []:
            item = projection(attempt, ('attempt', 'resolution', 'status', 'input_tokens', 'output_tokens', 'usage_verified', 'duration_ms', 'timeout_seconds'))
            if isinstance(attempt, dict):
                item['diagnostic'] = projection(attempt.get('diagnostic'), ('kind', 'status', 'page_count'))
                item['settings'] = projection(attempt.get('settings'), ('max_pixels', 'prompt_version', 'strategy_version', 'repetition_penalty'))
            clean['local_attempts'].append(item)
    return clean


def projected_change(row):
    clean = projection(row, CHANGE_FIELDS - {'scope', 'comparison', 'execution', 'telemetry', 'observation_ids'})
    if 'scope' in row:
        clean['scope'] = projection(row['scope'], ('as_of', 'known_at', 'captured_at', 'scope_id'))
    if isinstance(row.get('comparison'), dict):
        clean['comparison'] = {key: projection(row['comparison'].get(key), ('as_of', 'known_at', 'captured_at', 'scope_id')) for key in ('before', 'after')}
    if 'execution' in row:
        clean['execution'] = projected_execution(row['execution'])
    if 'telemetry' in row:
        clean['telemetry'] = projected_telemetry(row['telemetry'])
    if isinstance(row.get('observation_ids'), list):
        clean['observation_ids'] = [key for key in row['observation_ids'] if isinstance(key, str)]
    return clean


def attachment(document):
    return Response(document['raw'], media_type=document['mime'], headers={
        'Content-Disposition': "attachment; filename*=UTF-8''" + quote(document['filename'], safe=''),
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store',
        'Content-Security-Policy': "sandbox; default-src 'none'"})


def preview_response(saved, *, reused=False):
    warnings = list(saved.get('warnings', []))
    if reused:
        warnings.append('Existing review reopened. This file was not read again.')
    return {'id': saved['id'], 'source': source(saved['source']),
        'observations': [observation(o) for o in saved['observations']], 'warnings': warnings,
        'extraction_mode': saved['extraction_mode'], 'already_committed': saved['already_committed'],
        **({'facts': saved['facts']} if 'facts' in saved else {}),
        **({'extraction_review': saved['extraction_review']} if 'extraction_review' in saved else {})}


def create_entry_app(database=None, clock=None):
    app = FastAPI(title='Modus Records', version=RELEASE,
        description='Synthetic record reconciliation and availability replay. Contest eligibility remains unconfirmed.')
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
    app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5174', 'http://localhost:5174'], allow_methods=['GET', 'POST', 'PUT'], allow_headers=['Content-Type'])
    def commit_event(receipt):
        return {'schema': 'modus-entry-change-v1', 'kind': 'import', 'status': 'completed', 'mode': 'deterministic',
            **{k: receipt[k] for k in ('draft_id', 'source_id', 'available_at', 'observation_ids')},
            **({'fact_count': len(receipt['fact_ids'])} if 'fact_ids' in receipt else {})}
    store = RecordStore(database or os.getenv('MODUS_ENTRY_DB_PATH') or ROOT / 'data/entry.db', seed_provider=initial_data,
        commit_event_factory=commit_event, **({'clock': clock} if clock else {}))
    app.state.store = store
    preview_lock = asyncio.Lock()

    def recorded_run(kind, **fields):
        return store.save_run({'schema': 'modus-entry-change-v1', 'kind': kind, **fields})

    def captured(as_of, known_at=None, compare_from=None):
        try:
            return capture(store, as_of.isoformat(), known_at, compare_from)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.get('/api/health')
    def health():
        return {'application': 'modus-records', 'release': RELEASE, 'bundle_id': BUNDLE_ID, 'synthetic_only': True, 'provider': provider_status(), 'local_ocr': local_ocr.status()}

    @app.get('/api/records/view')
    def records_view(as_of: date, known_at: AwareDatetime | None = None):
        return captured(as_of, known_at)['view']

    @app.get('/api/history/view')
    def lifelong_history(as_of: date | None = None, known_at: AwareDatetime | None = None):
        return history_view(store, as_of.isoformat() if as_of else None, known_at)

    @app.post('/api/history/commit')
    def save_history(request: HistoryCommitRequest):
        try:
            receipt = commit_history(store, request.draft_id,
                [row.model_dump() for row in request.reviewed_facts])
            return {**receipt, 'bundle_id': BUNDLE_ID}
        except ValueError as error:
            raise HTTPException(404 if str(error) == 'Draft not found' else 422, str(error)) from None

    @app.get('/api/history/sources/{source_id}/original')
    def history_original(source_id: str, known_at: AwareDatetime, as_of: date | None = None):
        view = history_view(store, as_of.isoformat() if as_of else None, known_at)
        if not any(s['id'] == source_id and s.get('original_available') for s in view['sources']):
            raise HTTPException(404, 'Original is unavailable in this history scope')
        document = store.document(source_id)
        if document is None:
            raise HTTPException(404, 'Original is unavailable')
        return attachment(document)

    @app.get('/api/profile')
    def profile(known_at: AwareDatetime | None = None):
        return get_profile(store, known_at)

    @app.put('/api/profile')
    def save_profile(request: ProfileRequest):
        try:
            return update_profile(store, request.date_of_birth)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post('/api/records/compare')
    def compare(request: CompareRequest):
        return captured(request.as_of, request.after_known_at, request.before_known_at)['comparison']

    @app.post('/api/imports/preview')
    async def preview(file: UploadFile = File(...), synthetic_confirmed: bool = Form(False), use_meta: bool = Form(False), use_local_ocr: bool = Form(False)):
        # A single local profile has one active reader. The content-hash check
        # below then prevents simultaneous duplicate requests spending twice.
        async with preview_lock:
            return await read_preview(file, synthetic_confirmed, use_meta, use_local_ocr)

    async def read_preview(file, synthetic_confirmed, use_meta, use_local_ocr):
        if not synthetic_confirmed:
            raise HTTPException(400, 'Confirm that this file contains only synthetic example data')
        if use_meta and use_local_ocr:
            raise HTTPException(422, 'Choose one extraction method')
        raw = await file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise HTTPException(413, 'Maximum file size is 8 MB')
        name = Path((file.filename or 'upload').replace('\\', '/')).name
        extension = name.rsplit('.', 1)[-1].lower()
        if extension not in {'csv', 'txt', 'pdf', 'png', 'jpg', 'jpeg'}:
            raise HTTPException(422, 'Use a synthetic CSV, text, PDF, PNG or JPEG document')
        mime = {'csv': 'text/csv', 'txt': 'text/plain', 'pdf': 'application/pdf', 'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}[extension]
        existing = store.draft('import-' + sha256(raw).hexdigest()[:20])
        if existing is not None:
            # Existing review state wins; do not bill for an extraction whose
            # proposal INSERT OR IGNORE would silently discard.
            return preview_response(existing, reused=True)
        telemetry = {}
        mode = 'local-teleocr' if use_local_ocr else 'meta' if use_meta else 'local'
        try:
            extracted = None
            if use_local_ocr:
                telemetry['execution'] = execution_context('local-teleocr', local_ocr.status().get('model'))
                telemetry['execution']['model_version_basis'] = 'configured pinned local checkpoint; worker verifies integrity before inference'
                draft = await run_in_threadpool(local_ocr.make_local_history_draft, raw, name)
                telemetry.update(draft.pop('telemetry', {}))
            elif use_meta:
                if provider_status()['mode'] != 'meta':
                    raise ValueError('Enable the Meta provider before requesting model extraction')
                telemetry['execution'] = execution_context('meta-extraction', provider_status()['model'])
                extracted = await extract_record_document(raw, name, mime, telemetry,
                    use_local_ocr=local_ocr.status().get('available', False))
                draft = review_draft(name, raw, extracted)
            else:
                draft = make_history_draft(name, raw)
            if telemetry:
                draft['source']['extraction_telemetry'] = telemetry
            saved = store.add_draft(draft, raw=raw, filename=name, mime=mime)
            if use_meta:
                recorded_run('extraction', status='review_required', draft_id=saved['id'], mode=mode,
                    message='A draft was read. No measurements were saved.',
                    execution=telemetry.get('execution'), telemetry=telemetry)
            return preview_response(saved)
        except local_ocr.LocalOCRError as error:
            telemetry.update(getattr(error, 'telemetry', None) or {})
            recorded_run('extraction_failure', status='failed', mode=mode, error='Local OCR failed; no draft was accepted.', execution=telemetry.get('execution'), telemetry=telemetry)
            raise HTTPException(422, 'Local OCR is unavailable, busy or did not complete. No draft was accepted and no alternate provider was used.') from None
        except RuntimeError:
            recorded_run('extraction_failure', status='failed', mode=mode, error='Model extraction failed; no draft was accepted.', execution=telemetry.get('execution'), telemetry=telemetry)
            raise HTTPException(502, 'Model extraction failed; no draft was accepted. No local fallback was used.') from None
        except (ValueError, KeyError, TypeError) as error:
            if use_local_ocr:
                telemetry.update(getattr(error, 'telemetry', None) or {})
            if telemetry:
                recorded_run('extraction_failure', status='failed', mode=mode, error='No usable validated extraction was accepted.', execution=telemetry.get('execution'), telemetry=telemetry)
            raise HTTPException(422, 'No usable validated rows were accepted. Check explicit dates, values and units, or choose a supported extraction mode.') from None
        except Exception:
            raise HTTPException(422, 'Unable to read this synthetic document; no draft was accepted.') from None

    @app.get('/api/drafts/{draft_id}/original')
    def draft_original(draft_id: str):
        draft = store.draft(draft_id)
        if draft is None or draft.get('already_committed'):
            raise HTTPException(404, 'Uncommitted draft original is unavailable; use the scoped records route after adding')
        document = store.document(draft_id)
        if document is None:
            raise HTTPException(404, 'Original is unavailable')
        return attachment(document)

    @app.post('/api/imports/commit')
    def commit(request: CommitRequest):
        try:
            saved = store.commit_draft(request.draft_id, [o.model_dump(mode='json') for o in request.reviewed_observations])
        except ValueError as error:
            raise HTTPException(404 if str(error) == 'Draft not found' else 422, str(error)) from error
        payload = {k: saved[k] for k in ('draft_id', 'source_id', 'inserted', 'duplicate', 'available_at', 'observation_ids')}
        return {**payload, 'bundle_id': BUNDLE_ID}

    @app.get('/api/records/{source_id}/original')
    def record_original(source_id: str, as_of: date, known_at: AwareDatetime):
        result = captured(as_of, known_at)['view']
        if not any(s['id'] == source_id and s['original_available'] for s in result['sources']):
            raise HTTPException(404, 'Original is unavailable in this evidence scope')
        document = store.document(source_id)
        if document is None:
            raise HTTPException(404, 'Original is unavailable')
        return attachment(document)

    @app.post('/api/agent/chat')
    async def chat(request: ChatRequest):
        context = captured(request.as_of, request.known_at, request.compare_from)
        telemetry = {}
        try:
            response = await agent.live_chat(context, request.message, telemetry) if provider_status()['mode'] == 'meta' else agent.offline_chat(context, request.message)
            recorded_run('question', status='completed', message=request.message, scope=response['scope'],
                comparison=response.get('comparison'), answer=response['answer'], mode=response['mode'], execution=response['execution'], telemetry=response.get('telemetry', {}))
            return response
        except Exception:
            recorded_run('question', status='failed', scope=context['view']['scope'], mode='meta',
                error='No validated record answer was produced.', execution=telemetry.get('execution'), telemetry=telemetry)
            raise HTTPException(502, 'The record agent could not complete a validated response. No records changed and no local fallback was used.') from None

    @app.post('/api/history/chat')
    async def history_chat(request: HistoryChatRequest):
        try:
            context = await run_in_threadpool(capture_history, store,
                request.as_of.isoformat() if request.as_of else None,
                request.known_at, request.compare_from)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        telemetry = {}
        try:
            response = (await history_agent.live_chat(context, request.message, telemetry)
                if provider_status()['mode'] == 'meta' else history_agent.offline_chat(context, request.message))
            recorded_run('question', status='completed' if response['claims'] else 'abstained',
                message=request.message, scope=response['scope'],
                comparison=response.get('history_comparison'), answer=response['answer'],
                mode=response['mode'], execution=response['execution'], telemetry=response.get('telemetry', {}))
            return response
        except Exception:
            recorded_run('question', status='failed', scope=context['view']['scope'], mode=provider_status()['mode'],
                error='No validated history answer was produced.', execution=telemetry.get('execution'), telemetry=telemetry)
            raise HTTPException(502, 'The history agent could not complete a validated response. No records changed and no local fallback was used.') from None

    @app.get('/api/changes')
    def changes(known_at: AwareDatetime | None = None):
        rows = store.history(known_at)
        return {'changes': [projected_change(row)
            for row in rows if row.get('schema') == 'modus-entry-change-v1'
            and row.get('kind') in {'import', 'question', 'extraction', 'extraction_failure'}]}

    @app.post('/api/records/export')
    def export(request: ExportRequest):
        context = captured(request.as_of, request.known_at, request.compare_from)
        payload = {'format': 'modus-record-export-v1', 'synthetic': True, 'bundle_id': BUNDLE_ID,
            'kind': 'comparison' if context['comparison'] is not None else 'snapshot',
            'data': context['comparison'] if context['comparison'] is not None else context['view']}
        return Response(json.dumps(payload, indent=2), media_type='application/json', headers={
            'Content-Disposition': 'attachment; filename="modus-record-evidence.json"', 'Cache-Control': 'no-store'})

    # Match unknown APIs before static serving; never answer them with a SPA page.
    @app.api_route('/api/{unknown:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'], include_in_schema=False)
    def unknown_api(unknown: str):
        raise HTTPException(404, 'Record endpoint not found')

    frontend = ROOT / 'entry/frontend/dist'
    if frontend.is_dir():
        app.mount('/', StaticFiles(directory=frontend, html=True), name='entry-frontend')
    return app


app = create_entry_app()
