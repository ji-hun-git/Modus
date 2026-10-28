"""Artificial harness regressions. Never open a real old evaluation corpus."""
import builtins
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path

import pytest

SCRIPT = Path(__file__).absolute().parents[2] / "scripts/evaluate_ontology_rag.py"
SPEC = importlib.util.spec_from_file_location("ontology_rag_evaluation", SCRIPT)
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


@pytest.mark.parametrize("operation", [
    lambda p: builtins.open(p, "rb"),
    lambda p: p.read_bytes(),
    lambda p: p.stat(),
    lambda p: os.stat(p),
    lambda p: os.access(p, os.R_OK),
    lambda p: os.scandir(p.parent),
    lambda p: os.listdir(p.parent),
    lambda p: os.open(p, os.O_RDONLY),
])
def test_private_access_is_blocked_before_read_or_probe(tmp_path, operation):
    forbidden = tmp_path / "evaluation" / "old-private" / "heldout" / "input.json"
    forbidden.parent.mkdir(parents=True)
    forbidden.write_text("artificial sentinel only", encoding="utf-8")
    with evaluation.access_tripwire() as accesses:
        with pytest.raises(evaluation.PrivateCorpusAccess):
            operation(forbidden)
    assert accesses["blocked"]
    assert not accesses["reads"]


def test_exact_manifest_file_allowed_but_parent_enumeration_denied(tmp_path):
    allowed = tmp_path / "evaluation" / "new-baseline" / "source" / "module.py"
    allowed.parent.mkdir(parents=True)
    allowed.write_text("pass\n", encoding="utf-8")
    with evaluation.access_tripwire([allowed]):
        assert allowed.read_text(encoding="utf-8") == "pass\n"
        with pytest.raises(evaluation.PrivateCorpusAccess):
            list(allowed.parent.iterdir())


def test_private_alias_path_is_denied_without_resolving_it(tmp_path):
    path = tmp_path / "unrelated" / ".." / "evaluation" / "old" / "file.json"
    with evaluation.access_tripwire():
        with pytest.raises(evaluation.PrivateCorpusAccess):
            path.stat()


def test_fixture_fingerprint_mismatch_rejected_before_schedule(tmp_path):
    fixture = tmp_path / "artificial.json"
    fixture.write_text('{"cases": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="fixture fingerprint mismatch"):
        evaluation.load_fixture(fixture, "0" * 64)


def test_snapshot_and_protocol_fingerprint_mismatches_rejected(tmp_path):
    source = tmp_path / "snapshot" / "source" / "backend" / "example.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"original\n")
    protocol = tmp_path / "snapshot" / "protocol.json"
    raw = json.dumps({"source_sha256": {"backend/example.py": evaluation.sha256(b"original\n")}}).encode()
    protocol.write_bytes(raw)
    protocol_hash = evaluation.sha256(raw)
    evaluation.copy_verified_baseline(protocol, tmp_path / "valid-copy", protocol_hash)
    source.write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="baseline fingerprint mismatch"):
        evaluation.copy_verified_baseline(protocol, tmp_path / "bad-copy", protocol_hash)
    protocol.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="protocol fingerprint mismatch"):
        evaluation.baseline_manifest(protocol, protocol_hash)


def artificial_result():
    scope = {"as_of": "2021-12-31", "known_at": "2021-12-31T23:59:59+00:00", "captured_at": "2026-01-01T00:00:00+00:00", "scope_id": "artificial"}
    observation = {"id": "fact", "source_id": "document", "metric": "ldl", "value": 100,
                   "unit": "mg/dL", "date": "2021-02-02", "source_span": "LDL 100 mg/dL",
                   "available_at": "2021-02-03T00:00:00+00:00", "reported_at": None}
    view = {"scope": scope, "observations": [observation], "sources": [{"id": "document", "title": "Synthetic source"}]}
    hit = evaluation.hit_from_observation(observation, {"document": view["sources"][0]})
    case = {"expected_ids": ["fact"], "limit": 5}
    result = {"status": "completed", "input_view": view, "output": {"scope": deepcopy(scope), "hits": [hit]}}
    return case, result


def test_grade_rejects_unsupported_value_and_out_of_scope_evidence():
    case, result = artificial_result()
    assert evaluation.grade_retrieval(case, result)["exact"]
    result["output"]["hits"][0]["value"] = 101
    assert evaluation.grade_retrieval(case, result)["unsupported_hits"] == 1
    result["output"]["hits"][0]["observation_id"] = "future-unavailable"
    grade = evaluation.grade_retrieval(case, result)
    assert grade["temporal_leaks"] == 1
    assert not grade["exact"]


def test_grade_rejects_changed_scope_duplicates_and_limit_overflow():
    case, result = artificial_result()
    result["output"]["scope"]["known_at"] = "2027-01-01T00:00:00+00:00"
    assert not evaluation.grade_retrieval(case, result)["scope_exact"]
    case, result = artificial_result()
    result["output"]["hits"] *= 6
    grade = evaluation.grade_retrieval(case, result)
    assert grade["duplicate_ids"] == 5
    assert not grade["bounded"]
    assert not grade["exact"]


def test_error_is_not_successful_empty_abstention():
    negative = {"expected_ids": [], "limit": 5}
    grade = evaluation.grade_retrieval(negative, {"status": "error"})
    assert grade["error"] and not grade["abstention_correct"]
    assert grade["precision_at_k"] == grade["recall_at_k"] == 0


def test_mapping_error_keeps_expected_dimensions_in_denominator():
    case = {"kind": "coding", "expected": {"matches": {"code": {"method": "calculated", "specimen": "serum"}}}}
    grade = evaluation.grade_mapping(case, {"status": "error"})
    summary = evaluation.summarize([{"kind": "coding", "status": "error", "grade": grade}])
    assert summary["scheduled"] == 1 and summary["errors"] == 1
    assert summary["mapping"]["dimensions_expected"] == 2
    assert summary["mapping"]["dimensions_available"] == 0


def test_absent_baseline_dimensions_are_not_execution_errors():
    case = {"kind": "coding", "expected": {"status": "resolved", "metric": "ldl", "matches": {"code": {"method": "calculated"}}}}
    result = {"status": "completed", "output": {"metric": "ldl", "qualified": True, "matches": [], "unavailable_dimensions": ["method"]}}
    grade = evaluation.grade_mapping(case, result)
    assert grade["comparable_exact"] and not grade["contract_exact"]
    assert not grade["error"]
    assert grade["dimensions"]["code:method"] == {"available": False, "correct": False}


def test_gold_never_enters_worker_payload():
    fixture = {"captured_at": "fixed", "scopes": {}, "sources": [], "observations": [],
               "cases": [{"id": "example", "kind": "retrieval", "query": "records", "expected_ids": ["secret-gold"], "expected": {"metric": "gold"}, "category": "gold-category"}]}
    payload = evaluation.input_payload(fixture, "candidate", Path("temporary-source"))
    assert "expected" not in payload["cases"][0]
    assert "expected_ids" not in payload["cases"][0]
    assert "category" not in payload["cases"][0]


def test_candidate_only_plan_never_reads_or_probes_archive(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Candidate-only mode must not inspect a baseline")
    monkeypatch.setattr(evaluation, "baseline_manifest", forbidden)
    monkeypatch.setattr(evaluation, "copy_verified_baseline", forbidden)
    monkeypatch.setattr(evaluation, "load_fixture", lambda: {"cases": []})
    result = evaluation.evaluate(plan_only=True, candidate_only=True)
    assert result["comparison_mode"] == "candidate_only_no_baseline"
    assert result["baseline_source_id"] is None
    assert result["methods"] == ["candidate"]
