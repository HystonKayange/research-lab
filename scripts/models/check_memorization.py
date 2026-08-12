#!/usr/bin/env python3
"""Corpus memorization diagnostics for LM generations (not privacy claims)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lm_common import (  # noqa: E402
    load_json,
    longest_common_substring_len,
    ngram_overlap,
    write_json,
)

TOOL_NAME = "check_memorization"
TOOL_VERSION = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Memorization diagnostics on generations.")
    p.add_argument("--config", type=Path, default=Path("configs/models/lm_baselines_v0_1.json"))
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--train-text", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config = load_json(
        args.config if args.config.is_absolute() else root / args.config
    )
    run_dir = args.run_dir if args.run_dir.is_absolute() else root / args.run_dir
    gen_path = run_dir / "generations.jsonl"
    if not gen_path.is_file():
        print(f"error: missing {gen_path}", file=sys.stderr)
        return 1

    train_path = (
        args.train_text
        if args.train_text
        else root / config["split_root"] / "train" / "combined.txt"
    )
    train = train_path.read_text(encoding="utf-8")
    # use a moderate slice for expensive LCS
    train_scan = train[:400_000]

    rows: list[dict[str, Any]] = []
    for line in gen_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        g = json.loads(line)
        cont = g.get("generation") or ""
        # strip prompt if present at start
        prompt = g.get("prompt") or ""
        if cont.startswith(prompt):
            cont_only = cont[len(prompt) :]
        else:
            cont_only = cont
        lcs = longest_common_substring_len(cont_only, train_scan, max_scan=20000)
        ov5 = ngram_overlap(cont_only, train_scan, n=5)
        ov8 = ngram_overlap(cont_only, train_scan, n=8)
        flag = "near_verbatim" if lcs >= 80 or ov8 > 0.4 else (
            "formulaic_or_overlap" if lcs >= 40 or ov5 > 0.25 else "likely_original_or_common"
        )
        rows.append(
            {
                "review_id": g.get("review_id"),
                "model_id": g.get("model_id"),
                "prompt": prompt,
                "generation_len_chars": len(cont),
                "longest_exact_train_substring_chars": lcs,
                "ngram5_overlap": ov5,
                "ngram8_overlap": ov8,
                "flag": flag,
                "note": (
                    "Diagnostic only — distinguishes fluent generation vs formulaic "
                    "phrases vs near-verbatim train matches. Not a privacy claim."
                ),
            }
        )

    out = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "train_path": str(train_path.relative_to(root) if train_path.is_relative_to(root) else train_path),
        "n": len(rows),
        "results": rows,
        "summary": {
            "near_verbatim": sum(1 for r in rows if r["flag"] == "near_verbatim"),
            "formulaic_or_overlap": sum(1 for r in rows if r["flag"] == "formulaic_or_overlap"),
            "likely_original_or_common": sum(
                1 for r in rows if r["flag"] == "likely_original_or_common"
            ),
        },
    }
    write_json(run_dir / "memorization.json", out)
    print(json.dumps(out["summary"], indent=2))
    print(f"wrote {run_dir / 'memorization.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
