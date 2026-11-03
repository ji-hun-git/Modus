"""Browser boundary for the local, single-owner service; not account authentication."""
import asyncio
import ipaddress
import logging
from urllib.parse import urlsplit

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

MAX_REQUEST_BYTES = 8 * 1024 * 1024 + 128 * 1024
BODY_TIMEOUT_SECONDS = 30
WRITE_HEADER = b'x-modus-request'
SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
       "object-src 'none'; base-uri 'none'; form-action 'self'; frame-src 'none'; frame-ancestors 'none'")
SECURITY_HEADERS = {
    'Cache-Control': 'no-store',
    'Referrer-Policy': 'no-referrer',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Cross-Origin-Resource-Policy': 'same-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
}
logger = logging.getLogger(__name__)


def _origin(value, *, referer=False):
    """An exact scheme/host/port tuple. No suffix matching or forwarded headers."""
    if not value or any(c.isspace() or ord(c) < 32 for c in value) or '\\' in value:
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or (not referer and (parsed.path or parsed.query or parsed.fragment))):
            return None
        if parsed.port is not None and parsed.port < 1:
            return None
        return parsed.scheme, parsed.hostname.lower(), parsed.port if parsed.port is not None else (443 if parsed.scheme == 'https' else 80)
    except ValueError:
        return None


def _local_client(scope):
    try:
        return ipaddress.ip_address(scope['client'][0]).is_loopback
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def request_allowed(scope):
    headers = {}
    sensitive = {b'host', b'origin', b'referer', b'sec-fetch-site', b'authorization', WRITE_HEADER, b'content-length'}
    for key, value in scope['headers']:
        key = key.lower()
        if key in sensitive and key in headers:
            return False
        headers[key] = value.decode('latin-1')
    host = headers.get(b'host', '')
    target = _origin(scope.get('scheme', 'http') + '://' + host)
    if not _local_client(scope) or target is None or target[1] not in {'127.0.0.1', 'localhost', '::1'}:
        return False
    # An explicitly clicked external link can open only the static app shell.
    if (scope['method'] in {'GET', 'HEAD'} and scope['path'] == '/'
            and headers.get(b'sec-fetch-mode') == 'navigate'
            and headers.get(b'sec-fetch-dest') == 'document'
            and headers.get(b'sec-fetch-user') == '?1'):
        return True
    origin = headers.get(b'origin')
    referer = headers.get(b'referer')
    if origin is not None and _origin(origin) != target:
        return False
    if referer is not None and _origin(referer, referer=True) != target:
        return False
    site = headers.get(b'sec-fetch-site')
    # A different localhost port is same-site, not same-origin. Neither gets
    # access to records. Direct, user-initiated navigation remains usable.
    if site is not None and site not in {'same-origin', 'none'}:
        return False
    if scope['method'] not in SAFE_METHODS and headers.get(WRITE_HEADER) != '1':
        return False
    return True


class LocalSecurityMiddleware:
    def __init__(self, app, access=None):
        self.app = app
        self.access = access

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            await send({'type': 'websocket.close', 'code': 1008})
            return
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        started = False

        async def secured_send(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                started = True
                headers = MutableHeaders(scope=message)
                for key, value in SECURITY_HEADERS.items():
                    headers[key] = value
                if 'content-security-policy' not in headers:
                    headers['Content-Security-Policy'] = CSP
                # Do not disclose or enable cross-origin access through a
                # future route's accidental CORS header.
                for name in ('access-control-allow-origin', 'access-control-allow-credentials'):
                    if name in headers:
                        del headers[name]
            await send(message)

        async def reject(status, detail):
            await JSONResponse({'detail': detail}, status_code=status)(scope, receive, secured_send)

        if not request_allowed(scope):
            return await reject(403, 'Open Modus locally and make this request from its own window.')
        if self.access is not None and not self.access.permits(scope):
            return await reject(401, 'Open your local access file to unlock Modus.')
        lengths = [v for k, v in scope['headers'] if k.lower() == b'content-length']
        maximum = 1024 if scope['path'].startswith('/api/access/') else MAX_REQUEST_BYTES
        if lengths and (len(lengths[0]) > 10 or not lengths[0].isdigit() or int(lengths[0]) > maximum):
            return await reject(413, 'Request body exceeds the local upload limit.')
        if scope['method'] not in {'GET', 'HEAD'}:
            # Bound bytes BEFORE multipart parsing can spool an oversized file.
            # No model or parser is invoked until the entire bounded body arrives.
            async def read_body():
                chunks, size = [], 0
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return None
                    body = message.get('body', b'')
                    size += len(body)
                    if size > maximum:
                        raise OverflowError
                    chunks.append(body)
                    if not message.get('more_body', False):
                        return b''.join(chunks)
            try:
                body = await asyncio.wait_for(read_body(), BODY_TIMEOUT_SECONDS)
            except OverflowError:
                return await reject(413, 'Request body exceeds the local upload limit.')
            except TimeoutError:
                return await reject(408, 'Upload timed out. No document was read.')
            if body is None:
                return
            delivered = False
            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': body, 'more_body': False}
                return await receive()
        else:
            bounded_receive = receive
        try:
            await self.app(scope, bounded_receive, secured_send)
        except Exception as error:
            # Never log request URLs, bodies or exception prose containing data.
            logger.error('Record request failed (%s).', type(error).__name__)
            if started:
                raise RuntimeError('Record response interrupted') from None
            await reject(500, 'The request could not be completed. No validated result is available.')
