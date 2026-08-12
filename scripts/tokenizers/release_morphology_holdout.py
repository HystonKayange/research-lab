#!/usr/bin/env python3
"""Release locked morphology holdout — only after explicit method freeze.

Ordinary use without --confirm-method-freeze is refused.
This task must not release the holdout.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import load_json, sha256_text, utc_now_iso, write_json, write_jsonl, write_text  # noqa: E402

TOOL_NAME = "release_morphology_holdout"
TOOL_VERSION = "0.1.0"


def refuse_test(path: Path | str) -> None:
    if "/test/" in str(path).replace("\\", "/"):
        raise RuntimeError(f"refusing test path: {path}")


def load_sealed(path: Path) -> list[dict[str, Any]]:
    sealed = load_json(path)
    if sealed.get("format") != "mthandizi_morphology_holdout_seal_v1":
        raise ValueError("unknown seal format")
    raw = base64.b64decode(sealed["payload_b64"].encode("ascii")).decode("utf-8")
    if sha256_text(raw) != sealed["sha256"]:
        raise ValueError("payload checksum mismatch")
    items = json.loads(raw)
    if not isinstance(items, list):
        raise ValueError("payload not a list")
    return items


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Release morphology holdout after method freeze (blocked by default)."
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--benchmark-root",
        type=Path,
        default=Path("data/research/morphology_benchmark_v0.1"),
    )
    p.add_argument(
        "--confirm-method-freeze",
        action="store_true",
        help="Required. Confirms tokenizer method is frozen and holdout may be released.",
    )
    p.add_argument(
        "--i-understand-this-is-irreversible-for-design",
        action="store_true",
        help="Required second confirmation.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Where to write released JSONL (default: locked/released/ under benchmark).",
    )
    p.add_argument(
        "--status-only",
        action="store_true",
        help="Print lock status without releasing.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    bench = (
        args.benchmark_root
        if args.benchmark_root.is_absolute()
        else root / args.benchmark_root
    )
    locked = bench / "locked"
    refuse_test(bench)

    blocked = locked / "RELEASE_BLOCKED"
    sealed_path = locked / "holdout_payload.sealed.json"
    man_path = locked / "holdout_manifest.json"

    if args.status_only:
        man = load_json(man_path) if man_path.is_file() else {}
        print(
            json.dumps(
                {
                    "release_blocked_file": blocked.is_file(),
                    "n_items": man.get("n_items"),
                    "released": man.get("released", False),
                    "status": man.get("status", "UNKNOWN"),
                },
                indent=2,
            )
        )
        return 0

    if not args.confirm_method_freeze or not args.i_understand_this_is_irreversible_for_design:
        print(
            "REFUSED: morphology holdout remains locked.\n"
            "Both flags required after method freeze:\n"
            "  --confirm-method-freeze\n"
            "  --i-understand-this-is-irreversible-for-design\n"
            "Use --status-only to inspect counts without release.",
            file=sys.stderr,
        )
        return 2

    if not sealed_path.is_file():
        print(f"missing sealed payload: {sealed_path}", file=sys.stderr)
        return 1

    items = load_sealed(sealed_path)
    out_dir = (
        args.output_dir
        if args.output_dir
        else locked / "released"
    )
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = out_dir / "holdout_annotation_candidates.jsonl"
    write_jsonl(out_jsonl, items)

    man = load_json(man_path) if man_path.is_file() else {}
    man["released"] = True
    man["status"] = "RELEASED"
    man["released_at"] = utc_now_iso()
    man["released_by_tool"] = {"name": TOOL_NAME, "version": TOOL_VERSION}
    man["released_path"] = str(out_jsonl)
    write_json(man_path, man)

    # remove or rewrite RELEASE_BLOCKED
    write_text(
        locked / "RELEASE_BLOCKED",
        f"RELEASED at {man['released_at']}\n"
        f"path: {out_jsonl}\n"
        "Do not use for new method design after freeze.\n",
    )
    print(f"Released {len(items)} holdout items to {out_jsonl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
