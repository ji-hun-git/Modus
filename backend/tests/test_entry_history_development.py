"""The expanded record workflow must satisfy the authored development contract."""
import importlib.util
from pathlib import Path


def test_whole_history_development_contract():
    path = Path(__file__).resolve().parents[2] / 'scripts/evaluate_history_agent.py'
    spec = importlib.util.spec_from_file_location('history_development', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.evaluate()
    assert report['status'] == 'passed'
    assert report['summary']['whole_history'] == {'passed': 16, 'total': 16}
    assert report['cases'][0]['legacy_three_metric']['passed']
    assert report['provider_requests_made'] == 0
    assert report['heldout_executed'] is False
