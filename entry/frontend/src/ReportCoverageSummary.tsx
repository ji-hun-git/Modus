import type { ReportCoverage } from "./types";

const pageStatus = {
  processed: "Draft fields found",
  no_fields: "No fields proposed",
  failed: "Reading failed",
  not_run: "Not read",
};

export default function ReportCoverageSummary({
  coverage,
}: {
  coverage: ReportCoverage;
}) {
  const failed = coverage.pages.filter(
    (page) => page.status === "failed",
  ).length;
  const unread = coverage.pages.filter(
    (page) => page.status === "not_run",
  ).length;
  const empty = coverage.pages.filter(
    (page) => page.status === "no_fields",
  ).length;
  const pageNotes = [
    failed ? `${failed} failed` : "",
    unread ? `${unread} not read` : "",
    empty ? `${empty} with no fields` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <details
      className="report-page-coverage"
      open={coverage.status === "failed"}
    >
      <summary>
        {coverage.processed_pages} of {coverage.page_count} pages processed
        {coverage.status === "failed" ? " · Reading stopped" : ""}
        {pageNotes ? ` · ${pageNotes}` : " · Page details"}
      </summary>
      <p>Processing a page does not confirm that every detail was found.</p>
      <ol aria-label="Report page coverage">
        {coverage.pages.map((page) => (
          <li key={page.page}>
            <strong>Page {page.page}</strong>
            <span>
              {pageStatus[page.status]}
              {page.field_count > 0 ? ` · ${page.field_count} fields` : ""}
            </span>
            <small>
              {page.readability === "image_only"
                ? "Image supplied; text could not be checked locally."
                : page.readability === "unreadable"
                  ? "No readable text or image was available."
                  : "Source text available."}
              {page.field_count > 0 && page.verification_status !== "completed"
                ? " Source check unfinished."
                : ""}
            </small>
          </li>
        ))}
      </ol>
    </details>
  );
}
