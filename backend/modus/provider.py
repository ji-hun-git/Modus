"""Official-endpoint transport shared by bounded integrations. No model-owned URLs."""
import os
import re
import ssl
from time import perf_counter
import httpx
from .policy import POLICY


ERROR_KINDS = frozenset({'timeout', 'http_error', 'invalid_json', 'invalid_envelope',
                         'refusal', 'incomplete', 'transport_error', 'request_failed',
                         'budget_exceeded', 'model_mismatch'})


def safe_identifier(value):
    """Keep bounded opaque identifiers, never header maps or provider prose."""
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}', value) else None


class MetaRequestError(RuntimeError):
    def __init__(self, kind, *, http_status=None, request_id=None):
        self.error_kind = kind if kind in ERROR_KINDS else 'request_failed'
        self.http_status = http_status if type(http_status) is int and 100 <= http_status <= 599 else None
        self.request_id = safe_identifier(request_id)
        super().__init__('Meta request failed; no validated result was produced')


class ProviderResponse(dict):
    """A dict-compatible response with only allowlisted HTTP diagnostics."""
    def __init__(self, data, http_status, request_id):
        super().__init__(data)
        self.http_status = http_status
        self.request_id = safe_identifier(request_id)


def failure_kind(error):
    if isinstance(error, MetaRequestError):
        return error.error_kind
    if isinstance(error, (httpx.TimeoutException, TimeoutError)):
        return 'timeout'
    if isinstance(error, httpx.TransportError):
        return 'transport_error'
    return 'request_failed'


def validate_completion(response):
    """Reject explicit refusals/interruption even if a partial payload parses.

    Legacy injected test responses can omit completion metadata. Absence remains
    unknown; it is never synthesized as a successful finish reason.
    """
    choices = response.get('choices')
    if isinstance(response, ProviderResponse) and (not isinstance(choices, list) or not choices):
        raise MetaRequestError('invalid_envelope')
    if choices is None:
        return
    if not isinstance(choices, list):
        raise MetaRequestError('invalid_envelope')
    for choice in choices:
        if not isinstance(choice, dict) or not isinstance(choice.get('message'), dict):
            raise MetaRequestError('invalid_envelope')
        if choice['message'].get('refusal'):
            raise MetaRequestError('refusal')
        finish = choice.get('finish_reason')
        if finish is not None and (not isinstance(finish, str) or finish not in {'stop', 'tool_calls', 'function_call'}):
            raise MetaRequestError('incomplete')


def meta_credential():
    """Meta-only alias; evaluation provider credentials are never used here."""
    return os.getenv('MODUS_META_KEY') or os.getenv('MODEL_API_KEY')


def provider_status():
    configured = bool(meta_credential())
    requested = os.getenv('MODUS_PROVIDER', 'offline')
    return {'mode': 'meta' if requested == 'meta' and configured else 'offline',
            'requested_mode': requested, 'key_configured': configured,
            'model': os.getenv('MODUS_MODEL', 'muse-spark-1.3'), 'live_verified': False}


async def meta_request(payload):
    key = meta_credential()
    if not key:
        raise ValueError('Meta credentials are not configured')
    base = os.getenv('MODUS_META_BASE_URL', 'https://api.meta.ai/v1').rstrip('/')
    if base != 'https://api.meta.ai/v1':
        raise ValueError('Live Meta requests require the official API endpoint')
    if 'contributor' in payload.get('model', '').lower() and not POLICY.allow_contributor_mode:
        raise ValueError('Contributor mode is disabled by this project policy')
    async with httpx.AsyncClient(timeout=POLICY.request_timeout_seconds, verify=ssl.create_default_context()) as client:
        response = await client.post(base + '/chat/completions', headers={'Authorization': f'Bearer {key}'}, json=payload)
        request_id = safe_identifier(response.headers.get('x-request-id')) or safe_identifier(response.headers.get('request-id'))
        if response.status_code >= 400:
            raise MetaRequestError('http_error', http_status=response.status_code, request_id=request_id)
        try:
            data = response.json()
        except ValueError:
            raise MetaRequestError('invalid_json', http_status=response.status_code, request_id=request_id) from None
        if not isinstance(data, dict):
            raise MetaRequestError('invalid_envelope', http_status=response.status_code, request_id=request_id)
        return ProviderResponse(data, response.status_code, request_id)


async def measured_request(payload, telemetry, request=None):
    started = perf_counter()
    item = {'model': payload['model'], 'status': 'failed', 'usage': None,
            'response_id': None, 'request_id': None, 'http_status': None,
            'finish_reason': None, 'error_kind': None}
    item.update({k: telemetry['execution'][k] for k in ('run_id', 'bundle_id', 'config_id')}
                 if 'execution' in telemetry else {})
    try:
        response = await (request or meta_request)(payload)
        if not isinstance(response, dict):
            raise MetaRequestError('invalid_envelope')
        if isinstance(response, ProviderResponse):
            item.update(http_status=response.http_status, request_id=response.request_id)
        item['response_id'] = safe_identifier(response.get('id'))
        if isinstance(response.get('model'), str):
            item['returned_model'] = safe_identifier(response['model'])
        usage = response.get('usage') if isinstance(response.get('usage'), dict) else {}
        item['usage'] = {k: v for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')
                         if type(v := usage.get(k)) is int and v >= 0}
        choices = response.get('choices')
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            finish = choices[0].get('finish_reason')
            item['finish_reason'] = finish if isinstance(finish, str) and finish in {'stop', 'tool_calls', 'function_call', 'length', 'content_filter'} else 'unknown' if finish is not None else None
        validate_completion(response)
        item['status'] = 'completed'
        return response
    except Exception as error:
        item['error_kind'] = failure_kind(error)
        if isinstance(error, MetaRequestError):
            if error.http_status is not None:
                item['http_status'] = error.http_status
            if error.request_id is not None:
                item['request_id'] = error.request_id
        raise MetaRequestError(item['error_kind'], http_status=item['http_status'], request_id=item['request_id']) from None
    finally:
        item['duration_ms'] = round((perf_counter() - started) * 1000, 2)
        telemetry.setdefault('calls', []).append(item)
        telemetry['usage'] = {k: sum(c['usage'][k] for c in telemetry['calls'])
            if all(c['usage'] is not None and k in c['usage'] for c in telemetry['calls']) else None
            for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
