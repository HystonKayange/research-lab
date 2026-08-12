#!/usr/bin/env python3
"""Plot learning curves from machine-readable LM run logs (no training)."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lm_common import effective_epochs, load_json  # noqa: E402

TOOL_NAME = "plot_lm_learning_curves"
TOOL_VERSION = "0.1.0"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _finite(xs: list[float | None]) -> list[float]:
    return [float(x) for x in xs if x is not None and isinstance(x, (int, float)) and math.isfinite(float(x))]


def plot_xy(
    xs: list[float],
    ys: list[float],
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    out_base: Path,
    marker: str = "o",
) -> list[Path]:
    import matplotlib.pyplot as plt

    if not xs or not ys or len(xs) != len(ys):
        return []
    out_base.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(xs, ys, marker=marker, linestyle="-", linewidth=1.5, markersize=5)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    paths = []
    for ext in ("png", "svg"):
        p = out_base.with_suffix(f".{ext}")
        fig.savefig(p, dpi=150 if ext == "png" else None)
        paths.append(p)
    plt.close(fig)
    return paths


def build_curves(run_dir: Path, frozen_chars: int | None) -> dict[str, Any]:
    curve = load_jsonl(run_dir / "learning_curve.jsonl")
    train_log = load_jsonl(run_dir / "train_log.jsonl")
    man = load_json(run_dir / "manifest.json") if (run_dir / "manifest.json").is_file() else {}
    denom = frozen_chars or (man.get("exposure") or {}).get(
        "frozen_training_corpus_character_count"
    )
    # enrich curve rows with epochs if missing
    for row in curve:
        if row.get("effective_epochs") is None and denom and row.get("characters_processed") is not None:
            row["effective_epochs"] = effective_epochs(
                float(row["characters_processed"]), int(denom)
            )
    return {
        "learning_curve": curve,
        "train_log": train_log,
        "manifest": man,
        "frozen_chars": denom,
    }


def generate_plots(run_dir: Path, out_dir: Path, *, frozen_chars: int | None = None) -> list[Path]:
    data = build_curves(run_dir, frozen_chars)
    curve = data["learning_curve"]
    train_log = data["train_log"]
    man = data["manifest"]
    tok = man.get("tokenizer_id") or run_dir.parts[-4] if len(run_dir.parts) >= 4 else "model"
    seed = man.get("seed")
    title_prefix = f"{tok} seed={seed}" if seed is not None else str(tok)

    written: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)

    def series(rows: list[dict], xk: str, yk: str) -> tuple[list[float], list[float]]:
        xs, ys = [], []
        for r in rows:
            x, y = r.get(xk), r.get(yk)
            if x is None or y is None:
                continue
            if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
                continue
            if not (math.isfinite(float(x)) and math.isfinite(float(y))):
                continue
            xs.append(float(x))
            ys.append(float(y))
        return xs, ys

    pairs = [
        ("characters_processed", "bits_per_character", "val_bpc_vs_characters",
         "Characters processed", "Validation BPC"),
        ("effective_epochs", "bits_per_character", "val_bpc_vs_effective_epochs",
         "Effective epochs", "Validation BPC"),
        ("effective_epochs", "bits_per_byte", "val_bpb_vs_effective_epochs",
         "Effective epochs", "Validation BPB"),
        ("characters_processed", "characters_per_second", "chars_per_second_vs_characters",
         "Characters processed", "Characters / second"),
        ("step", "tokens_per_second", "tokens_per_second_vs_steps",
         "Optimizer steps", "Tokens / second"),
    ]
    for xk, yk, name, xl, yl in pairs:
        xs, ys = series(curve, xk, yk)
        written.extend(
            plot_xy(
                xs,
                ys,
                title=f"{title_prefix}: {yl} vs {xl}",
                xlabel=xl,
                ylabel=yl,
                out_base=out_dir / name,
            )
        )

    # train log curves
    for xk, yk, name, xl, yl in [
        ("step", "train_loss", "train_loss_vs_steps", "Optimizer steps", "Train loss"),
        ("step", "lr", "lr_vs_steps", "Optimizer steps", "Learning rate"),
        ("step", "grad_norm", "grad_norm_vs_steps", "Optimizer steps", "Gradient norm"),
    ]:
        xs, ys = series(train_log, xk, yk)
        written.extend(
            plot_xy(
                xs,
                ys,
                title=f"{title_prefix}: {yl} vs {xl}",
                xlabel=xl,
                ylabel=yl,
                out_base=out_dir / name,
                marker=".",
            )
        )

    # also export machine-readable series used
    meta = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "run_dir": str(run_dir),
        "n_curve_points": len(curve),
        "n_train_log_points": len(train_log),
        "plots": [str(p) for p in written],
        "note": "Points are raw logged measurements; no fabricated interpolations.",
    }
    (out_dir / "plot_manifest.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot LM learning curves from logs.")
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Default: data/reports/figures/lm_baselines_v0.1/<run_slug>",
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--frozen-chars", type=int, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    run_dir = args.run_dir if args.run_dir.is_absolute() else root / args.run_dir
    if not run_dir.is_dir():
        print(f"error: run dir missing: {run_dir}", file=sys.stderr)
        return 1
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print(
            "error: matplotlib required. .venv/bin/pip install matplotlib",
            file=sys.stderr,
        )
        return 2
    if args.out_dir:
        out_dir = args.out_dir if args.out_dir.is_absolute() else root / args.out_dir
    else:
        slug = "__".join(run_dir.parts[-5:])
        out_dir = root / "data/reports/figures/lm_baselines_v0.1" / slug
    paths = generate_plots(run_dir, out_dir, frozen_chars=args.frozen_chars)
    print(f"Wrote {len(paths)} figure files under {out_dir}")
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
