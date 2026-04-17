from __future__ import annotations

from fy_platform.ai.adapter_cli_helper import run_adapter_cli
from dockerify.adapter.service import DockerifyAdapter


def main(argv=None) -> int:
    return run_adapter_cli(DockerifyAdapter, argv)


if __name__ == '__main__':
    raise SystemExit(main())
