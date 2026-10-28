"""Run with python -m eval.judges.cli; preparation is the default."""
import argparse
import asyncio
import json
from pathlib import Path

from .runner import run

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--models', type=Path, default=Path(__file__).with_name('models.yaml'))
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--allow-network', action='store_true')
    parser.add_argument('--human-labels', type=Path)
    args = parser.parse_args(argv)
    result = asyncio.run(run(args.input, args.models, execute=args.execute, allow_network=args.allow_network,
        private_root=ROOT / 'evaluation/jury', report_root=ROOT / 'eval', human_path=args.human_labels))
    # Reports contain only bounded metadata/scores, never provider prose or keys.
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit('Jury stopped before a valid report: ' + type(error).__name__) from None
