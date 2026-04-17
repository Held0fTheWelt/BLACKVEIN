from __future__ import annotations

import argparse
import json
from typing import Sequence

from contractify.adapter.service import ContractifyAdapter
from testify.adapter.service import TestifyAdapter
from documentify.adapter.service import DocumentifyAdapter
from docify.adapter.service import DocifyAdapter
from despaghettify.adapter.service import DespaghettifyAdapter
from dockerify.adapter.service import DockerifyAdapter
from postmanify.adapter.service import PostmanifyAdapter

SUITES = {
    'contractify': ContractifyAdapter,
    'testify': TestifyAdapter,
    'documentify': DocumentifyAdapter,
    'docify': DocifyAdapter,
    'despaghettify': DespaghettifyAdapter,
    'dockerify': DockerifyAdapter,
    'postmanify': PostmanifyAdapter,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run autark fy suite adapters against an outward target repository.')
    parser.add_argument('suite', choices=sorted(SUITES))
    parser.add_argument('command', choices=['init', 'inspect', 'audit', 'explain', 'prepare-context-pack', 'compare-runs', 'clean', 'reset', 'triage', 'prepare-fix'])
    parser.add_argument('--target-repo', default='')
    parser.add_argument('--query', default='')
    parser.add_argument('--audience', default='developer')
    parser.add_argument('--left-run-id', default='')
    parser.add_argument('--right-run-id', default='')
    parser.add_argument('--mode', default='standard')
    parser.add_argument('--finding-id', action='append', default=[])
    args = parser.parse_args(list(argv) if argv is not None else None)

    adapter = SUITES[args.suite]()
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
