#!/usr/bin/env python3
"""Regenerate StatBound V1 boundary_stats from TRAIN only and verify SHA-256.

Expected hash is read from the frozen evaluation protocol and is NEVER modified.

Usage:
  .venv/bin/python scripts/tokenizers/verify_boundary_stats_repro.py
  .venv/bin/python scripts/tokenizers/verify_boundary_stats_repro.py --write-if-missing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.tokenizers.statbound.boundary_stats import (  # noqa: E402
    BoundaryDiscoveryConfig,
    learn_boundary_stats,
    save_boundary_stats,
)
from src.tokenizers.statbound.leakage import LeakageError, assert_train_only_path  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_expected_sha(protocol_path: Path) -> tuple[str, str, int | None]:
    proto = json.loads(protocol_path.read_text(encoding="utf-8"))
    art = proto["reproducibility_snapshot"]["artifacts"]["boundary_stats"]
    return art["sha256"], art["path"], art.get("bytes")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Verify boundary_stats.json reproducibility")
    p.add_argument("--repo-root", type=Path, default=_REPO)
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="statbound_unigram_v1.json (default under repo)",
    )
    p.add_argument(
        "--protocol",
        type=Path,
        default=None,
        help="eval protocol JSON holding expected SHA",
    )
    p.add_argument(
        "--write-if-missing",
        action="store_true",
        help="If on-disk artifact missing, write regenerated stats to configured path after hash match",
    )
    p.add_argument(
        "--update-on-disk-if-match",
        action="store_true",
        help="After successful hash match, copy regenerated file to configured path",
    )
    args = p.parse_args(argv)
    root = args.repo_root.resolve()
    config_path = args.config or (root / "configs/tokenizers/statbound_unigram_v1.json")
    protocol_path = args.protocol or (
        root / "configs/tokenizers/statbound_unigram_v1_eval_protocol.json"
    )

    expected_sha, rel_path, expected_bytes = load_expected_sha(protocol_path)
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    train_path = root / cfg["corpus"]["train_text"]
    forbidden = cfg.get("leakage_guard", {}).get("forbid_path_substrings")
    try:
        assert_train_only_path(train_path, forbidden_substrings=forbidden)
    except LeakageError as e:
        print(f"FAIL leakage: {e}", file=sys.stderr)
        return 2

    bcfg = BoundaryDiscoveryConfig.from_dict(cfg["boundary_discovery"])
    print("Regenerating boundary stats from TRAIN only …")
    obj = learn_boundary_stats(train_path, bcfg, forbidden_substrings=forbidden)

    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td) / "boundary_stats.json"
        save_boundary_stats(obj, tmp_path)
        actual_sha = sha256_file(tmp_path)
        actual_bytes = tmp_path.stat().st_size
        print(f"expected_sha: {expected_sha}")
        print(f"actual_sha:   {actual_sha}")
        print(f"expected_bytes: {expected_bytes}")
        print(f"actual_bytes:   {actual_bytes}")
        if actual_sha != expected_sha:
            print(
                "FAIL: boundary_stats SHA-256 mismatch — "
                "do not change the expected hash; investigate non-determinism or code drift.",
                file=sys.stderr,
            )
            return 1

        target = root / rel_path
        if args.update_on_disk_if_match or (args.write_if_missing and not target.is_file()):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tmp_path.read_bytes())
            print(f"wrote matched artifact → {target}")

    print("PASS: boundary_stats regeneration matches frozen protocol SHA-256")
    print(json.dumps({"pass": True, "sha256": actual_sha, "bytes": actual_bytes}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
