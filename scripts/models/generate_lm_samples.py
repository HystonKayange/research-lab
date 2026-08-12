#!/usr/bin/env python3
"""Generate fixed-prompt samples for human review (greedy + sampling)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lm_common import (  # noqa: E402
    load_json,
    load_tokenizer,
    write_json,
    write_jsonl,
)
from evaluate_lm_baseline import load_model_from_ckpt  # noqa: E402

TOOL_NAME = "generate_lm_samples"
TOOL_VERSION = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate LM samples.")
    p.add_argument("--config", type=Path, default=Path("configs/models/lm_baselines_v0_1.json"))
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--checkpoint", default="best.pt")
    p.add_argument("--device", default=None)
    p.add_argument("--review-id-prefix", default=None)
    return p.parse_args(argv)


def generate(
    model,
    tokenizer,
    prompt: str,
    *,
    max_new: int,
    device,
    greedy: bool,
    temperature: float,
    top_k: int,
    top_p: float,
) -> str:
    import torch
    import torch.nn.functional as F

    ids = tokenizer.encode(prompt)
    if not ids:
        ids = [tokenizer.bos_id] if tokenizer.bos_id >= 0 else [0]
    x = torch.tensor([ids], dtype=torch.long, device=device)
    model.eval()
    with torch.no_grad():
        for _ in range(max_new):
            x_cond = x[:, -model.context_length :]
            logits, *_ = model(x_cond)
            logits = logits[:, -1, :]
            if greedy:
                next_id = int(torch.argmax(logits, dim=-1).item())
            else:
                logits = logits / max(temperature, 1e-5)
                if top_k > 0:
                    v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                    logits[logits < v[:, [-1]]] = -float("inf")
                if 0 < top_p < 1:
                    sorted_logits, sorted_idx = torch.sort(logits, descending=True)
                    probs = F.softmax(sorted_logits, dim=-1)
                    cum = torch.cumsum(probs, dim=-1)
                    mask = cum > top_p
                    mask[..., 1:] = mask[..., :-1].clone()
                    mask[..., 0] = False
                    sorted_logits[mask] = -float("inf")
                    logits = torch.zeros_like(logits).scatter(1, sorted_idx, sorted_logits)
                probs = F.softmax(logits, dim=-1)
                next_id = int(torch.multinomial(probs, num_samples=1).item())
            x = torch.cat([x, torch.tensor([[next_id]], device=device)], dim=1)
            if next_id == tokenizer.eos_id:
                break
    return tokenizer.decode(x[0].tolist())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config = load_json(
        args.config if args.config.is_absolute() else root / args.config
    )
    run_dir = args.run_dir if args.run_dir.is_absolute() else root / args.run_dir
    man = load_json(run_dir / "manifest.json")
    tok_id = man["tokenizer_id"]
    seed = man["seed"]

    try:
        import torch
    except ImportError:
        print("error: torch required", file=sys.stderr)
        return 2

    device = torch.device(
        args.device if args.device else ("cuda" if torch.cuda.is_available() else "cpu")
    )
    tokenizer = load_tokenizer(config["tokenizers"][tok_id], root)
    model, _ckpt = load_model_from_ckpt(run_dir / args.checkpoint, device)

    gen_cfg = config["generation"]
    rows: list[dict[str, Any]] = []
    model_id = f"{tok_id}_seed{seed}"
    prefix = args.review_id_prefix or f"{tok_id}_{seed}"
    rid = 0
    for prompt in gen_cfg["prompts"]:
        for mode, greedy in (("greedy", True), ("sample", False)):
            rid += 1
            text = generate(
                model,
                tokenizer,
                prompt,
                max_new=int(gen_cfg["max_new_tokens"]),
                device=device,
                greedy=greedy,
                temperature=float(gen_cfg["temperature"]),
                top_k=int(gen_cfg["top_k"]),
                top_p=float(gen_cfg["top_p"]),
            )
            rows.append(
                {
                    "review_id": f"{prefix}_{rid:04d}",
                    "model_id": model_id,
                    "decoding": mode,
                    "prompt": prompt,
                    "generation": text,
                    "fluency": None,
                    "coherence": None,
                    "grammar": None,
                    "semantic_relevance": None,
                    "memorization_concern": None,
                    "notes": None,
                }
            )
            print(f"[{mode}] {prompt!r} → {text[:80]!r}…")

    write_jsonl(run_dir / "generations.jsonl", rows)
    # append to global review file
    review_path = root / config["generation_review_path"]
    existing: list[dict[str, Any]] = []
    if review_path.is_file():
        for line in review_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.append(__import__("json").loads(line))
    # replace same model_id entries
    existing = [r for r in existing if r.get("model_id") != model_id]
    existing.extend(rows)
    write_jsonl(review_path, existing)
    write_json(run_dir / "generation_meta.json", {"n": len(rows), "model_id": model_id})
    print(f"wrote {run_dir / 'generations.jsonl'} and {review_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
