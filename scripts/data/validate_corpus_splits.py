#!/usr/bin/env python3
"""Validate frozen corpus splits for leakage, reconciliation, and freeze integrity.

Does not modify processed corpus or splits. Standard library only. Python 3.11+.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from audit_sources import load_json  # noqa: E402
from build_corpus_splits import (  # noqa: E402
    SPLITS,
    normalize_line,
    sha256_text,
    shingle_overlap_report,
)
from build_inventory import sha256_file  # noqa: E402

TOOL_NAME = "validate_corpus_splits"
TOOL_VERSION = "0.1.0"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSONL {path}:{i}: {e}") from e
    return rows


def read_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def validate(
    *,
    config: dict[str, Any],
    repo_root: Path,
    include_shingles: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    out_root = repo_root / config["output_root"]
    corpus_root = repo_root / config["processed_corpus_root"]
    source_ids = list(config.get("sources") or ["bible", "wikipedia"])

    if not out_root.is_dir():
        return {
            "ok": False,
            "errors": [f"split root missing: {out_root}"],
            "warnings": [],
        }

    freeze = out_root / "metadata" / "FROZEN_SPLIT.json"
    if not freeze.is_file():
        errors.append("missing FROZEN_SPLIT.json freeze marker")
    else:
        fr = load_json(freeze)
        if not fr.get("frozen"):
            errors.append("FROZEN_SPLIT.json has frozen=false")

    assignments = load_jsonl(out_root / "metadata" / "split_assignments.jsonl")
    if not assignments:
        errors.append("empty or missing split_assignments.jsonl")

    # 1. No group in more than one split
    group_splits: dict[str, set[str]] = defaultdict(set)
    for a in assignments:
        group_splits[a["group_id"]].add(a["split"])
    multi = {g: sorted(s) for g, s in group_splits.items() if len(s) > 1}
    if multi:
        errors.append(f"groups in multiple splits: {list(multi.items())[:5]}")

    # Load split texts
    split_source_lines: dict[str, dict[str, list[str]]] = {
        s: {} for s in SPLITS
    }
    for split in SPLITS:
        for sid in source_ids:
            p = out_root / split / f"{sid}.txt"
            if not p.is_file():
                errors.append(f"missing {split}/{sid}.txt")
                split_source_lines[split][sid] = []
            else:
                split_source_lines[split][sid] = read_lines(p)
        # combined
        cpath = out_root / split / "combined.txt"
        if not cpath.is_file():
            errors.append(f"missing {split}/combined.txt")
        else:
            # combined must equal concatenation in configured order
            order = list(config.get("combined_source_order") or source_ids)
            expected: list[str] = []
            for sid in order:
                expected.extend(split_source_lines[split].get(sid) or [])
            actual = read_lines(cpath)
            if actual != expected:
                errors.append(
                    f"{split}/combined.txt does not match deterministic source concatenation"
                )

    # 2–3 exact and normalized cross-split
    exact_map: dict[str, set[str]] = defaultdict(set)
    norm_map: dict[str, set[str]] = defaultdict(set)
    for split in SPLITS:
        for sid in source_ids:
            for line in split_source_lines[split][sid]:
                if not line.strip():
                    continue
                exact_map[line].add(split)
                nk = normalize_line(line)
                if nk:
                    norm_map[nk].add(split)

    exact_x = sorted(k for k, s in exact_map.items() if len(s) > 1)
    norm_x = sorted(k for k, s in norm_map.items() if len(s) > 1)
    if exact_x:
        errors.append(f"exact cross-split lines: {len(exact_x)} (sample sha {sha256_text(exact_x[0])})")
    if norm_x:
        errors.append(
            f"normalized cross-split lines: {len(norm_x)} (sample sha {sha256_text(norm_x[0])})"
        )

    # 4–6 reconciliation with processed corpus
    input_lines: dict[str, list[str]] = {}
    for sid in source_ids:
        ip = corpus_root / "corpus" / f"{sid}.txt"
        if not ip.is_file():
            errors.append(f"processed corpus missing {sid}.txt")
            input_lines[sid] = []
        else:
            input_lines[sid] = read_lines(ip)

    for sid in source_ids:
        out_count = sum(len(split_source_lines[s][sid]) for s in SPLITS)
        in_count = len(input_lines[sid])
        if out_count != in_count:
            errors.append(
                f"source {sid} line count mismatch: input={in_count} split_sum={out_count}"
            )
        # Multiset equality
        in_c = Counter(input_lines[sid])
        out_c: Counter[str] = Counter()
        for s in SPLITS:
            out_c.update(split_source_lines[s][sid])
        if in_c != out_c:
            errors.append(f"source {sid} multiset of lines does not reconcile with processed corpus")

    # Within-split unexpected duplicates (promotion already exact-deduped; warn only)
    for split in SPLITS:
        for sid in source_ids:
            c = Counter(split_source_lines[split][sid])
            dups = sum(1 for n in c.values() if n > 1)
            if dups:
                warnings.append(
                    f"{split}/{sid}: {dups} exact lines repeated within split file"
                )

    # 7 checksums recorded
    checksums_path = out_root / "metadata" / "checksums.json"
    if not checksums_path.is_file():
        errors.append("missing metadata/checksums.json")
    else:
        checksums = load_json(checksums_path)
        for rel, exp in checksums.items():
            p = out_root / rel
            if not p.is_file():
                # README may be stored with different key
                errors.append(f"checksum entry missing file: {rel}")
                continue
            actual = sha256_file(p)
            if actual != exp:
                errors.append(f"checksum mismatch: {rel}")

    # Processed corpus unchanged relative to inventory of checksums
    proc_checksums = corpus_root / "metadata" / "checksums.json"
    if proc_checksums.is_file():
        for rel, exp in load_json(proc_checksums).items():
            if not rel.startswith("corpus/"):
                continue
            p = corpus_root / rel
            if p.is_file() and sha256_file(p) != exp:
                errors.append(f"processed corpus mutated: {rel}")

    # 8 tokenizer configs must not reference val/test (scan known config dir)
    tok_refs: list[str] = []
    for cfg in (repo_root / "configs").rglob("*.json"):
        try:
            text = cfg.read_text(encoding="utf-8")
        except OSError:
            continue
        # Only flag explicit tokenizer-training style keys pointing at val/test
        if "tokenizer" in cfg.name.lower() or "sentencepiece" in text.lower():
            if "validation/" in text or "/test/" in text or "splits/" in text and "test" in text:
                # soft check
                if '"split": "test"' in text or "train_on_validation" in text:
                    tok_refs.append(str(cfg.relative_to(repo_root)))
    if tok_refs:
        warnings.append(f"tokenizer-related configs may reference holdout paths: {tok_refs}")

    # document metadata files
    for split in SPLITS:
        docs = load_jsonl(out_root / "metadata" / f"{split}_documents.jsonl")
        n_lines = sum(len(split_source_lines[split][sid]) for sid in source_ids)
        if docs and len(docs) != n_lines:
            errors.append(
                f"{split}_documents.jsonl count {len(docs)} != text lines {n_lines}"
            )

    shingles: dict[str, Any] = {"enabled": False}
    if include_shingles:
        # rebuild minimal groups for diagnostic from assignments + lines is heavy;
        # compute from concatenated split text
        class _G:
            def __init__(self, split: str, text: str) -> None:
                self.split = split
                self.lines = [type("L", (), {"text": text})()]

        fake = []
        for split in SPLITS:
            text = "\n".join(
                line
                for sid in source_ids
                for line in split_source_lines[split][sid]
            )
            fake.append(_G(split, text))
        shingles = shingle_overlap_report(fake, n=5, max_pairs=10)  # type: ignore[arg-type]

    ok = len(errors) == 0
    return {
        "ok": ok,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "errors": errors,
        "warnings": warnings,
        "exact_cross_split_count": len(exact_x),
        "normalized_cross_split_count": len(norm_x),
        "n_groups": len(group_splits),
        "line_counts": {
            s: {sid: len(split_source_lines[s][sid]) for sid in source_ids}
            for s in SPLITS
        },
        "shingle_diagnostics": shingles,
        "frozen_marker_present": freeze.is_file(),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate frozen corpus splits.")
    p.add_argument("--config", type=Path, default=Path("configs/data/split_v0_1.json"))
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--json-output", type=Path, default=None)
    p.add_argument("--no-shingles", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    try:
        config = load_json(config_path)
        result = validate(
            config=config,
            repo_root=root,
            include_shingles=not args.no_shingles,
        )
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.json_output:
        out = args.json_output if args.json_output.is_absolute() else root / args.json_output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    status = "PASS" if result["ok"] else "FAIL"
    print(f"Split validation: {status}")
    print(f"  groups={result['n_groups']} exact_x={result['exact_cross_split_count']} "
          f"norm_x={result['normalized_cross_split_count']}")
    for w in result["warnings"]:
        print(f"  warning: {w}")
    for e in result["errors"]:
        print(f"  error: {e}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
