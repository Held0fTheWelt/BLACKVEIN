#!/usr/bin/env python3
"""Generic LLM baseline chat for MVP comparative evaluation (Phase 2, roadmap).

This is **not** the World of Shadows runtime. It is a deliberately plain multi-turn
chat loop against a chat-completions API, using a fixed opening brief aligned with
the God of Carnage slice *premise* (see ``scripts/data/mvp_goc_baseline_opening.json``).

Purpose:
  - Arm B of the controlled comparison (same evaluator goal framing, no engine authority).
  - Keeps retrieval, validation, and commit out of the baseline path by design.

Requirements:
  - ``httpx`` (same as backend stack).
  - ``OPENAI_API_KEY`` in the environment (or ``--api-key``).
  - Optional ``OPENAI_BASE_URL`` for compatible endpoints (default ``https://api.openai.com``).

Usage:
  python scripts/mvp_generic_llm_baseline_chat.py --print-opening
  python scripts/mvp_generic_llm_baseline_chat.py --model gpt-4o-mini
  python scripts/mvp_generic_llm_baseline_chat.py --max-turns 8
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "scripts" / "data" / "mvp_goc_baseline_opening.json"


def load_opening_bundle(path: Path = DATA_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing baseline opening data: {path}")
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("Opening bundle must be a JSON object")
    return raw


def build_initial_messages(bundle: dict[str, Any]) -> list[dict[str, str]]:
    system = str(bundle.get("arm_b_system_prompt") or "").strip()
    opening = str(bundle.get("opening_narration") or "").strip()
    goal = str(bundle.get("evaluator_goal_framing") or "").strip()
    role = str(bundle.get("player_role_hint") or "").strip()
    if not system or not opening:
        raise ValueError("Bundle must include arm_b_system_prompt and opening_narration")
    user_parts = []
    if goal:
        user_parts.append(f"Evaluator goal framing:\n{goal}")
    if role:
        user_parts.append(role)
    user_parts.append(f"Opening:\n{opening}")
    user_content = "\n\n".join(user_parts)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


def complete_chat(
    messages: list[dict[str, str]],
    *,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float,
    timeout_s: float,
) -> str:
    import httpx

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    with httpx.Client(timeout=timeout_s) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("API returned no choices")
    msg = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Empty assistant content in API response")
    return content.strip()


def run_repl(
    *,
    api_key: str,
    base_url: str,
    model: str,
    temperature: float,
    max_turns: int | None,
    timeout_s: float,
) -> None:
    bundle = load_opening_bundle()
    messages = build_initial_messages(bundle)
    print("--- MVP generic baseline (Arm B) — type exit or quit to stop ---\n")
    print(bundle.get("evaluator_goal_framing", ""), end="\n\n")
    assistant = complete_chat(
        messages,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        timeout_s=timeout_s,
    )
    messages.append({"role": "assistant", "content": assistant})
    print(f"Assistant:\n{assistant}\n")

    turn = 0
    while max_turns is None or turn < max_turns:
        try:
            line = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[session end]")
            break
        if not line:
            continue
        low = line.lower()
        if low in ("exit", "quit", ":q"):
            break
        messages.append({"role": "user", "content": line})
        assistant = complete_chat(
            messages,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            timeout_s=timeout_s,
        )
        messages.append({"role": "assistant", "content": assistant})
        print(f"\nAssistant:\n{assistant}\n")
        turn += 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generic LLM baseline REPL for MVP comparison")
    p.add_argument("--print-opening", action="store_true", help="Print frozen bundle fields and exit")
    p.add_argument("--model", default=os.environ.get("MVP_BASELINE_MODEL", "gpt-4o-mini"))
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-turns", type=int, default=None, help="Max player turns after opening reply")
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    p.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com"))
    args = p.parse_args(argv)

    if args.print_opening:
        bundle = load_opening_bundle()
        # stdout: machine-readable JSON only (tests and tooling may parse this)
        print(json.dumps(bundle, indent=2, ensure_ascii=False))
        msgs = build_initial_messages(bundle)
        print("\n--- Initial messages (roles) ---", file=sys.stderr)
        for m in msgs:
            role = m["role"]
            preview = m["content"][:400] + ("…" if len(m["content"]) > 400 else "")
            print(f"[{role}]\n{preview}\n", file=sys.stderr)
        return 0

    if not str(args.api_key or "").strip():
        print("OPENAI_API_KEY is required (or pass --api-key).", file=sys.stderr)
        return 2

    try:
        run_repl(
            api_key=str(args.api_key).strip(),
            base_url=str(args.base_url).strip(),
            model=str(args.model).strip(),
            temperature=float(args.temperature),
            max_turns=args.max_turns,
            timeout_s=float(args.timeout),
        )
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
