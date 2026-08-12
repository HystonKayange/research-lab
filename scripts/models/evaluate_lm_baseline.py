#!/usr/bin/env python3
"""Evaluate a trained LM checkpoint on validation and/or test (test only after selection lock)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lm_common import (  # noqa: E402
    build_gpt,
    load_json,
    load_tokenizer,
    pack_lines_to_sequences,
    sequences_to_tensors,
    sha256_file,
    bits_per_byte,
    bits_per_character,
    token_perplexity_from_nll,
    verify_frozen_split,
    write_json,
)
from train_lm_baseline import evaluate_split  # noqa: E402

TOOL_NAME = "evaluate_lm_baseline"
TOOL_VERSION = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate LM baseline checkpoint.")
    p.add_argument("--config", type=Path, default=Path("configs/models/lm_baselines_v0_1.json"))
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--run-dir", type=Path, required=True, help="Path to seed run directory")
    p.add_argument(
        "--splits",
        nargs="+",
        default=["validation"],
        choices=["validation", "test", "bible_validation", "bible_test", "wikipedia_validation", "wikipedia_test"],
    )
    p.add_argument(
        "--allow-test",
        action="store_true",
        help="Required to evaluate test (selection must already be locked).",
    )
    p.add_argument("--checkpoint", default="best.pt")
    p.add_argument("--device", default=None)
    return p.parse_args(argv)


def load_model_from_ckpt(ckpt_path: Path, device):
    import torch

    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    arch = ckpt["arch"]
    vocab_size = int(ckpt.get("vocab_size") or 0)
    if vocab_size <= 0:
        # infer from embedding
        vocab_size = ckpt["model"]["wte.weight"].shape[0]
    model = build_gpt(
        vocab_size=vocab_size,
        n_layer=int(arch["n_layer"]),
        n_embd=int(arch["n_embd"]),
        n_head=int(arch["n_head"]),
        n_inner=int(arch["n_inner"]),
        context_length=int(arch["context_length"]),
        dropout=0.0,
        tie_embeddings=bool(arch.get("tie_embeddings", True)),
        pre_ln=bool(arch.get("pre_ln", True)),
    ).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model, ckpt


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config = load_json(
        args.config if args.config.is_absolute() else root / args.config
    )
    run_dir = args.run_dir if args.run_dir.is_absolute() else root / args.run_dir
    man = load_json(run_dir / "manifest.json")
    tok_id = man["tokenizer_id"]

    if any("test" in s for s in args.splits) and not args.allow_test:
        print(
            "error: test evaluation requires --allow-test after selection lock",
            file=sys.stderr,
        )
        return 1

    try:
        import torch
    except ImportError:
        print("error: torch required", file=sys.stderr)
        return 2

    device = torch.device(
        args.device
        if args.device
        else ("cuda" if torch.cuda.is_available() else "cpu")
    )
    verify_frozen_split(root / config["split_root"])
    tokenizer = load_tokenizer(config["tokenizers"][tok_id], root)
    model, ckpt = load_model_from_ckpt(run_dir / args.checkpoint, device)
    arch = ckpt["arch"]
    split_root = root / config["split_root"]

    results: dict[str, Any] = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "run_dir": str(run_dir),
        "checkpoint": args.checkpoint,
        "checkpoint_sha256": sha256_file(run_dir / args.checkpoint),
        "tokenizer_id": tok_id,
        "splits": {},
    }

    path_map = {
        "validation": split_root / "validation" / "combined.txt",
        "test": split_root / "test" / "combined.txt",
        "bible_validation": split_root / "validation" / "bible.txt",
        "bible_test": split_root / "test" / "bible.txt",
        "wikipedia_validation": split_root / "validation" / "wikipedia.txt",
        "wikipedia_test": split_root / "test" / "wikipedia.txt",
    }

    for name in args.splits:
        path = path_map[name]
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        seqs, meta, _, _credits = pack_lines_to_sequences(
            lines,
            tokenizer,
            context_length=int(arch["context_length"]),
            eos_between_lines=True,
        )
        metrics = evaluate_split(
            model,
            seqs,
            pad_id=tokenizer.pad_id,
            device=device,
            batch_size=int(config["evaluation"]["eval_batch_size"]),
            source_text=text,
            amp=False,
            dtype=torch.float32,
        )
        metrics["packing"] = meta.__dict__
        metrics["source_path"] = str(path.relative_to(root))
        results["splits"][name] = metrics
        print(
            f"{name}: BPC={metrics['bits_per_character']:.4f} "
            f"BPB={metrics['bits_per_byte']:.4f}"
        )

    out = run_dir / "eval_metrics.json"
    # merge if exists
    if out.is_file():
        prev = load_json(out)
        prev.setdefault("splits", {}).update(results["splits"])
        prev["checkpoint_sha256"] = results["checkpoint_sha256"]
        results = prev
    write_json(out, results)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
