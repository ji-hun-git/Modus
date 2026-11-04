"""Independent record surface. Broad Modus app/tools/seed are never imported."""
import json
import os
import asyncio
import sqlite3
import sqlcipher3
from starlette.formparsers import MultiPartParser
from hashlib import sha256
from datetime import date
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from pydantic import AwareDatetime
from modus.record_store import RecordStore
from modus.ingest import make_draft, MAX_BYTES, NoObservationsError
from modus.history_ingest import make_history_draft
from modus.record_history import commit_history, history_view, get_profile, update_profile
from modus.record_history_models import proposed_facts
from modus.record_omissions import commit_omissions, omission_review_state, OmissionConflict
from .models import OmissionCommitRequest
from modus.record_amendments import (AmendmentRequest, AmendmentCommitRequest, AmendmentConflict,
                                    preview_amendment, commit_amendment, revision_history)
from modus.provider import provider_status
from modus.record_extraction import extract_record_document
from .models import RELEASE, CompareRequest, ChatRequest, HistoryChatRequest, ExportRequest, CommitRequest, HistoryCommitRequest, ProfileRequest
from .seed import initial_data
from .runtime import ROOT, BUNDLE_ID, ENVIRONMENT, execution_context
from .tools import capture, source, observation
from . import agent
from . import history_agent
from .history_conversation import HistoryConversation
from .history_pages import HistoryPages, SnapshotExpired
from .report_summary import ReportSummaryRequest, build_report_summary
from .longitudinal_series import SeriesResponse, build_series
from .report_briefs import ReportBriefRequest, ReportBriefExportRequest, build_report_brief, validate_report_export
from .history_tools import capture_history, safe_view
from .report_investigation_tools import prepare_reports
from .report_investigation_request import ReportBounds
from .investigation import investigate, offline_investigate
from .history_compare import HistoryCompareRequest, compare_history
from .briefs import (BriefRequest, BriefExportRequest, BriefChangedError,
                     build_brief, validate_export, render_html, render_json)
from .extraction_review import review_draft
from .document_guard import screen_untrusted
from .report_coverage import public_coverage, extraction_failure_detail
from .local_security import LocalSecurityMiddleware
from .local_access import LocalAccess, access_routes

load_dotenv(ROOT / '.env')
CHANGE_FIELDS = {'id', 'created_at', 'kind', 'status', 'draft_id', 'source_id', 'available_at',
                 'observation_ids', 'fact_count', 'fact_id', 'revision_id', 'scope', 'comparison', 'message', 'answer', 'mode', 'error', 'execution', 'telemetry'}


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
    coverage = public_coverage(value.get('report_coverage'))
    if coverage:
        clean['report_coverage'] = coverage
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


def preview_response(saved, *, reused=False, store=None):
    warnings = list(saved.get('warnings', []))
    if reused and saved.get('extraction_mode') != 'authored_seed':
        warnings.append('Existing review reopened. This file was not read again.')
    return {'id': saved['id'], 'source': source(saved['source']),
        'observations': [observation(o) for o in saved['observations']], 'warnings': warnings,
        'extraction_mode': saved['extraction_mode'], 'already_committed': saved['already_committed'],
        'facts': [] if saved.get('facts') == [] else list(proposed_facts(saved).values()),
        **({'document_guard': saved['document_guard']} if 'document_guard' in saved else {}),
        **({'extraction_review': saved['extraction_review']} if 'extraction_review' in saved else {}),
        **(omission_review_state(store, saved['id']) if store is not None else {})}


def create_entry_app(database=None, clock=None):
    # The boundary rejects larger bodies before multipart parsing. Accepted
    # uploads stay in memory instead of spooling originals to plaintext OS
    # temporary files. This process serves only the bounded entry application.
    from .local_security import MAX_REQUEST_BYTES
    MultiPartParser.spool_max_size = MAX_REQUEST_BYTES
    app = FastAPI(title='Modus Records', version=RELEASE, docs_url=None, redoc_url=None, openapi_url=None,
        description='Synthetic record reconciliation and availability replay. Contest eligibility remains unconfirmed.')
    app.state.local_access = LocalAccess()
    app.add_middleware(LocalSecurityMiddleware, access=app.state.local_access)
    app.include_router(access_routes(app.state.local_access))

    @app.exception_handler(RequestValidationError)
    async def private_validation_error(request, error):
        # Input values, arbitrary extra-property names and validator context can
        # contain record text or credentials. Return error categories only.
        return JSONResponse(status_code=422, content={'detail': [
            {'type': item['type'], 'msg': 'Invalid request field.'} for item in error.errors()[:10]]})
    def commit_event(receipt):
        return {'schema': 'modus-entry-change-v1', 'kind': 'import', 'status': 'completed', 'mode': 'deterministic',
            **{k: receipt[k] for k in ('draft_id', 'source_id', 'available_at', 'observation_ids')},
            **({'fact_count': len(receipt['fact_ids'])} if 'fact_ids' in receipt else {})}
    store = RecordStore(database or os.getenv('MODUS_ENTRY_DB_PATH') or ROOT / 'data/entry.db', seed_provider=initial_data,
        commit_event_factory=commit_event, **({'clock': clock} if clock else {}))
    app.state.store = store
    conversations = HistoryConversation()
    store.history_pages = HistoryPages(store)
    preview_lock = asyncio.Lock()

    @app.exception_handler(sqlite3.OperationalError)
    @app.exception_handler(sqlcipher3.OperationalError)
    async def database_busy(request, error):
        if getattr(error, 'sqlite_errorcode', 0) & 0xff in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            return JSONResponse(status_code=503, headers={'Retry-After': '1'},
                content={'detail': 'Your records are busy. Please try again shortly.'})
        raise error

    def recorded_run(kind, **fields):
        return store.save_run({'schema': 'modus-entry-change-v1', 'kind': kind, **fields})

    def captured(as_of, known_at=None, compare_from=None):
        try:
            return capture(store, as_of.isoformat(), known_at, compare_from)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.get('/api/health')
    def health():
        return {'application': 'modus-records', 'release': RELEASE, 'bundle_id': BUNDLE_ID, 'synthetic_only': True, 'provider': provider_status(),
            'local_ocr': {'available': False, 'mode': 'disabled',
                'reason': 'Local OCR is retired from the contest entry. Model extraction uses Meta only.'}}

    @app.get('/api/records/view')
    def records_view(as_of: date, known_at: AwareDatetime | None = None):
        return captured(as_of, known_at)['view']

    @app.get('/api/history/view')
    def lifelong_history(as_of: date | None = None, known_at: AwareDatetime | None = None):
        return store.history_pages.view(as_of.isoformat() if as_of else None, known_at)

    @app.get('/api/history/page')
    def history_page(as_of: date | None = None, known_at: AwareDatetime | None = None,
                     snapshot_id: str | None = Query(None, min_length=32, max_length=32),
                     section: str = 'facts', offset: int = Query(0, ge=0, le=100000),
                     limit: int = Query(50, ge=1, le=50), kind: str | None = None,
                     label: str | None = Query(None, max_length=200), facility: str | None = Query(None, max_length=200),
                     source_id: str | None = Query(None, max_length=160), order: str = 'newest',
                     query: str = Query('', max_length=2000), conflict_id: str | None = None, through: date | None = None,
                     conflicts_only: bool = False, compare_fact_id: str | None = Query(None, max_length=160)):
        try:
            return store.history_pages.page(as_of=as_of.isoformat() if as_of else None, known_at=known_at,
                snapshot_id=snapshot_id, section=section, offset=offset, limit=limit, kind=kind, label=label,
                facility=facility, source_id=source_id, order=order, query=query, conflict_id=conflict_id,
                through=through.isoformat() if through else None, conflicts_only=conflicts_only, compare_fact_id=compare_fact_id)
        except SnapshotExpired as error:
            raise HTTPException(410, str(error)) from None
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.get('/api/history/series', response_model=SeriesResponse)
    def longitudinal_series(web_request: Request,
                            snapshot_id: str = Query(pattern=r'^[0-9a-f]{32}$'),
                            fact_id: str = Query(min_length=1, max_length=160),
                            offset: int = Query(0, ge=0, le=100000),
                            limit: int = Query(50, ge=1, le=50)):
        if len(web_request.query_params.multi_items()) != len(set(web_request.query_params)):
            raise HTTPException(422, 'Each series parameter must be supplied once.')
        if set(web_request.query_params) - {'snapshot_id', 'fact_id', 'offset', 'limit'}:
            raise HTTPException(422, 'Series scope comes from the snapshot; unsupported parameters were supplied.')
        try:
            captured = store.history_pages.get(snapshot_id)
            return build_series(captured['view'], snapshot_id, fact_id, offset, limit)
        except SnapshotExpired as error:
            raise HTTPException(409, str(error)) from None
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post('/api/history/report-summary')
    def report_summary(request: ReportSummaryRequest):
        try:
            captured = store.history_pages.get(request.snapshot_id)
            return build_report_summary(captured['view'], request)
        except SnapshotExpired as error:
            raise HTTPException(409, str(error)) from None
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post('/api/history/report-investigation')
    async def report_investigation(request: ReportSummaryRequest):
        try:
            captured = await run_in_threadpool(store.history_pages.get, request.snapshot_id)
            context = await run_in_threadpool(prepare_reports,
                {'view': safe_view(captured['view']), 'comparison': None},
                (request.selected_source_id, request.comparison_source_id), snapshot_id=request.snapshot_id)
        except SnapshotExpired as error:
            raise HTTPException(409, str(error)) from None
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        telemetry = {}
        message = 'Compare these two selected reports and inspect their recorded discrepancies.'
        try:
            response = (await investigate(context, message, ReportBounds(), telemetry)
                if provider_status()['mode'] == 'meta' else
                await run_in_threadpool(offline_investigate, context, ReportBounds()))
            response = history_agent.decorate(context, response)
            await run_in_threadpool(recorded_run, 'question', status='completed' if response['claims'] else 'abstained',
                message=message, scope=response['scope'], answer=response['answer'],
                mode=response['mode'], execution=response['execution'], telemetry=response.get('telemetry', {}))
            return response
        except Exception:
            await run_in_threadpool(recorded_run, 'question', status='failed', scope=context['view']['scope'],
                mode=provider_status()['mode'], error='No validated report investigation was produced.',
                execution=telemetry.get('execution'), telemetry=telemetry)
            raise HTTPException(502, 'The report investigation could not complete a validated answer. No records changed and no local fallback was used.') from None

    @app.post('/api/history/compare')
    def history_compare(request: HistoryCompareRequest):
        try:
            return compare_history(store, request)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post('/api/history/commit')
    def save_history(request: HistoryCommitRequest):
        try:
            receipt = commit_history(store, request.draft_id,
                [row.model_dump(exclude_unset=True) for row in request.reviewed_facts],
                reviewed_omissions=[row.model_dump() for row in request.reviewed_omissions])
            return {**receipt, 'bundle_id': BUNDLE_ID}
        except ValueError as error:
            raise HTTPException(404 if str(error) == 'Draft not found' else 422, str(error)) from None

    @app.post('/api/history/omissions/commit')
    def save_omissions(request: OmissionCommitRequest):
        try:
            return {**commit_omissions(store, request.draft_id,
                [row.model_dump() for row in request.reviewed_omissions]), 'bundle_id': BUNDLE_ID}
        except ValueError as error:
            status = 409 if isinstance(error, OmissionConflict) else 404 if str(error) == 'Draft not found' else 422
            raise HTTPException(status, str(error)) from None

    @app.get('/api/history/sources/{source_id}/original')
    def history_original(source_id: str, known_at: AwareDatetime, as_of: date | None = None):
        view = history_view(store, as_of.isoformat() if as_of else None, known_at)
        if not any(s['id'] == source_id and s.get('original_available') for s in view['sources']):
            raise HTTPException(404, 'Original is unavailable in this history scope')
        document = store.document(source_id)
        if document is None:
            raise HTTPException(404, 'Original is unavailable')
        return attachment(document)

    @app.get('/api/history/facts/{fact_id}/revisions')
    def revisions(fact_id: str, known_at: AwareDatetime | None = None, as_of: date | None = None):
        try:
            return revision_history(store, fact_id, known_at, as_of.isoformat() if as_of else None)
        except ValueError as error:
            raise HTTPException(404 if str(error) == 'Saved record not found' else 422, str(error)) from None

    @app.post('/api/history/amendments/preview')
    def amendment_preview(request: AmendmentRequest):
        try:
            return preview_amendment(store, request)
        except ValueError as error:
            raise HTTPException(409 if isinstance(error, AmendmentConflict) else 422, str(error)) from None

    @app.post('/api/history/amendments/commit')
    def amendment_commit(request: AmendmentCommitRequest):
        try:
            return {**commit_amendment(store, request), 'bundle_id': BUNDLE_ID}
        except ValueError as error:
            raise HTTPException(409 if isinstance(error, AmendmentConflict) else 422, str(error)) from None

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
    async def preview(file: UploadFile = File(...), synthetic_confirmed: bool = Form(False), use_meta: bool = Form(False), use_local_ocr: bool = Form(False), reuse_only: bool = Form(False)):
        # A single local profile has one active reader. The content-hash check
        # below then prevents simultaneous duplicate requests spending twice.
        async with preview_lock:
            return await read_preview(file, synthetic_confirmed, use_meta, use_local_ocr, reuse_only)

    async def read_preview(file, synthetic_confirmed, use_meta, use_local_ocr, reuse_only):
        if not synthetic_confirmed:
            raise HTTPException(400, 'Confirm that this file contains only synthetic example data')
        if use_local_ocr:
            raise HTTPException(422, 'Local OCR is not available in this entry. Choose Meta or the local text reader.')
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
            return preview_response(existing, reused=True, store=store)
        if reuse_only:
            # Explicitly bounded recovery: no parsing, provider check, model
            # request, new draft, or fallback when these bytes have no draft.
            raise HTTPException(404, 'No previous draft was found for this exact file. No reading was attempted.')
        telemetry = {}
        mode = 'meta' if use_meta else 'local'
        try:
            extracted = None
            if use_meta:
                if provider_status()['mode'] != 'meta':
                    raise ValueError('Enable the Meta provider before requesting model extraction')
                telemetry['execution'] = execution_context('meta-extraction', provider_status()['model'])
                extracted = await extract_record_document(raw, name, mime, telemetry,
                    use_local_ocr=False, screen_document=screen_untrusted)
                draft = review_draft(name, raw, extracted)
            else:
                draft = make_history_draft(name, raw)
            inspected = {'source_content': draft['source'].get('content', ''),
                'facts': draft.get('facts', []), 'observations': draft['observations']}
            if extension in {'csv', 'txt'}:
                inspected['source_text'] = raw.decode('utf-8', errors='replace')
            checks = {'draft': screen_untrusted(inspected)}
            if 'source_document_guard' in draft:
                checks['source'] = draft['source_document_guard']
            draft['document_guard'] = {'method': 'deterministic_known_patterns', 'model_executed': False,
                'status': 'quarantined' if any(check['status'] == 'quarantined' for check in checks.values()) else 'passed',
                'checks': checks, 'scope': 'Available text and draft fields only; image pixels are not screened.'}
            if draft['document_guard']['status'] == 'quarantined':
                draft.setdefault('warnings', []).append('Instruction-like text was flagged for review. The original and extracted records are preserved; this text cannot authorize tools or save records.')
            if telemetry:
                draft['source']['extraction_telemetry'] = telemetry
            saved = store.add_draft(draft, raw=raw, filename=name, mime=mime)
            if use_meta:
                recorded_run('extraction', status='review_required', draft_id=saved['id'], mode=mode,
                    message='A draft was read. No measurements were saved.',
                    execution=telemetry.get('execution'), telemetry=telemetry)
            return preview_response(saved, store=store)
        except RuntimeError:
            recorded_run('extraction_failure', status='failed', mode=mode, error='Model extraction failed; no draft was accepted.', execution=telemetry.get('execution'), telemetry=telemetry)
            raise HTTPException(502, extraction_failure_detail('Model extraction failed; no draft was accepted. No local fallback was used.', telemetry)) from None
        except (ValueError, KeyError, TypeError) as error:
            if telemetry:
                recorded_run('extraction_failure', status='failed', mode=mode, error='No usable validated extraction was accepted.', execution=telemetry.get('execution'), telemetry=telemetry)
            raise HTTPException(422, extraction_failure_detail('No usable validated rows were accepted. Check explicit dates, values and units, or choose a supported extraction mode.', telemetry)) from None
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
            response = await run_in_threadpool(conversations.answer, context, request.message, request.continuation_token)
            if response is None:
                response = (await history_agent.live_chat(context, request.message, telemetry)
                    if provider_status()['mode'] == 'meta' else await run_in_threadpool(history_agent.offline_chat, context, request.message))
                response = conversations.remember(context, response, request.message)
            await run_in_threadpool(recorded_run, 'question', status='completed' if response['claims'] else 'abstained',
                message=request.message, scope=response['scope'],
                comparison=response.get('history_comparison'), answer=response['answer'],
                mode=response['mode'], execution=response['execution'], telemetry=response.get('telemetry', {}))
            return response
        except Exception:
            await run_in_threadpool(recorded_run, 'question', status='failed', scope=context['view']['scope'], mode=provider_status()['mode'],
                error='No validated history answer was produced.', execution=telemetry.get('execution'), telemetry=telemetry)
            raise HTTPException(502, 'The history agent could not complete a validated response. No records changed and no local fallback was used.') from None

    @app.post('/api/briefs/preview')
    def preview_brief(request: BriefRequest):
        try:
            return build_brief(store, request)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post('/api/briefs/report-preview')
    def preview_report_brief(request: ReportBriefRequest):
        try:
            return build_report_brief(store, request)
        except SnapshotExpired as error:
            raise HTTPException(409, str(error)) from None
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post('/api/briefs/report-export')
    def export_report_brief(request: ReportBriefExportRequest):
        try:
            brief = validate_report_export(store, request)
            content = render_html(brief) if request.format == 'html' else render_json(brief)
        except (SnapshotExpired, BriefChangedError) as error:
            raise HTTPException(409, str(error)) from None
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        return Response(content, media_type='text/html' if request.format == 'html' else 'application/json', headers={
            'Content-Disposition': f'attachment; filename="modus-checkup-comparison.{request.format}"',
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})

    @app.post('/api/briefs/export')
    def export_brief(request: BriefExportRequest):
        try:
            brief = validate_export(store, request)
            content = render_html(brief) if request.format == 'html' else render_json(brief)
        except BriefChangedError:
            raise HTTPException(409, 'This brief changed after preview. Review the updated brief before downloading.') from None
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        return Response(content, media_type='text/html' if request.format == 'html' else 'application/json', headers={
            'Content-Disposition': f'attachment; filename="modus-record-brief.{request.format}"',
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})

    @app.get('/api/changes')
    def changes(known_at: AwareDatetime | None = None):
        rows = store.history(known_at)
        return {'changes': [projected_change(row)
            for row in rows if row.get('schema') == 'modus-entry-change-v1'
            and row.get('kind') in {'import', 'question', 'extraction', 'extraction_failure', 'amendment'}]}

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
