import test from "node:test";
import assert from "node:assert/strict";
import {
  recordLabel,
  metricDescription,
  unitLabel,
  recordDateLabel,
  facilityLabel,
} from "../src/recordPresentation.mjs";

test("HbA1c uses its short recorded name without teaching copy", () => {
  assert.equal(recordLabel("HbA1c"), "HbA1c");
  assert.equal(recordLabel(" hba1c "), "HbA1c");
  assert.equal(metricDescription("HbA1c"), "");
});
test("LDL stays distinct from unspecified cholesterol and unknown test names", () => {
  for (const alias of ["LDL", "LDL-C", "LDL cholesterol"])
    assert.equal(recordLabel(alias), "LDL");
  assert.equal(metricDescription("LDL"), "");
  assert.equal(recordLabel("Cholesterol"), "Cholesterol");
  assert.equal(metricDescription("Cholesterol"), "");
  assert.equal(recordLabel("HbA1c (IFCC)"), "HbA1c (IFCC)");
  for (const label of [
    "eGFR (creatinine)",
    "LDL, calculated",
    "Glucose",
    "Kidney function",
    "HbA1c target",
  ])
    assert.equal(recordLabel(label), label);
});
test("eGFR uses its short recorded name without interpretation", () => {
  assert.equal(recordLabel("eGFR"), "eGFR");
  assert.equal(metricDescription("eGFR"), "");
  assert.doesNotMatch(
    metricDescription("eGFR"),
    /normal|healthy|disease|score/i,
  );
});
test("unit typography never converts a recorded unit", () => {
  assert.equal(unitLabel("mL/min/1.73m2"), "mL/min/1.73 m²");
  assert.equal(unitLabel("mmol/mol"), "mmol/mol");
  assert.equal(unitLabel("unknown units"), "unknown units");
  assert.equal(unitLabel(null), "");
});
test("known demo provenance notes are not displayed as facilities", () => {
  assert.equal(facilityLabel("Authored synthetic example"), null);
  assert.equal(facilityLabel("Imported synthetic document"), null);
  assert.equal(
    facilityLabel("Imported Radiology Center"),
    "Imported Radiology Center",
  );
  assert.equal(facilityLabel(null), null);
});
test("year-only and month-only dates keep their original precision", () => {
  assert.equal(recordDateLabel("2012"), "2012");
  assert.equal(recordDateLabel("2012-04"), "Apr 2012");
  assert.equal(recordDateLabel(null), "Date not recorded");
  assert.equal(recordDateLabel("childhood"), "childhood");
});
test("date-only records keep the recorded calendar day", () => {
  assert.equal(recordDateLabel("2021-04-08"), "8 Apr 2021");
  assert.equal(recordDateLabel("2021-04-08T00:00:00Z"), "8 Apr 2021");
});
test("ambiguous and impossible dates are not silently interpreted or rolled forward", () => {
  assert.equal(recordDateLabel("04/05/2020"), "04/05/2020");
  assert.equal(recordDateLabel("approximately 2019"), "approximately 2019");
  assert.equal(recordDateLabel("spring 2019"), "spring 2019");
  assert.equal(recordDateLabel("2020-02-30"), "2020-02-30");
  assert.equal(recordDateLabel("2020-02-30T00:00:00Z"), "2020-02-30T00:00:00Z");
  assert.equal(recordDateLabel("2020-13"), "2020-13");
});
