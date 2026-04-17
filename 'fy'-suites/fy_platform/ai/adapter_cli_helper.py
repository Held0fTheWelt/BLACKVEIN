from __future__ import annotations

import argparse
import json
from typing import Callable, Sequence


def run_adapter_cli(adapter_factory: Callable[[], object], argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Autark suite adapter CLI')
    parser.add_argument('command', choices=['init', 'inspect', 'audit', 'explain', 'prepare-context-pack', 'compare-runs', 'clean', 'reset', 'triage', 'prepare-fix'])
    parser.add_argument('--target-repo', default='')
    parser.add_argument('--query', default='')
    parser.add_argument('--audience', default='developer')
    parser.add_argument('--left-run-id', default='')
    parser.add_argument('--right-run-id', default='')
    parser.add_argument('--mode', default='standard')
    parser.add_argument('--finding-id', action='append', default=[])
    args = parser.parse_args(list(argv) if argv is not None else None)
    adapter = adapter_factory()
    if args.command == 'init':
        out = adapter.init(args.target_repo or None)
    elif args.command == 'inspect':
        out = adapter.inspect(args.query or None)
    elif args.command == 'audit':
        out = adapter.audit(args.target_repo)
    elif args.command == 'explain':
        out = adapter.explain(args.audience)
    elif args.command == 'prepare-context-pack':
        out = adapter.prepare_context_pack(args.query, args.audience)
    elif args.command == 'compare-runs':
        out = adapter.compare_runs(args.left_run_id, args.right_run_id)
    elif args.command == 'clean':
        out = adapter.clean(args.mode)
    elif args.command == 'reset':
        out = adapter.reset(args.mode)
    elif args.command == 'triage':
        out = adapter.triage(args.query or None)
    elif args.command == 'prepare-fix':
        out = adapter.prepare_fix(args.finding_id)
    else:
        parser.error('unsupported command')
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0
