"""Independent, frozen development evaluation; no private corpus or provider access.

The only permitted evaluation/ reads are the explicitly named pre-feature
protocol and its exact manifest files. Frozen modules run from a temporary copy,
never through an archived CLI. Gold stays in the parent process, not the runtime.
"""
from __future__ import annotations

import argparse
import builtins
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from time import perf_counter

ROOT = Path(__file__).absolute().parents[1]
FIXTURE = ROOT / "data/development/ontology_rag_v1.json"
FIXTURE_SHA256 = "f8d0aee72b2b6053f688b600321c04bcbdc8a895d84fa20c5ec6718b1b7a9d5d"
BASELINE = ROOT / "evaluation/ontology-rag-baseline-v1"
PROTOCOL = BASELINE / "protocol.json"
BASELINE_PROTOCOL_SHA256 = "9a836ea436894fa59baf293abc1501c2787d2d26837a49f9fa338656271e188a"
REPORT = ROOT / "eval/ontology-rag-development-v1.json"
GRADING_CONTRACT = {
    "version": "ontology-rag-dev-grading-v1",
    "schedule": "all 24 authored cases; 12 mapping and 12 retrieval; no success-only exclusion",
    "mapping_comparable": "exact concept set, or exact coarse metric plus whether mapping is qualified",
    "mapping_qualified": "candidate status resolved; baseline parse_fhir returned a row",
    "mapping_dimensions": "separate declared status/unit/method/property/specimen checks and coverage; baseline lacks these outputs",
    "retrieval": "exact unordered relevant observation-ID set at k=5, plus precision/recall; no answer-style grading",
    "support": "every returned ID and source/value/unit/date/span/availability/report field must equal its scoped observation",
    "scope": "exact returned scope equals captured view; leakage is any unknown/out-of-scope ID or future event/availability",
    "abstention": "completed empty output only; errors do not earn abstention credit",
    "lexical": "separate unfiltered token-overlap comparator, without ontology expansion or advice/injection policy",
    "time": "latency is a local observation, not a controlled performance benchmark",
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


GRADING_SHA256 = sha256(canonical(GRADING_CONTRACT))


def normalized_path(path):
    if isinstance(path, int):
        return None
    return os.path.normcase(os.path.abspath(os.fsdecode(path)))


class PrivateCorpusAccess(PermissionError):
    pass


@contextmanager
def access_tripwire(allowed_files=()):
    """Block old corpus reads *and probes*, including directory enumeration.

    Path checks are lexical: checking a forbidden path never resolves, stats or
    opens it. Test with temporary artificial names, not real held-out paths.
    """
    allowed = {normalized_path(path) for path in allowed_files}
    reads, blocked = set(), []
    state = {"active": True}
    originals = {}

    def check(path, operation):
        normalized = normalized_path(path)
        if normalized is None:
            return
        parts = normalized.replace("\\", "/").lower().split("/")
        private = any(part in {"holdout", "heldout", "held-out", "held_out"} for part in parts)
        protected = "evaluation" in parts
        if private or protected and normalized not in allowed:
            blocked.append({"operation": operation, "path": normalized})
            raise PrivateCorpusAccess(f"Private corpus access blocked: {operation}")
        if operation in {"open", "io.open", "os.open"}:
            reads.add(normalized)

    def audit(event, args):
        if state["active"] and event in {"open", "os.listdir", "os.scandir"} and args:
            check(args[0], event)

    sys.addaudithook(audit)

    for obj, name in [(builtins, "open"), (io, "open"), (os, "open"),
                      (os, "stat"), (os, "lstat"), (os, "scandir"),
                      (os, "listdir"), (os, "access"), (os, "readlink")]:
        original = getattr(obj, name)
        originals[(obj, name)] = original
        operation = name if obj is builtins else ("io." if obj is io else "os.") + name

        def wrapped(path, *args, _original=original, _operation=operation, **kwargs):
            check(path, _operation)
            return _original(path, *args, **kwargs)

        setattr(obj, name, wrapped)
    try:
        yield {"reads": reads, "blocked": blocked}
    finally:
        state["active"] = False
        for (obj, name), original in originals.items():
            setattr(obj, name, original)


def load_fixture(path=FIXTURE, expected_hash=FIXTURE_SHA256):
    raw = Path(path).read_bytes().replace(b"\r\n", b"\n")
    if sha256(raw) != expected_hash:
        raise ValueError("Frozen development fixture fingerprint mismatch")
    fixture = json.loads(raw)
    ids = [case["id"] for case in fixture["cases"]]
    if len(ids) != len(set(ids)) or len(ids) != 24:
        raise ValueError("Expected 24 unique scheduled development cases")
    if Counter(case["kind"] for case in fixture["cases"]) != {"concept": 4, "coding": 8, "retrieval": 12}:
        raise ValueError("Frozen schedule differs from the declared grading contract")
    return fixture


def baseline_manifest(protocol_path=PROTOCOL, expected_hash=BASELINE_PROTOCOL_SHA256):
    raw = Path(protocol_path).read_bytes().replace(b"\r\n", b"\n")
    if sha256(raw) != expected_hash:
        raise ValueError("Frozen baseline protocol fingerprint mismatch")
    protocol = json.loads(raw)
    manifest = protocol["source_sha256"]
    for relative in manifest:
        parts = relative.replace("\\", "/").split("/")
        if relative.startswith(("/", "\\")) or ":" in relative or ".." in parts:
            raise ValueError("Unsafe baseline manifest path")
    return protocol


def copy_verified_baseline(protocol_path, destination, expected_protocol_hash=BASELINE_PROTOCOL_SHA256):
    protocol = baseline_manifest(protocol_path, expected_protocol_hash)
    source_root = Path(protocol_path).parent / "source"
    destination = Path(destination)
    for relative, expected in protocol["source_sha256"].items():
        raw = (source_root / relative).read_bytes()
        if sha256(raw.replace(b"\r\n", b"\n")) != expected:
            raise ValueError(f"Frozen baseline fingerprint mismatch: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return protocol


def input_payload(fixture, method, source_root):
    # Expected IDs/dimensions and authorship notes never reach candidate modules.
    cases = []
    for case in fixture["cases"]:
        cases.append({key: deepcopy(value) for key, value in case.items()
                      if key not in {"expected", "expected_ids", "category"}})
    return {"method": method, "source_root": str(source_root),
            "captured_at": fixture["captured_at"], "scopes": fixture["scopes"],
            "sources": fixture["sources"], "observations": fixture["observations"], "cases": cases}


def hit_from_observation(row, sources):
    result = {key: row.get(key) for key in ("source_id", "metric", "value", "unit", "date",
              "source_span", "available_at", "reported_at")}
    result["observation_id"] = row["id"]
    result["source_title"] = sources[row["source_id"]]["title"]
    return result


def tokens(value):
    return set(re.findall(r"[\w]+", str(value).lower(), flags=re.UNICODE))


def lexical_result(view, query, limit):
    """Explicitly naive comparator: no safety policy, aliases or clinical logic."""
    terms = tokens(query) - {"the", "a", "an", "show", "find", "records", "record", "results"}
    sources = {source["id"]: source for source in view["sources"]}
    scored = []
    for row in view["observations"]:
        text = " ".join(str(row.get(key, "")) for key in ("metric", "unit", "source_span"))
        text += " " + sources[row["source_id"]]["title"]
        score = len(terms & tokens(text))
        if score:
            scored.append((score, row["id"], row))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return {"scope": deepcopy(view["scope"]), "hits": [
        {**hit_from_observation(row, sources), "score": score} for score, _, row in scored[:limit]],
        "method": "plain-token-overlap-no-policy", "empty_reason": None if scored else "no_token_overlap"}


def baseline_retrieval(view, query, limit):
    from modus_entry.agent import offline_route
    from modus_entry.tools import dispatch
    context = {"view": view, "comparison": None}
    route = offline_route(context, query)
    if route is None:
        return {"scope": deepcopy(view["scope"]), "hits": [], "route": None,
                "empty_reason": "old_router_abstained", "capability": "old typed-tool evidence, not ranked RAG"}
    name, arguments = route
    if name == "record_inventory":
        arguments = {**arguments, "limit": limit}
    raw = dispatch(context, name, arguments)
    # Actual old tool evidence order, bounded to the common top-k. No invented ranking.
    ids = list(dict.fromkeys(identifier for claim in raw.get("claims", [])
                             for identifier in claim.get("evidence_ids", [])))[:limit]
    rows = {row["id"]: row for row in view["observations"]}
    sources = {source["id"]: source for source in view["sources"]}
    return {"scope": deepcopy(view["scope"]), "hits": [hit_from_observation(rows[key], sources) for key in ids],
            "route": [name, arguments], "raw_tool": raw,
            "capability": "old typed-tool evidence order, not ranked RAG", "empty_reason": None if ids else "no_tool_evidence"}


def baseline_mapping(case):
    from modus.ingest import metric_key, parse_fhir
    if case["kind"] == "concept":
        metric = metric_key(case["query"])
        return {"concept_ids": [metric] if metric else [], "adapter": "actual frozen metric_key"}
    observation = {"resourceType": "Observation", "id": "development-input", "status": "final",
                   "subject": {"reference": "Patient/synthetic-development"},
                   "effectiveDateTime": "2021-04-08T12:00:00Z", "code": {"coding": case["codings"]},
                   "valueQuantity": case.get("quantity") or {}}
    rows, warnings = parse_fhir({"resourceType": "Bundle", "entry": [{"resource": observation}]})
    return {"metric": rows[0]["metric"] if rows else None, "qualified": bool(rows),
            "raw_rows": rows, "warnings": warnings, "matches": [],
            "unavailable_dimensions": ["mapping_status", "unit_identity", "method", "property", "specimen"],
            "adapter": "actual frozen parse_fhir; acceptance is coarse parser behavior, not a formal mapper status"}


def worker(payload):
    source_root = Path(payload["source_root"])
    sys.path.insert(0, str(source_root / "backend"))
    # Provider/network operations are never part of this local experiment.
    def audit(event, args):
        if event.startswith("socket.") and event not in {"socket.__new__"}:
            raise PermissionError("Network operation blocked in development evaluation")
    sys.addaudithook(audit)
    results = []
    with access_tripwire() as access:
        try:
            from modus.record_store import RecordStore
            from modus_entry.tools import capture
            with tempfile.TemporaryDirectory(prefix="modus-ontology-cases-") as tmp:
                store = RecordStore(Path(tmp) / "records.sqlite", seed_provider=lambda: (
                    payload["sources"], payload["observations"]), clock=lambda: payload["captured_at"])
                for case in payload["cases"]:
                    if payload["method"] == "lexical" and case["kind"] != "retrieval":
                        continue
                    started = perf_counter()
                    result = {"id": case["id"], "kind": case["kind"], "status": "completed"}
                    try:
                        if case["kind"] == "retrieval":
                            scope = payload["scopes"][case["scope"]]
                            view = capture(store, scope["as_of"], scope["known_at"])["view"]
                            result["input_view"] = view
                            if payload["method"] == "candidate":
                                from modus.record_retrieval import retrieve_record_evidence
                                output = retrieve_record_evidence(view, case["query"], limit=case["limit"])
                            elif payload["method"] == "baseline":
                                output = baseline_retrieval(view, case["query"], case["limit"])
                            else:
                                output = lexical_result(view, case["query"], case["limit"])
                        elif payload["method"] == "baseline":
                            output = baseline_mapping(case)
                        else:
                            from modus.ontology import resolve_codings, resolve_concepts
                            output = {"concept_ids": resolve_concepts(case["query"])} if case["kind"] == "concept" else resolve_codings(case["codings"], case.get("quantity"))
                        result["output"] = output
                    except Exception as exc:
                        result.update(status="error", error={"type": type(exc).__name__, "message": str(exc)[:1500]})
                    result["elapsed_ms"] = round((perf_counter() - started) * 1000, 3)
                    results.append(result)
        except Exception as exc:
            results = [{"id": case["id"], "kind": case["kind"], "status": "error",
                        "error": {"type": type(exc).__name__, "message": str(exc)[:1500]}}
                       for case in payload["cases"] if payload["method"] != "lexical" or case["kind"] == "retrieval"]
        loaded = {}
        prefix = normalized_path(source_root) + os.sep
        for name in sorted(access["reads"]):
            if name.startswith(prefix) and Path(name).suffix in {".py", ".json", ".md", ".txt"}:
                try:
                    loaded[os.path.relpath(name, source_root).replace("\\", "/")] = sha256(Path(name).read_bytes().replace(b"\r\n", b"\n"))
                except (FileNotFoundError, IsADirectoryError):
                    pass
    return {"method": payload["method"], "results": results,
            "loaded_source_sha256": loaded, "blocked_accesses": access["blocked"], "network": "blocked"}


def grade_mapping(case, result):
    dimensions = {code + ":" + dimension: {"available": False, "correct": False}
                  for code, fields in case["expected"].get("matches", {}).items() for dimension in fields}
    if result.get("status") != "completed":
        return {"comparable_exact": False, "contract_exact": False, "dimensions": dimensions, "error": True}
    output, expected = result["output"], case["expected"]
    if case["kind"] == "concept":
        exact = sorted(output.get("concept_ids", [])) == sorted(expected["concept_ids"])
        return {"comparable_exact": exact, "contract_exact": exact, "error": False}
    qualified = output.get("qualified", output.get("status") == "resolved")
    comparable = output.get("metric") == expected["metric"] and qualified == (expected["status"] == "resolved")
    checks = {"status": output.get("status") == expected["status"]}
    if "unit_identity" in expected:
        checks["unit_identity"] = output.get("unit", {}).get("identity") == expected["unit_identity"] and "unit" in output
    matches = {match.get("code"): match for match in output.get("matches", [])}
    if "match_codes" in expected:
        checks["match_codes"] = sorted(matches) == sorted(expected["match_codes"])
    dimension_checks = {}
    for code, fields in expected.get("matches", {}).items():
        for dimension, value in fields.items():
            key = code + ":" + dimension
            dimension_checks[key] = {"available": code in matches and dimension in matches[code],
                                     "correct": matches.get(code, {}).get(dimension) == value}
    if expected.get("matches") == {}:
        checks["no_authorized_code_match"] = not matches
    exact = comparable and all(checks.values()) and all(item["correct"] for item in dimension_checks.values())
    return {"comparable_exact": comparable, "contract_exact": exact, "checks": checks,
            "dimensions": dimension_checks, "unavailable_dimensions": output.get("unavailable_dimensions", []), "error": False}


def grade_retrieval(case, result):
    gold = set(case["expected_ids"])
    if result.get("status") != "completed":
        return {"exact": False, "precision_at_k": 0.0, "recall_at_k": 0.0,
                "abstention_correct": False if not gold else None, "error": True,
                "returned": 0, "relevant_returned": 0, "expected": len(gold),
                "unsupported_hits": 0, "temporal_leaks": 0, "support_exact": False, "scope_exact": False}
    output, view = result["output"], result["input_view"]
    hits = output.get("hits", [])
    ids = [hit.get("observation_id") for hit in hits]
    found = set(ids)
    rows = {row["id"]: row for row in view["observations"]}
    sources = {source["id"]: source for source in view["sources"]}
    unsupported, leaks = [], []
    fields = ("source_id", "metric", "value", "unit", "date", "source_span", "available_at", "reported_at")
    for hit in hits:
        key = hit.get("observation_id")
        row = rows.get(key)
        if row is None:
            unsupported.append(key)
            leaks.append(key)
            continue
        if any(hit.get(field) != row.get(field) for field in fields) or hit.get("source_title") != sources[row["source_id"]]["title"]:
            unsupported.append(key)
        if row["date"] > view["scope"]["as_of"] or datetime.fromisoformat(row["available_at"].replace("Z", "+00:00")) > datetime.fromisoformat(view["scope"]["known_at"].replace("Z", "+00:00")):
            leaks.append(key)
    relevant = len(found & gold)
    precision = relevant / len(ids) if ids else (1.0 if not gold else 0.0)
    recall = relevant / len(gold) if gold else (1.0 if not ids else 0.0)
    scope_exact = output.get("scope") == view["scope"]
    duplicate_count = len(ids) - len(found)
    bounded = len(ids) <= case["limit"]
    support = not unsupported and not leaks and scope_exact and not duplicate_count and bounded
    return {"exact": found == gold and support, "precision_at_k": precision, "recall_at_k": recall,
            "abstention_correct": not ids if not gold else None, "error": False,
            "returned": len(ids), "relevant_returned": relevant, "expected": len(gold),
            "unsupported_hits": len(unsupported), "unsupported_ids": unsupported,
            "temporal_leaks": len(leaks), "temporal_leak_ids": leaks,
            "support_exact": support, "scope_exact": scope_exact, "duplicate_ids": duplicate_count, "bounded": bounded}


def summarize(cases):
    mapping = [case["grade"] for case in cases if case["kind"] != "retrieval"]
    retrieval = [case["grade"] for case in cases if case["kind"] == "retrieval"]
    dimensions = [value for grade in mapping for value in grade.get("dimensions", {}).values()]
    answerable = [grade for grade in retrieval if grade["expected"]]
    negative = [grade for grade in retrieval if not grade["expected"]]
    total_hits = sum(g["returned"] for g in retrieval)
    unsupported_hits = sum(g["unsupported_hits"] for g in retrieval)
    return {
        "scheduled": len(cases), "completed": sum(case["status"] == "completed" for case in cases),
        "errors": sum(case["status"] != "completed" for case in cases),
        "mapping": {"scheduled": len(mapping), "comparable_exact": sum(g["comparable_exact"] for g in mapping),
                    "full_contract_exact": sum(g["contract_exact"] for g in mapping),
                    "dimensions_expected": len(dimensions), "dimensions_available": sum(g["available"] for g in dimensions),
                    "dimensions_correct": sum(g["correct"] for g in dimensions)},
        "retrieval": {"scheduled": len(retrieval), "exact": sum(g["exact"] for g in retrieval),
                      "macro_precision_at_5": sum(g["precision_at_k"] for g in retrieval) / len(retrieval) if retrieval else None,
                      "macro_recall_at_5": sum(g["recall_at_k"] for g in retrieval) / len(retrieval) if retrieval else None,
                      "answerable_cases": len(answerable), "answerable_macro_recall_at_5": sum(g["recall_at_k"] for g in answerable) / len(answerable) if answerable else None,
                      "abstention_cases": len(negative), "correct_abstentions": sum(g["abstention_correct"] for g in negative),
                      "returned_hits": total_hits, "unsupported_hits": unsupported_hits,
                      "hit_support_precision": (total_hits - unsupported_hits) / total_hits if total_hits else None,
                      "temporal_leaks": sum(g["temporal_leaks"] for g in retrieval), "supported_cases": sum(g["support_exact"] for g in retrieval),
                      "scope_exact_cases": sum(g["scope_exact"] for g in retrieval)}}


def run_subprocess(payload, directory):
    path = Path(directory) / (payload["method"] + "-input.json")
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    env = {key: value for key, value in os.environ.items()
           if not any(word in key.upper() for word in ("TOKEN", "SECRET", "API_KEY", "PASSWORD"))}
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        completed = subprocess.run([sys.executable, "-I", str(Path(__file__).absolute()), "--worker", str(path)],
                                   cwd=directory, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
        if completed.returncode:
            raise RuntimeError("Worker failed: " + completed.stderr[-1800:])
        return json.loads(completed.stdout)
    except Exception as exc:
        return {"method": payload["method"], "blocked_accesses": [], "results": [
            {"id": c["id"], "kind": c["kind"], "status": "error", "error": {"type": type(exc).__name__, "message": str(exc)}}
            for c in payload["cases"] if payload["method"] != "lexical" or c["kind"] == "retrieval"]}


def comparable_view(view):
    """Bundle-derived scope IDs may differ; captured bounds and evidence must not."""
    if not view:
        return None
    fields = ("id", "source_id", "metric", "value", "unit", "date", "source_span", "available_at", "reported_at")
    return {"scope": {key: view["scope"][key] for key in ("as_of", "known_at", "captured_at")},
            "observations": sorted([{key: row.get(key) for key in fields} for row in view["observations"]], key=lambda row: row["id"]),
            "sources": sorted([{key: source.get(key) for key in ("id", "title", "content", "available_at")} for source in view["sources"]], key=lambda source: source["id"])}


def evaluate(*, plan_only=False, candidate_only=False, output=REPORT):
    protocol = None
    if not candidate_only:
        with access_tripwire([PROTOCOL]):
            protocol = baseline_manifest()
    allowed = ([PROTOCOL] + [BASELINE / "source" / name for name in protocol["source_sha256"]]) if protocol else []
    with access_tripwire(allowed) as access:
        fixture = load_fixture()
        with tempfile.TemporaryDirectory(prefix="modus-ontology-evaluation-") as tmp:
            frozen = Path(tmp) / "frozen-source"
            if protocol:
                copy_verified_baseline(PROTOCOL, frozen)
            identity = {"fixture_sha256": FIXTURE_SHA256, "grading_sha256": GRADING_SHA256,
                        "baseline_source_id": protocol["source_id"] if protocol else None,
                        "comparison_mode": "candidate_only_no_baseline" if candidate_only else "prefeature_comparison",
                        "harness_sha256": sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n"))}
            schedule = [("candidate", ROOT)] if candidate_only else [("baseline", frozen), ("lexical", frozen), ("candidate", ROOT)]
            if plan_only:
                return {"format": "modus-ontology-rag-plan-v1", **identity, "cases": len(fixture["cases"]),
                        "methods": [method for method, _ in schedule], "provider_requests": 0, "blocked_accesses": access["blocked"]}
            runs = []
            for method, source_root in schedule:
                run = run_subprocess(input_payload(fixture, method, source_root), tmp)
                indexed = {item["id"]: item for item in run["results"]}
                graded = []
                for case in fixture["cases"]:
                    if method == "lexical" and case["kind"] != "retrieval":
                        continue
                    result = indexed.get(case["id"], {"id": case["id"], "kind": case["kind"], "status": "error", "error": {"type": "MissingResult"}})
                    grade = grade_retrieval(case, result) if case["kind"] == "retrieval" else grade_mapping(case, result)
                    graded.append({**result, "category": case["category"], "grade": grade})
                run["results"], run["summary"] = graded, summarize(graded)
                runs.append(run)
            baseline_views = {r["id"]: comparable_view(r.get("input_view")) for r in runs[0]["results"] if r["kind"] == "retrieval"}
            scope_alignment = {run["method"]: {r["id"]: comparable_view(r.get("input_view")) == baseline_views[r["id"]] and baseline_views[r["id"]] is not None
                               for r in run["results"] if r["kind"] == "retrieval"} for run in runs[1:]}
            report = {"format": "modus-ontology-rag-development-result-v1", "created_at": datetime.now(timezone.utc).isoformat(),
                      "split": "development", **identity, "grading_contract": GRADING_CONTRACT,
                      "provider_requests": 0, "private_corpus_access": "blocked by path tripwire", "blocked_accesses": access["blocked"],
                      "matched_scopes_and_evidence": scope_alignment,
                      "limitations": (["Candidate-only mode: no baseline source was read or executed; this run cannot establish improvement over the pre-feature code."] if candidate_only else []) + ["24 authored development cases, not held-out generalization or clinical validation.",
                                      "Baseline mapping is coarse metric_key/parse_fhir; missing formal dimensions are reported separately.",
                                      "Baseline retrieval is actual offline route/tool evidence, not a historical ranked retrieval API.",
                                      "Plain lexical comparator deliberately has no ontology expansion or unsafe-query policy.",
                                      "Scope IDs differ by source bundle; bounds and fixture source content are held constant.",
                                      "Follow-up fixes after these outcomes are development tuning; preserve initial output."], "runs": runs}
            output = Path(output)
            output.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            retained = output.with_name(output.stem + "-" + stamp + output.suffix)
            report["retained_report"] = retained.name
            raw = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            with retained.open("x", encoding="utf-8") as handle:
                handle.write(raw)
            output.write_text(raw, encoding="utf-8")
            return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--candidate-only", action="store_true", help="Evaluate current source against frozen development gold without reading or claiming a baseline comparison")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        sys.stdout.reconfigure(encoding="utf-8")
        result = worker(json.loads(args.worker.read_text(encoding="utf-8")))
        print(json.dumps(result, ensure_ascii=False))
        return
    result = evaluate(plan_only=args.plan, candidate_only=args.candidate_only)
    if args.plan:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({"retained_report": result["retained_report"], **{r["method"]: r["summary"] for r in result["runs"]}}, indent=2))


if __name__ == "__main__":
    main()
