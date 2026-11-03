"""Per-process local access. No user accounts, cookies, persisted sessions or model authority."""
from collections import deque
from hashlib import sha256
import hmac
import math
import re
import secrets
import threading
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from .local_security import _origin

IDLE_SECONDS = 30 * 60
ABSOLUTE_SECONDS = 8 * 60 * 60
PUBLIC_ACCESS = {('GET', '/api/access/status'), ('POST', '/api/access/unlock')}


def request_origin(scope):
    return _origin(scope.get('scheme', 'http') + '://' + dict(scope['headers']).get(b'host', b'').decode('latin-1'))


def request_token(scope):
    values = [v for k, v in scope['headers'] if k.lower() == b'authorization']
    if len(values) != 1:
        return ''
    match = re.fullmatch(rb'(?i:Bearer) (modus_session_[A-Za-z0-9_-]{43})', values[0])
    return match[1].decode('ascii') if match else ''


class AccessDenied(ValueError):
    pass


class AccessThrottled(ValueError):
    def __init__(self, seconds):
        self.seconds = seconds


class LocalAccess:
    def __init__(self, *, clock=time.monotonic):
        self.clock = clock
        self.origin = None
        self._bootstrap = None
        self._sessions = {}
        self._failures = deque(maxlen=5)
        self._lock = threading.RLock()

    def configure(self, origin):
        parsed = _origin(origin)
        if parsed is None or parsed[0] != 'http' or parsed[1] not in {'127.0.0.1', 'localhost', '::1'}:
            raise ValueError('Local access requires a loopback HTTP origin')
        token = 'modus_local_' + secrets.token_urlsafe(32)
        with self._lock:
            self.origin = parsed
            self._bootstrap = sha256(token.encode()).digest()
            self._sessions.clear()
            self._failures.clear()
        return {'format': 'modus-local-access-v1', 'origin': origin, 'token': token}

    def _expire(self):
        now = self.clock()
        self._sessions = {key: value for key, value in self._sessions.items()
            if now - value['last'] < IDLE_SECONDS and now - value['created'] < ABSOLUTE_SECONDS}

    def unlock(self, token, origin):
        with self._lock:
            now = self.clock()
            while self._failures and now - self._failures[0] >= 60:
                self._failures.popleft()
            if len(self._failures) >= 5:
                raise AccessThrottled(max(1, math.ceil(60 - (now - self._failures[0]))))
            valid = (isinstance(token, str) and re.fullmatch(r'modus_local_[A-Za-z0-9_-]{43}', token)
                     and self._bootstrap is not None and origin == self.origin
                     and hmac.compare_digest(sha256(token.encode()).digest(), self._bootstrap))
            if not valid:
                self._failures.append(now)
                raise AccessDenied('Use the current local access file for this Modus window.')
            self._expire()
            if len(self._sessions) >= 8:
                del self._sessions[min(self._sessions, key=lambda key: self._sessions[key]['last'])]
            session = 'modus_session_' + secrets.token_urlsafe(32)
            self._sessions[sha256(session.encode()).digest()] = {'created': now, 'last': now}
            self._failures.clear()
            return {'access_token': session, 'idle_seconds': IDLE_SECONDS, 'expires_in': ABSOLUTE_SECONDS}

    def authenticated(self, scope, *, touch=True):
        token = request_token(scope)
        with self._lock:
            self._expire()
            if not token or request_origin(scope) != self.origin:
                return False
            digest = sha256(token.encode()).digest()
            session = self._sessions.get(digest)
            if session is None:
                return False
            if touch:
                session['last'] = self.clock()
            return True

    def lock(self):
        with self._lock:
            self._sessions.clear()

    def permits(self, scope):
        path = scope['path']
        if (scope['method'], path) in PUBLIC_ACCESS:
            return True
        # Static shell/assets contain no records. Every API (including unknown
        # routes and originals) and custom private route requires authentication.
        public_file = scope['method'] in {'GET', 'HEAD'} and (
            path in {'/', '/index.html', '/favicon.ico', '/LOINC_short_license.txt'} or path.startswith(('/assets/', '/examples/', '/fonts/')))
        return public_file or self.authenticated(scope)


class UnlockRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: StrictStr = Field(min_length=1, max_length=128)


def access_routes(access):
    router = APIRouter()

    @router.get('/api/access/status')
    def status(request: Request):
        return {'configured': access.origin is not None,
                'authenticated': access.authenticated(request.scope, touch=False)}

    @router.post('/api/access/unlock')
    def unlock(body: UnlockRequest, request: Request):
        try:
            return access.unlock(body.token, request_origin(request.scope))
        except AccessThrottled as error:
            raise HTTPException(429, 'Too many attempts. Try again shortly.', headers={'Retry-After': str(error.seconds)}) from None
        except AccessDenied:
            raise HTTPException(401, 'Use the current local access file for this Modus window.') from None

    @router.post('/api/access/lock')
    def lock():
        access.lock()
        return {'locked': True}

    @router.post('/api/access/touch')
    def touch():
        return {'active': True}

    return router
