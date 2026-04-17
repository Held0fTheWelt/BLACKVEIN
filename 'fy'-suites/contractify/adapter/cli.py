from __future__ import annotations

from fy_platform.ai.adapter_cli_helper import run_adapter_cli
from contractify.adapter.service import ContractifyAdapter


def main(argv=None) -> int:
    return run_adapter_cli(ContractifyAdapter, argv)


if __name__ == '__main__':
    raise SystemExit(main())
