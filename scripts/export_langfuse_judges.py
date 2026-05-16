#!/usr/bin/env python3
"""Export WoS Langfuse judge definitions for local Langfuse UI bootstrap."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_stack.langfuse_evaluator_transfer import (
    build_local_langfuse_judge_transfer_bundle,
    render_local_langfuse_judge_transfer_markdown,
)


DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "generated" / "langfuse"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export canonical WoS LLM-as-a-Judge definitions for local Langfuse.",
    )
    parser.add_argument(
        "--environment",
        default="local",
        help="Langfuse environment filter to stamp into the transfer bundle.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for JSON and Markdown export files.",
    )
    parser.add_argument(
        "--no-prompts",
        action="store_true",
        help="Omit prompt bodies from the JSON bundle.",
    )
    args = parser.parse_args()

    environment = str(args.environment or "local").strip() or "local"
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = (REPO_ROOT / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle = build_local_langfuse_judge_transfer_bundle(
        environment=environment,
        include_prompts=not bool(args.no_prompts),
    )
    json_path = output_dir / f"langfuse_judge_transfer.{environment}.json"
    md_path = output_dir / f"langfuse_judge_transfer.{environment}.md"
    json_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_local_langfuse_judge_transfer_markdown(bundle), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"Judges: {bundle['judge_count']}")


if __name__ == "__main__":
    main()
