#!/usr/bin/env python3
"""Train a deterministic character-level tokenizer on the frozen train split only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import (  # noqa: E402
    CharacterTokenizer,
    ensure_output_not_exists,
    git_commit,
    load_json,
    normalization_audit,
    platform_info,
    sha256_file,
    sha256_json,
    utc_now_iso,
    verify_frozen_split,
    write_json,
    write_text,
)

TOOL_NAME = "train_character_tokenizer"
TOOL_VERSION = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train character tokenizer on train split only.")
    p.add_argument("--config", type=Path, default=Path("configs/tokenizers/baselines_v0_1.json"))
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--force", action="store_true", help="Overwrite (discouraged).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)

    split_root = root / config["split_root"]
    verify_frozen_split(split_root, config)

    train_path = root / config["training_inputs"]["combined"]
    if not train_path.is_file():
        print(f"error: missing training file {train_path}", file=sys.stderr)
        return 1
    # safety: path must include /train/
    if "/train/" not in str(train_path).replace("\\", "/"):
        print("error: training path must be under train/", file=sys.stderr)
        return 1

    out_root = root / config["output_root"] / "character"
    try:
        ensure_output_not_exists(out_root, force=args.force)
    except FileExistsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.force and out_root.exists():
        import shutil

        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    text = train_path.read_text(encoding="utf-8")
    sample = text.splitlines()[:50]
    audit = normalization_audit(sample, config["normalization"]["policy"])
    if audit["n_changed"] != 0 and config["normalization"]["policy"] == "identity":
        print("error: identity normalization changed text", file=sys.stderr)
        return 1

    specials = list(config["character"]["special_token_order"])
    tok = CharacterTokenizer.train_from_text(text, specials=specials)

    vocab = tok.to_dict()
    write_json(out_root / "vocab.json", {
        "itos": vocab["itos"],
        "stoi": vocab["stoi"],
        "vocab_size": vocab["vocab_size"],
    })
    tok_cfg = {
        "type": "character",
        "tokenizer_id": config["character"]["tokenizer_id"],
        "special_tokens": config["special_tokens"],
        "unknown_behavior": config["character"]["unknown_behavior"],
        "whitespace": config["character"]["whitespace"],
        "vocab_order": config["character"]["vocab_order"],
        "normalization": config["normalization"],
        "pad_id": tok.stoi["<pad>"],
        "unk_id": tok.stoi["<unk>"],
        "bos_id": tok.stoi["<bos>"],
        "eos_id": tok.stoi["<eos>"],
        "vocab_size": len(tok.itos),
    }
    write_json(out_root / "tokenizer_config.json", tok_cfg)

    info = platform_info()
    info["git_commit"] = git_commit(root)
    manifest = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "created_at": utc_now_iso(),
        "experiment_id": config["experiment_id"],
        "tokenizer_id": "character",
        "training_input": str(train_path.relative_to(root)),
        "training_input_sha256": sha256_file(train_path),
        "config_path": str(config_path.relative_to(root) if config_path.is_relative_to(root) else config_path),
        "config_sha256": sha256_file(config_path),
        "vocab_size": len(tok.itos),
        "n_special_tokens": len(specials),
        "n_character_types": len(tok.itos) - len(specials),
        "normalization_audit": audit,
        "platform": info,
        "artifacts": {
            "vocab.json": sha256_file(out_root / "vocab.json"),
            "tokenizer_config.json": sha256_file(out_root / "tokenizer_config.json"),
        },
        "frozen_split_check": {
            "split_root": config["split_root"],
            "verified": True,
        },
        "disclaimers": [
            "Vocabulary learned from train split only.",
            "Validation/test characters not in train map to <unk>.",
            "Not a morphology-aware tokenizer.",
        ],
    }
    write_json(out_root / "manifest.json", manifest)
    # update artifact checksums with manifest
    manifest["artifacts"]["manifest.json"] = sha256_file(out_root / "manifest.json")
    write_json(out_root / "manifest.json", manifest)

    write_text(
        out_root / "README.md",
        "# Character tokenizer (baselines_v0.1)\n\n"
        f"Vocab size: {len(tok.itos)} (including specials).\n"
        f"Train input: `{train_path.relative_to(root)}`\n"
        "Unknown characters → `<unk>`.\n",
    )

    print(f"Character tokenizer trained → {out_root}")
    print(f"  vocab_size={len(tok.itos)} specials={specials}")
    print(f"  train_sha256={manifest['training_input_sha256'][:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
