#!/usr/bin/env python3
"""Run the frozen Phase-F LM matrix for StatBound-Unigram V1, lambda*=0.25.

This driver reuses the frozen LM training loop and evaluation function from
``train_lm_baseline.py``.  The only adapter-specific code maps the frozen
StatBound piece sequence to the IDs of the frozen base Unigram model.  It does
not change the StatBound algorithm, score, n-best size, model definition,
optimizer, schedule, or budget.

The split integrity check deliberately hashes only train/validation files.
It reads no LM-test file; the pre-existing r2 baseline audit is used as the
record that the completed standard matrix did not access test data.
"""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import pickle
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts/models") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts/models"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import lm_common  # noqa: E402
import train_lm_baseline as train  # noqa: E402
from evaluate_lm_baseline import load_model_from_ckpt  # noqa: E402
from lm_common import TokenizerAdapter  # noqa: E402
from src.tokenizers.statbound.tokenizer import StatBoundUnigramTokenizer  # noqa: E402


TOKENIZER_ID = "statbound_lambda_0_25"
LAMBDA = 0.25
MATRIX_CONFIG = ROOT / "configs/models/lm_baselines_v0_1_final_matrix_r2.json"
PARENT_CONFIG = ROOT / "configs/models/lm_baselines_v0_1.json"
STATBOUND_CONFIG = ROOT / "configs/tokenizers/statbound_unigram_v1.json"
BOUNDARY_STATS = ROOT / "data/tokenizers/chichewa_corpus_v0.1/statbound_unigram_v1/boundary_stats.json"
BASE_MODEL = ROOT / "data/tokenizers/chichewa_corpus_v0.1/baselines_v0.1/unigram/vocab_8000/model.model"
DEFAULT_CACHE = Path("/tmp/phase_f_statbound_lambda_0_25_line_cache_v0_1.pkl")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


class LineEncodingCache:
    """Cache exact StatBound line encodings without changing tokenization."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.metadata = {
            "schema": "phase_f_statbound_line_cache_v0_1",
            "tokenizer_id": TOKENIZER_ID,
            "lambda": LAMBDA,
            "statbound_config_sha256": sha256_file(STATBOUND_CONFIG),
            "boundary_stats_sha256": sha256_file(BOUNDARY_STATS),
            "base_unigram_model_sha256": sha256_file(BASE_MODEL),
        }
        self.encodings: dict[str, list[int]] = {}
        if path.is_file():
            try:
                with path.open("rb") as f:
                    obj = pickle.load(f)
                if obj.get("metadata") == self.metadata:
                    self.encodings = {
                        str(k): [int(x) for x in v]
                        for k, v in (obj.get("encodings") or {}).items()
                    }
            except (OSError, EOFError, ValueError, pickle.PickleError):
                self.encodings = {}

    def get(self, line: str, encode_uncached) -> list[int]:
        key = sha256_text(line)
        if key not in self.encodings:
            self.encodings[key] = list(encode_uncached(line))
        return list(self.encodings[key])

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("wb") as f:
            pickle.dump(
                {"metadata": self.metadata, "encodings": self.encodings},
                f,
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        tmp.replace(self.path)


class StatBoundLMAdapter(TokenizerAdapter):
    """LM adapter backed by the frozen StatBound word encoder."""

    def __init__(self, tokenizer: StatBoundUnigramTokenizer, cache: LineEncodingCache) -> None:
        self.statbound = tokenizer
        self.sp = tokenizer.adapter.sp
        self.cache = cache
        self.pad_id = int(self.sp.pad_id())
        self.unk_id = int(self.sp.unk_id())
        self.bos_id = int(self.sp.bos_id())
        self.eos_id = int(self.sp.eos_id())
        self.vocab_size = int(self.sp.get_piece_size())
        self.tokenizer_id = TOKENIZER_ID

    def _encode_uncached(self, text: str) -> list[int]:
        pieces = self.statbound.encode_text(text)
        ids = [int(self.sp.piece_to_id(piece)) for piece in pieces]
        if any(i < 0 for i in ids):
            raise ValueError("StatBound returned a piece absent from the frozen base vocabulary")
        return ids

    def encode(self, text: str) -> list[int]:
        return self.cache.get(text, self._encode_uncached)

    def decode(self, ids: Sequence[int]) -> str:
        return self.sp.decode(list(ids))

    def id_to_token(self, i: int) -> str:
        return self.sp.id_to_piece(int(i))


def verify_train_validation_only(split_root: Path) -> dict[str, Any]:
    """Verify frozen train/validation inputs without opening LM-test files."""
    freeze = load_json(split_root / "metadata/FROZEN_SPLIT.json")
    if not freeze.get("frozen"):
        raise ValueError("split is not marked frozen")
    checksums = load_json(split_root / "metadata/checksums.json")
    checked = 0
    for rel, expected in checksums.items():
        rel_s = str(rel).replace("\\", "/")
        if not (rel_s.startswith("train/") or rel_s.startswith("validation/")):
            continue
        path = split_root / rel
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"train/validation checksum mismatch: {rel}")
        checked += 1
    if checked == 0:
        raise ValueError("no train/validation checksums were verified")
    return {
        "frozen": True,
        # train_lm_baseline.py records this field in its manifest.
        "n_ok": checked,
        "train_validation_checksums_verified": checked,
        "lm_test_file_opened": False,
    }


def install_patches(root: Path, adapter: StatBoundLMAdapter) -> None:
    """Inject only the frozen tokenizer adapter into the existing LM runner."""
    original_parse = train.parse_args
    original_load_json = train.load_json
    original_load_tokenizer = train.load_tokenizer
    original_verify_tokenizer = train.verify_tokenizer_artifacts

    def patched_parse_args(argv=None):
        raw = list(sys.argv[1:] if argv is None else argv)
        found = False
        rewritten: list[str] = []
        for value in raw:
            if value == TOKENIZER_ID:
                rewritten.append("unigram_8000")
                found = True
            else:
                rewritten.append(value)
        parsed = original_parse(rewritten)
        if found:
            parsed.tokenizer = TOKENIZER_ID
        return parsed

    def patched_load_json(path: Path):
        obj = original_load_json(path)
        name = Path(path).name
        if name == PARENT_CONFIG.name:
            out = copy.deepcopy(obj)
            custom = copy.deepcopy(out["tokenizers"]["unigram_8000"])
            custom["tokenizer_id"] = TOKENIZER_ID
            custom["kind"] = "statbound"
            custom["path"] = str(STATBOUND_CONFIG.relative_to(root).parent)
            out["tokenizers"][TOKENIZER_ID] = custom
            out["parameter_matched"]["overrides"][TOKENIZER_ID] = copy.deepcopy(
                out["parameter_matched"]["overrides"]["unigram_8000"]
            )
            return out
        if name == MATRIX_CONFIG.name:
            # merge_matrix_budget() replaces parameter_matched.overrides with
            # the matrix copy, so carry the custom tokenizer key there too.
            out = copy.deepcopy(obj)
            out["parameter_matched"]["overrides"][TOKENIZER_ID] = copy.deepcopy(
                out["parameter_matched"]["overrides"]["unigram_8000"]
            )
            return out
        return obj

    def patched_load_tokenizer(tok_cfg: dict[str, Any], repo_root: Path):
        if tok_cfg.get("kind") == "statbound":
            return adapter
        return original_load_tokenizer(tok_cfg, repo_root)

    def patched_verify_tokenizer(tok_cfg: dict[str, Any], repo_root: Path):
        if tok_cfg.get("kind") == "statbound":
            return {
                "path": str(STATBOUND_CONFIG.relative_to(root).parent),
                "tokenizer_id": TOKENIZER_ID,
                "lambda": LAMBDA,
                "base_model_sha256": sha256_file(BASE_MODEL),
                "boundary_stats_sha256": sha256_file(BOUNDARY_STATS),
                "statbound_config_sha256": sha256_file(STATBOUND_CONFIG),
                "artifact_checks": [
                    "base_unigram_model",
                    "boundary_stats",
                    "statbound_config",
                ],
            }
        return original_verify_tokenizer(tok_cfg, repo_root)

    train.parse_args = patched_parse_args
    train.load_json = patched_load_json
    train.load_tokenizer = patched_load_tokenizer
    train.verify_tokenizer_artifacts = patched_verify_tokenizer
    train.verify_frozen_split = verify_train_validation_only


def evaluate_validation_sources(
    root: Path,
    matrix: dict[str, Any],
    run_dir: Path,
    adapter: StatBoundLMAdapter,
    device_name: str | None,
) -> dict[str, Any]:
    """Evaluate the selected checkpoint on combined/Bible/Wikipedia validation only."""
    import torch

    device = torch.device(
        device_name if device_name else ("cuda" if torch.cuda.is_available() else "cpu")
    )
    ckpt_path = run_dir / "best.pt"
    model, ckpt = load_model_from_ckpt(ckpt_path, device)
    context_length = int(ckpt["arch"]["context_length"])
    source_paths = {
        "combined_validation": root / "data/splits/chichewa_corpus_v0.1/validation/combined.txt",
        "bible_validation": root / "data/splits/chichewa_corpus_v0.1/validation/bible.txt",
        "wikipedia_validation": root / "data/splits/chichewa_corpus_v0.1/validation/wikipedia.txt",
    }
    output: dict[str, Any] = {
        "tokenizer_id": TOKENIZER_ID,
        "lambda": LAMBDA,
        "checkpoint": "best.pt",
        "checkpoint_sha256": sha256_file(ckpt_path),
        "splits": {},
        "lm_test_file_opened": False,
    }
    for name, path in source_paths.items():
        text = path.read_text(encoding="utf-8")
        seqs, meta, _, _credits = lm_common.pack_lines_to_sequences(
            text.splitlines(),
            adapter,
            context_length=context_length,
            eos_between_lines=True,
        )
        metrics = train.evaluate_split(
            model,
            seqs,
            pad_id=adapter.pad_id,
            device=device,
            batch_size=int(matrix["evaluation"]["eval_batch_size"]),
            source_text=text,
            amp=False,
            dtype=torch.float32,
        )
        output["splits"][name] = {
            "bits_per_character": metrics["bits_per_character"],
            "bits_per_byte": metrics["bits_per_byte"],
            "n_chars": metrics["n_chars"],
            "n_bytes": metrics["n_bytes"],
            "n_pred_tokens": metrics["n_pred_tokens"],
            "nan_detected": metrics["nan_detected"],
            "packing": meta.__dict__,
            "source_path": str(path.relative_to(root)),
        }
    lm_common.write_json(run_dir / "source_validation_metrics.json", output)
    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return output


def run_one(
    root: Path,
    track: str,
    budget_policy: str,
    seed: int,
    device_name: str | None,
) -> int:
    args = [
        "--config",
        str(PARENT_CONFIG.relative_to(root)),
        "--matrix-config",
        str(MATRIX_CONFIG.relative_to(root)),
        "--phase",
        "final",
        "--tokenizer",
        TOKENIZER_ID,
        "--seed",
        str(seed),
        "--track",
        track,
        "--budget-policy",
        budget_policy,
        "--yes",
    ]
    if device_name:
        args.extend(["--device", device_name])
    status = train.main(args)
    if status != 0:
        return int(status)

    matrix = load_json(MATRIX_CONFIG)
    slug = matrix["budget_path_slugs"][budget_policy]
    run_dir = (
        root
        / matrix["output_root"]
        / track
        / TOKENIZER_ID
        / f"seed_{seed}"
        / "final"
        / slug
    )
    # Reuse the same selected checkpoint if a resumable invocation reached it.
    if not (run_dir / "best.pt").is_file():
        raise RuntimeError(f"completed training run has no best checkpoint: {run_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=ROOT)
    p.add_argument("--device", default=None, help="cuda|cpu; default follows baseline auto-selection")
    p.add_argument("--cache-path", type=Path, default=DEFAULT_CACHE)
    p.add_argument("--skip-existing", action="store_true", default=True)
    args = p.parse_args(argv)
    root = args.repo_root.resolve()
    matrix = load_json(root / MATRIX_CONFIG.relative_to(ROOT))

    # One shared frozen tokenizer and line cache are used for all 12 runs.
    cache = LineEncodingCache(args.cache_path)
    statbound = StatBoundUnigramTokenizer.from_config(
        root / STATBOUND_CONFIG.relative_to(ROOT),
        stats_path=root / BOUNDARY_STATS.relative_to(ROOT),
        lambda_bias=LAMBDA,
        repo_root=root,
    )
    adapter = StatBoundLMAdapter(statbound, cache)
    install_patches(root, adapter)

    conditions = [
        ("parameter_matched", "fixed_characters"),
        ("architecture_matched", "fixed_characters"),
        ("parameter_matched", "fixed_updates"),
        ("architecture_matched", "fixed_updates"),
    ]
    seeds = [42, 1337, 2026]
    failures: list[dict[str, Any]] = []
    completed = 0
    for track, budget in conditions:
        slug = matrix["budget_path_slugs"][budget]
        for seed in seeds:
            run_dir = root / matrix["output_root"] / track / TOKENIZER_ID / f"seed_{seed}" / "final" / slug
            manifest_path = run_dir / "manifest.json"
            if manifest_path.is_file() and (run_dir / "selection_lock.json").is_file():
                manifest = load_json(manifest_path)
                if manifest.get("status") == "completed":
                    print(f"SKIP completed {track} seed={seed} budget={budget}")
                    if not (run_dir / "source_validation_metrics.json").is_file():
                        evaluate_validation_sources(root, matrix, run_dir, adapter, args.device)
                    completed += 1
                    continue
            print(f"RUN {track} seed={seed} budget={budget}")
            try:
                rc = run_one(root, track, budget, seed, args.device)
                if rc != 0:
                    failures.append({"track": track, "budget_policy": budget, "seed": seed, "return_code": rc})
                    continue
                evaluate_validation_sources(root, matrix, run_dir, adapter, args.device)
                completed += 1
            except Exception as exc:  # noqa: BLE001
                failures.append({"track": track, "budget_policy": budget, "seed": seed, "error": repr(exc)})
                print(f"FAIL {track} seed={seed} budget={budget}: {exc}", file=sys.stderr)
                break
            finally:
                gc.collect()
                try:
                    import torch

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass
    cache.save()
    print(json.dumps({"completed": completed, "expected": 12, "failures": failures, "cache_entries": len(cache.encodings)}, indent=2))
    return 1 if failures or completed != 12 else 0


if __name__ == "__main__":
    raise SystemExit(main())
