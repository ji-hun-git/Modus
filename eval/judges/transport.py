"""Literal provider endpoints and strict one-shot JSON responses. No retries."""
import base64
import json
import re
from time import perf_counter

import httpx

from .schema import ENDPOINTS, validate_judgement

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class JudgeError(RuntimeError):
    def __init__(self, kind, **metadata):
        self.kind, self.metadata = kind, metadata
        super().__init__(kind)


def safe_id(value):
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,180}', value) else None


def payload(provider, system, user, images, schema):
    encoded = [{'mime': i['mime'], 'data': base64.b64encode(i['raw']).decode('ascii')} for i in images]
    if provider.provider == 'meta':
        content = [{'type': 'text', 'text': user}] + [{'type': 'image_url', 'image_url': {
            'url': 'data:' + image['mime'] + ';base64,' + image['data']}} for image in encoded]
        return {'model': provider.model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': content}],
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'IndependentJury', 'strict': True, 'schema': schema}},
            'max_completion_tokens': provider.max_output_tokens, 'reasoning_effort': provider.settings['reasoning_effort']}
    if provider.provider == 'anthropic':
        content = [{'type': 'text', 'text': user}] + [{'type': 'image', 'source': {
            'type': 'base64', 'media_type': image['mime'], 'data': image['data']}} for image in encoded]
        return {'model': provider.model, 'system': system, 'messages': [{'role': 'user', 'content': content}],
            'max_tokens': provider.max_output_tokens, 'thinking': provider.settings['thinking'],
            'output_config': {'effort': provider.settings['effort'], 'format': {'type': 'json_schema', 'schema': schema}}}
    content = [{'type': 'input_text', 'text': user}] + [{'type': 'input_image',
        'image_url': 'data:' + image['mime'] + ';base64,' + image['data']} for image in encoded]
    return {'model': provider.model, 'instructions': system, 'input': [{'role': 'user', 'content': content}],
        'max_output_tokens': provider.max_output_tokens, 'store': False, 'reasoning': {'effort': 'none'},
        'text': {'format': {'type': 'json_schema', 'name': 'IndependentJury', 'strict': True, 'schema': schema}}}


def error_details(raw, key):
    """Bounded provider diagnostics are untrusted data, never instructions."""
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    error = body.get('error') if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return None
    kind = error.get('type', error.get('code'))
    kind = kind.replace(key, '[REDACTED]') if isinstance(kind, str) and key else kind
    kind = kind if isinstance(kind, str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', kind) else None
    message = error.get('message')
    if isinstance(message, str):
        message = message.replace(key, '[REDACTED]') if key else message
        message = ' '.join(re.sub(r'[\x00-\x1f\x7f]', ' ', message).split())[:600]
    else:
        message = None
    return {'type': kind, 'message': message, 'untrusted_provider_data': True}


async def send(provider, request, key):
    if provider.endpoint != ENDPOINTS[provider.provider][0]:
        raise JudgeError('endpoint_not_allowlisted')
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    if provider.provider == 'anthropic':
        headers['anthropic-version'] = provider.api_version
    started = perf_counter()
    info = {'request_id': None, 'http_status': None}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10), follow_redirects=False) as client:
            async with client.stream('POST', provider.endpoint, headers=headers, json=request) as response:
                info.update(http_status=response.status_code, request_id=safe_id(response.headers.get('x-request-id')) or safe_id(response.headers.get('request-id')))
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(raw) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise JudgeError('response_size_limit', **info)
                    raw.extend(chunk)
        if response.status_code != 200:
            raise JudgeError('http_error', **info, provider_error=error_details(raw, key))
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise JudgeError('invalid_envelope_json', **info) from None
        if not isinstance(body, dict):
            raise JudgeError('invalid_envelope', **info)
        return {**info, 'latency_ms': round((perf_counter() - started) * 1000, 2), 'body': body}
    except JudgeError as error:
        error.metadata['latency_ms'] = round((perf_counter() - started) * 1000, 2)
        raise
    except httpx.TimeoutException:
        raise JudgeError('timeout', **info, latency_ms=round((perf_counter() - started) * 1000, 2)) from None
    except httpx.HTTPError:
        raise JudgeError('transport_error', **info, latency_ms=round((perf_counter() - started) * 1000, 2)) from None


def usage(provider, body):
    raw = body.get('usage')
    if not isinstance(raw, dict):
        return None
    keys = ('prompt_tokens', 'completion_tokens') if provider.provider == 'meta' else ('input_tokens', 'output_tokens')
    if any(type(raw.get(k)) is not int or raw[k] < 0 for k in keys):
        return None
    # No explicit prompt-cache controls are sent. Unexpected cache-priced usage
    # stays unknown rather than being priced using the wrong token category.
    if provider.provider == 'anthropic' and any(raw.get(k, 0) for k in ('cache_creation_input_tokens', 'cache_read_input_tokens')):
        return None
    return {'input_tokens': raw[keys[0]], 'output_tokens': raw[keys[1]]}


def parse(provider, envelope, criteria):
    body = envelope['body']
    info = {k: envelope.get(k) for k in ('request_id', 'http_status', 'latency_ms')}
    info.update(response_id=safe_id(body.get('id')), returned_model=safe_id(body.get('model')), usage=usage(provider, body))
    if body.get('model') != provider.model:
        # A different model cannot be priced or accepted as the locked judge.
        raise JudgeError('model_mismatch', **{**info, 'usage': None})
    texts = []
    try:
        if provider.provider == 'meta':
            choices = body['choices']
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError
            choice, message = choices[0], choices[0]['message']
            if message.get('refusal'):
                raise JudgeError('refusal', **info)
            if choice.get('finish_reason') != 'stop':
                raise JudgeError('incomplete', **info)
            if message.get('tool_calls'):
                raise JudgeError('unexpected_tool', **info)
            texts = [message['content']]
        elif provider.provider == 'anthropic':
            if body.get('stop_reason') == 'refusal':
                raise JudgeError('refusal', **info)
            if body.get('stop_reason') != 'end_turn':
                raise JudgeError('incomplete', **info)
            for part in body['content']:
                if part.get('type') != 'text':
                    raise JudgeError('unexpected_content', **info)
                texts.append(part['text'])
        else:
            if body.get('status') != 'completed' or body.get('error') or body.get('incomplete_details'):
                raise JudgeError('incomplete', **info)
            for item in body['output']:
                if item.get('type') == 'reasoning':
                    continue
                if item.get('type') != 'message':
                    raise JudgeError('unexpected_tool_or_output', **info)
                for part in item['content']:
                    if part.get('type') == 'refusal':
                        raise JudgeError('refusal', **info)
                    if part.get('type') != 'output_text':
                        raise JudgeError('unexpected_content', **info)
                    texts.append(part['text'])
        if not texts or any(not isinstance(t, str) for t in texts):
            raise ValueError
    except (KeyError, TypeError, ValueError, AttributeError):
        raise JudgeError('invalid_output_envelope', **info) from None
    text = ''.join(texts)
    try:
        judgement = validate_judgement(text, criteria)
    except ValueError:
        raise JudgeError('invalid_judgement', **info, output_text=text[:16000]) from None
    return judgement, info
