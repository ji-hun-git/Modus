import type { ReportCoverage } from "./types";

let sessionToken: string | null = null;
let sessionDeadline = 0;
let idleMilliseconds = 0;
let expiryTimer: ReturnType<typeof setTimeout> | undefined;
const accessListeners = new Set<() => void>();
export const hasLocalAccess = () => sessionToken !== null;
export function subscribeLocalAccess(listener: () => void) {
  accessListeners.add(listener);
  return () => { accessListeners.delete(listener); };
}
export function clearLocalAccess() {
  sessionToken = null;
  clearTimeout(expiryTimer);
  accessListeners.forEach(listener => listener());
}
function renewLocalDeadline() {
  clearTimeout(expiryTimer);
  expiryTimer = setTimeout(clearLocalAccess, Math.max(0, Math.min(idleMilliseconds, sessionDeadline - Date.now())));
}
export function acceptLocalSession(value: unknown) {
  const session = value as {access_token?: unknown; idle_seconds?: unknown; expires_in?: unknown};
  if (!session || typeof session.access_token !== 'string' || !/^modus_session_[\w-]{43}$/.test(session.access_token)
      || typeof session.idle_seconds !== 'number' || !Number.isFinite(session.idle_seconds) || session.idle_seconds <= 0 || session.idle_seconds > 1800
      || typeof session.expires_in !== 'number' || !Number.isFinite(session.expires_in) || session.expires_in <= 0 || session.expires_in > 28800)
    throw new Error('Modus did not return a valid local session.');
  sessionToken = session.access_token;
  sessionDeadline = Date.now() + session.expires_in * 1000;
  idleMilliseconds = session.idle_seconds * 1000;
  renewLocalDeadline();
  accessListeners.forEach(listener => listener());
}
export function readAccessFile(text: string, origin: string): string {
  let file: {format?: unknown; origin?: unknown; token?: unknown};
  try { file = JSON.parse(text); } catch { throw new Error('Choose the access file created by the Modus launcher.'); }
  if (!file || file.format !== 'modus-local-access-v1' || file.origin !== origin
      || typeof file.token !== 'string' || !/^modus_local_[\w-]{43}$/.test(file.token))
    throw new Error('Choose the current access file for this Modus window.');
  return file.token;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly reportCoverage?: ReportCoverage,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await localRequest("/api" + path, options);
  if (!response.ok) {
    let message = `The request could not be completed (${response.status}).`;
    let coverage: ReportCoverage | undefined;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (typeof body.detail?.message === "string") {
        message = body.detail.message;
        if (body.detail.report_coverage?.version === "whole-report-v1")
          coverage = body.detail.report_coverage;
      }
    } catch {
      /* retain safe status */
    }
    throw new ApiError(message, response.status, coverage);
  }
  return response.json();
}
// Custom write header cannot be sent by a cross-origin HTML form. The server
// also verifies the origin and browser metadata; this is not an auth token.
export function localRequest(path: string, options?: RequestInit) {
  if (!path.startsWith('/api/') || path.includes('\\')) throw new Error('Use a local record endpoint.');
  const headers = new Headers(options?.headers);
  // Tokens stay only in this module's memory, never cookies, storage or URLs.
  const requestSession = sessionToken;
  if (requestSession) headers.set('Authorization', `Bearer ${requestSession}`);
  else headers.delete('Authorization');
  if (!['GET', 'HEAD', 'OPTIONS'].includes((options?.method || 'GET').toUpperCase()))
    headers.set('X-Modus-Request', '1');
  if (requestSession && path !== '/api/access/status') renewLocalDeadline();
  return fetch(path, {...options, headers, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', redirect: 'error'}).then(response => {
    // A lock receipt contains no records and must remain readable after this
    // window clears its credential. Late private responses are still rejected.
    if (requestSession && requestSession !== sessionToken && path !== '/api/access/lock')
      throw new ApiError('Your local session changed. Open your records again.', 401);
    if (response.status === 401 && requestSession && requestSession === sessionToken) clearLocalAccess();
    return response;
  });
}
export async function lockLocalAccess() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const pending = localRequest('/api/access/lock', {method: 'POST', signal: controller.signal});
    clearLocalAccess(); // Hide records even if the service is slow or unavailable.
    const response = await pending;
    if (!response.ok) throw new ApiError('The service could not confirm locking all windows.', response.status);
  } finally { clearTimeout(timeout); }
}
export const post = <T>(path: string, body: unknown) =>
  api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
