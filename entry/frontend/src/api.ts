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
  const response = await fetch("/api" + path, options);
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
export const post = <T>(path: string, body: unknown) =>
  api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
