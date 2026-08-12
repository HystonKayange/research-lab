#!/usr/bin/env python3
"""Train SentencePiece BPE and Unigram baselines on frozen train split only."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import (  # noqa: E402
    ensure_output_not_exists,
    git_commit,
    load_json,
    normalization_audit,
    platform_info,
    sentencepiece_version,
    sha256_file,
    utc_now_iso,
    verify_frozen_split,
    write_json,
    write_text,
)

TOOL_NAME = "train_sentencepiece_baselines"
TOOL_VERSION = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train SentencePiece BPE/Unigram baselines.")
    p.add_argument("--config", type=Path, default=Path("configs/tokenizers/baselines_v0_1.json"))
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--model-type",
        choices=["bpe", "unigram", "all"],
        default="all",
    )
    p.add_argument("--force", action="store_true")
    return p.parse_args(argv)


def train_one(
    *,
    root: Path,
    config: dict,
    config_path: Path,
    model_type: str,
    vocab_size: int,
    train_path: Path,
    force: bool,
) -> Path:
    try:
        import sentencepiece as spm  # type: ignore
    except ImportError as e:
        raise ImportError(
            "Missing dependency: sentencepiece. "
            "Install with: .venv/bin/pip install -r requirements-tokenizers.txt"
        ) from e

    out_dir = (
        root
        / config["output_root"]
        / model_type
        / f"vocab_{vocab_size}"
    )
    if out_dir.exists() and any(out_dir.iterdir()) and not force:
        raise FileExistsError(f"Exists: {out_dir}")
    if force and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sp_cfg = config["sentencepiece"]
    prefix = out_dir / "model"
    # Explicit recorded parameters — no silent defaults for key knobs
    train_kwargs = {
        "input": str(train_path),
        "model_prefix": str(prefix),
        "vocab_size": int(vocab_size),
        "model_type": model_type,
        "character_coverage": float(sp_cfg["character_coverage"]),
        "normalization_rule_name": str(sp_cfg["normalization_rule_name"]),
        "byte_fallback": bool(sp_cfg["byte_fallback"]),
        "split_by_unicode_script": bool(sp_cfg["split_by_unicode_script"]),
        "split_by_number": bool(sp_cfg["split_by_number"]),
        "split_by_whitespace": bool(sp_cfg["split_by_whitespace"]),
        "treat_whitespace_as_suffix": bool(sp_cfg["treat_whitespace_as_suffix"]),
        "allow_whitespace_only_pieces": bool(sp_cfg["allow_whitespace_only_pieces"]),
        "remove_extra_whitespaces": bool(sp_cfg["remove_extra_whitespaces"]),
        "add_dummy_prefix": bool(sp_cfg["add_dummy_prefix"]),
        "hard_vocab_limit": bool(sp_cfg["hard_vocab_limit"]),
        "input_sentence_size": int(sp_cfg["input_sentence_size"]),
        "shuffle_input_sentence": bool(sp_cfg["shuffle_input_sentence"]),
        "num_threads": int(sp_cfg["num_threads"]),
        "max_sentence_length": int(sp_cfg["max_sentence_length"]),
        "pad_id": int(sp_cfg["pad_id"]),
        "unk_id": int(sp_cfg["unk_id"]),
        "bos_id": int(sp_cfg["bos_id"]),
        "eos_id": int(sp_cfg["eos_id"]),
        "pad_piece": str(sp_cfg["pad_piece"]),
        "unk_piece": str(sp_cfg["unk_piece"]),
        "bos_piece": str(sp_cfg["bos_piece"]),
        "eos_piece": str(sp_cfg["eos_piece"]),
        "unk_surface": str(sp_cfg["unk_surface"]),
        "required_chars": str(sp_cfg.get("required_chars") or ""),
        "train_extremely_large_corpus": False,
    }
    # Record seed policy even though TrainerSpec has no seed field in SP 0.2.0
    recorded = {
        **train_kwargs,
        "seed": sp_cfg.get("seed"),
        "seed_note": sp_cfg.get("seed_note"),
        "determinism_controls": {
            "shuffle_input_sentence": train_kwargs["shuffle_input_sentence"],
            "num_threads": train_kwargs["num_threads"],
            "input_sentence_size": train_kwargs["input_sentence_size"],
        },
    }

    # Write intended config before training
    write_json(out_dir / "training_config.json", recorded)

    spm.SentencePieceTrainer.train(**train_kwargs)

    model_file = out_dir / "model.model"
    vocab_file = out_dir / "model.vocab"
    if not model_file.is_file():
        raise RuntimeError(f"Training failed; missing {model_file}")

    # Copy/rename for clarity
    # SentencePiece already wrote model.model and model.vocab via prefix
    info = platform_info()
    info["git_commit"] = git_commit(root)
    info["sentencepiece_version"] = sentencepiece_version()

    # special token ids from loaded model
    sp = spm.SentencePieceProcessor()
    sp.load(str(model_file))
    special_ids = {
        "pad_id": sp.pad_id(),
        "unk_id": sp.unk_id(),
        "bos_id": sp.bos_id(),
        "eos_id": sp.eos_id(),
        "vocab_size_actual": sp.get_piece_size(),
    }

    sample = train_path.read_text(encoding="utf-8").splitlines()[:30]
    audit = normalization_audit(sample, config["normalization"]["policy"])

    manifest = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "created_at": utc_now_iso(),
        "experiment_id": config["experiment_id"],
        "tokenizer_id": f"{model_type}_{vocab_size}",
        "model_type": model_type,
        "requested_vocab_size": vocab_size,
        "training_input": str(train_path.relative_to(root)),
        "training_input_sha256": sha256_file(train_path),
        "config_path": str(
            config_path.relative_to(root) if config_path.is_relative_to(root) else config_path
        ),
        "config_sha256": sha256_file(config_path),
        "training_kwargs": recorded,
        "special_token_ids": special_ids,
        "normalization_audit": audit,
        "platform": info,
        "input_sentence_sampling": {
            "input_sentence_size": train_kwargs["input_sentence_size"],
            "shuffle_input_sentence": train_kwargs["shuffle_input_sentence"],
            "policy": "all_sentences" if train_kwargs["input_sentence_size"] == 0 else "sampled",
        },
        "byte_fallback": train_kwargs["byte_fallback"],
        "split_by_whitespace": train_kwargs["split_by_whitespace"],
        "treatment_of_digits": "split_by_number=" + str(train_kwargs["split_by_number"]),
        "treatment_of_punctuation": "handled_via_unicode_script_and_pieces",
        "artifacts": {
            "model.model": sha256_file(model_file),
            "model.vocab": sha256_file(vocab_file) if vocab_file.is_file() else None,
            "training_config.json": sha256_file(out_dir / "training_config.json"),
        },
        "frozen_split_check": {"verified": True, "split_root": config["split_root"]},
        "disclaimers": [
            "Trained on train split only.",
            "Segmentation is not claimed to be linguistically correct.",
            "Not MthandiziTokenizer / morphology-aware.",
        ],
    }
    write_json(out_dir / "manifest.json", manifest)
    write_text(
        out_dir / "README.md",
        f"# {model_type.upper()} vocab={vocab_size}\n\n"
        f"tokenizer_id: `{model_type}_{vocab_size}`\n"
        f"model: `model.model`\n"
        f"train: `{train_path.relative_to(root)}`\n",
    )
    return out_dir


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)

    if sentencepiece_version() is None:
        print(
            "error: sentencepiece is not installed.\n"
            "  python3 -m venv .venv\n"
            "  .venv/bin/pip install -r requirements-tokenizers.txt",
            file=sys.stderr,
        )
        return 2

    split_root = root / config["split_root"]
    try:
        verify_frozen_split(split_root, config)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    train_path = root / config["training_inputs"]["combined"]
    if "/train/" not in str(train_path).replace("\\", "/"):
        print("error: training path must be under train/", file=sys.stderr)
        return 1

    types = (
        list(config["sentencepiece"]["model_types"])
        if args.model_type == "all"
        else [args.model_type]
    )
    sizes = list(config["sentencepiece"]["vocab_sizes"])

    # top-level bpe/unigram dirs: allow creating under new experiment only
    exp_root = root / config["output_root"]
    exp_root.mkdir(parents=True, exist_ok=True)

    trained: list[str] = []
    try:
        for mt in types:
            for vs in sizes:
                out = train_one(
                    root=root,
                    config=config,
                    config_path=config_path,
                    model_type=mt,
                    vocab_size=vs,
                    train_path=train_path,
                    force=args.force,
                )
                trained.append(str(out.relative_to(root)))
                print(f"trained {mt} vocab={vs} → {out}")
    except (FileExistsError, RuntimeError, ImportError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"Done. Trained {len(trained)} models.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
