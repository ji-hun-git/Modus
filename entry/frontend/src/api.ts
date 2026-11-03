import type { ReportCoverage } from "./types";

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
  if (!['GET', 'HEAD', 'OPTIONS'].includes((options?.method || 'GET').toUpperCase()))
    headers.set('X-Modus-Request', '1');
  return fetch(path, {...options, headers, credentials: 'same-origin', cache: 'no-store', referrerPolicy: 'no-referrer', redirect: 'error'});
}
export const post = <T>(path: string, body: unknown) =>
  api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
