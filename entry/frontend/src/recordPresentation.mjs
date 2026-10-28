const metrics = {
  hba1c: {
    label: "HbA1c",
    description:
      "A blood test that reflects average blood sugar over about 3 months.",
  },
  egfr: {
    label: "eGFR",
    description: "An estimate of how quickly the kidneys filter blood.",
  },
  ldl: {
    label: "LDL cholesterol",
    description: "The cholesterol carried by LDL particles in the blood.",
  },
};
const aliases = {
  hba1c: "hba1c",
  egfr: "egfr",
  ldl: "ldl",
  "ldl-c": "ldl",
  "ldl cholesterol": "ldl",
};
const metric = (label) => metrics[aliases[label.trim().toLowerCase()]];

// Only reviewed exact aliases receive a display name. Qualifiers and unknown
// labels stay intact; presentation never infers a medical concept from a word.
export const recordLabel = (label) => metric(label)?.label ?? label;
export const metricLabel = recordLabel;
export const metricDescription = (label) => metric(label)?.description ?? "";
const provenancePlaceholders = new Set([
  "authored synthetic example",
  "imported synthetic document",
]);
// Legacy demo imports used source-provenance notes as facility strings. Keep
// those raw notes in source details, rather than presenting them as a facility.
export const facilityLabel = (value) =>
  value && !provenancePlaceholders.has(value.trim().toLowerCase())
    ? value
    : null;

// Typography only: no unit conversion, case folding or numeric interpretation.
export const unitLabel = (unit) =>
  ({
    "mL/min/1.73m2": "mL/min/1.73 m²",
    "mL/min/1.73 m2": "mL/min/1.73 m²",
  })[unit ?? ""] ??
  unit ??
  "";

export function recordDateLabel(value) {
  if (!value) return "Date not recorded";
  if (/^[0-9]{4}$/.test(value)) return value;
  if (/^[0-9]{4}-(0[1-9]|1[0-2])$/.test(value)) {
    return new Date(`${value}-01T12:00:00Z`).toLocaleDateString("en-GB", {
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });
  }
  const exact = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;
  const timestamp =
    /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,9})?)?(?:Z|[+-][0-9]{2}:[0-9]{2})$/;
  if (!exact.test(value) && !timestamp.test(value)) return value;
  const calendarDay = value.slice(0, 10);
  const calendar = new Date(`${calendarDay}T12:00:00Z`);
  if (
    Number.isNaN(calendar.getTime()) ||
    calendar.toISOString().slice(0, 10) !== calendarDay
  )
    return value;
  const date = new Date(exact.test(value) ? `${value}T12:00:00Z` : value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}
