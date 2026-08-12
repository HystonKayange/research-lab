#!/usr/bin/env python3
"""Build frozen, leakage-safe train/validation/test splits from a processed corpus.

Deterministic contiguous-block grouping when structural document IDs are unavailable.
Uses SHA-256 group hashing (not Python's built-in hash). Does not modify the
processed corpus. Does not train tokenizers or models.

Requires Python 3.11+. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from audit_sources import load_json, utc_now_iso  # noqa: E402
from build_inventory import sha256_file  # noqa: E402

TOOL_NAME = "build_corpus_splits"
TOOL_VERSION = "0.1.0"
SPLITS = ("train", "validation", "test")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_commit(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def normalize_line(text: str) -> str:
    """NFC + collapse internal whitespace + strip (for leakage checks)."""
    t = unicodedata.normalize("NFC", text)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


@dataclass
class LineRecord:
    source_id: str
    line_index: int
    text: str
    doc_id: str
    text_sha256: str
    n_chars: int


@dataclass
class Group:
    group_id: str
    source_id: str
    source_document_id: str
    start_line: int
    end_line: int  # exclusive
    lines: list[LineRecord] = field(default_factory=list)
    assignment_method: str = "sha256_group_hash"
    split: str | None = None
    reassigned_for_leakage: bool = False

    @property
    def line_count(self) -> int:
        return len(self.lines)

    @property
    def character_count(self) -> int:
        return sum(lr.n_chars for lr in self.lines)

    @property
    def byte_count(self) -> int:
        return sum(len(lr.text.encode("utf-8")) for lr in self.lines)

    @property
    def word_count(self) -> int:
        return sum(count_words(lr.text) for lr in self.lines)


def load_source_lines(
    corpus_root: Path, source_id: str, documents_by_key: dict[tuple[str, int], dict]
) -> list[LineRecord]:
    path = corpus_root / "corpus" / f"{source_id}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Missing corpus file: {path}")
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    out: list[LineRecord] = []
    for i, text in enumerate(lines):
        meta = documents_by_key.get((source_id, i))
        if meta:
            doc_id = str(meta.get("doc_id") or f"{source_id}:{i}")
            text_sha = str(meta.get("text_sha256") or sha256_text(text))
            n_chars = int(meta.get("n_chars") if meta.get("n_chars") is not None else len(text))
        else:
            doc_id = f"{source_id}:{i}"
            text_sha = sha256_text(text)
            n_chars = len(text)
        # Integrity: text sha must match content
        actual = sha256_text(text)
        if text_sha != actual:
            # Prefer content truth; flag via recomputed hash
            text_sha = actual
        out.append(
            LineRecord(
                source_id=source_id,
                line_index=i,
                text=text,
                doc_id=doc_id,
                text_sha256=text_sha,
                n_chars=n_chars,
            )
        )
    return out


def load_documents_index(path: Path) -> dict[tuple[str, int], dict]:
    idx: dict[tuple[str, int], dict] = {}
    if not path.is_file():
        return idx
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = obj.get("source_id")
        li = obj.get("line_index")
        if sid is None or li is None:
            continue
        try:
            idx[(str(sid), int(li))] = obj
        except (TypeError, ValueError):
            continue
    return idx


def form_contiguous_char_blocks(
    records: Sequence[LineRecord],
    *,
    target_chars: int,
    source_id: str,
) -> list[Group]:
    """Partition ordered lines into contiguous groups of ~target_chars."""
    if target_chars < 1:
        raise ValueError("target_group_characters must be >= 1")
    groups: list[Group] = []
    if not records:
        return groups

    start = 0
    cur_chars = 0
    for i, rec in enumerate(records):
        cur_chars += rec.n_chars
        # +1 for newline accounting optional; use unicode chars of text only
        at_end = i == len(records) - 1
        if cur_chars >= target_chars or at_end:
            end = i + 1
            block = list(records[start:end])
            gid = f"{source_id}:block:{start:06d}-{end:06d}"
            groups.append(
                Group(
                    group_id=gid,
                    source_id=source_id,
                    source_document_id=gid,
                    start_line=start,
                    end_line=end,
                    lines=block,
                )
            )
            start = end
            cur_chars = 0
    return groups


def bucket_thresholds(proportions: dict[str, float], modulus: int) -> dict[str, tuple[int, int]]:
    train_p = float(proportions["train"])
    val_p = float(proportions["validation"])
    test_p = float(proportions["test"])
    s = train_p + val_p + test_p
    if abs(s - 1.0) > 1e-6:
        raise ValueError(f"proportions must sum to 1.0, got {s}")
    train_end = int(round(train_p * modulus))
    val_end = train_end + int(round(val_p * modulus))
    # ensure last bucket covers modulus
    if val_end > modulus:
        val_end = modulus
    return {
        "train": (0, train_end),
        "validation": (train_end, val_end),
        "test": (val_end, modulus),
    }


def assign_split_sha256(
    group_id: str,
    *,
    salt: str,
    modulus: int,
    thresholds: dict[str, tuple[int, int]],
) -> tuple[str, int, str]:
    """Return (split, bucket, digest_hex). Stable cryptographic assignment."""
    material = f"{salt}|{group_id}".encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    # first 8 bytes → uint64
    value = int.from_bytes(bytes.fromhex(digest[:16]), "big")
    bucket = value % modulus
    for name, (lo, hi) in thresholds.items():
        if lo <= bucket < hi:
            return name, bucket, digest
    return "test", bucket, digest


def assign_groups(
    groups: list[Group],
    *,
    salt: str,
    modulus: int,
    proportions: dict[str, float],
) -> None:
    thresholds = bucket_thresholds(proportions, modulus)
    for g in groups:
        split, _bucket, _digest = assign_split_sha256(
            g.group_id, salt=salt, modulus=modulus, thresholds=thresholds
        )
        g.split = split
        g.assignment_method = "sha256_group_hash"


def resolve_cross_split_line_conflicts(
    groups: list[Group],
    *,
    use_normalized: bool,
) -> list[dict[str, Any]]:
    """If the same (normalized) line appears in multiple splits, reassign non-train groups to train.

    Preserves group integrity (whole group moves). Returns conflict log entries.
    """
    # Map key → set of group indices
    key_to_groups: dict[str, set[int]] = defaultdict(set)
    for gi, g in enumerate(groups):
        for lr in g.lines:
            if not lr.text.strip():
                continue
            key = normalize_line(lr.text) if use_normalized else lr.text
            if not key:
                continue
            key_to_groups[key].add(gi)

    log: list[dict[str, Any]] = []
    for key, gis in key_to_groups.items():
        splits = {groups[i].split for i in gis}
        if len(splits) <= 1:
            continue
        # Conflict: move all non-train groups involved to train
        for i in sorted(gis):
            g = groups[i]
            if g.split != "train":
                old = g.split
                g.split = "train"
                g.reassigned_for_leakage = True
                log.append(
                    {
                        "action": "reassign_group_to_train",
                        "group_id": g.group_id,
                        "from_split": old,
                        "reason": "normalized_cross_split" if use_normalized else "exact_cross_split",
                        "sample_key_sha256": sha256_text(key[:200]),
                    }
                )
    return log


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_json_atomic(path: Path, obj: Any) -> None:
    write_text_atomic(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def write_jsonl_atomic(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def group_stats(groups: Sequence[Group], split: str | None = None) -> dict[str, Any]:
    sel = [g for g in groups if split is None or g.split == split]
    by_source: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "groups": 0,
            "lines": 0,
            "words": 0,
            "characters": 0,
            "bytes": 0,
        }
    )
    totals = {"groups": 0, "lines": 0, "words": 0, "characters": 0, "bytes": 0}
    for g in sel:
        s = by_source[g.source_id]
        s["groups"] += 1
        s["lines"] += g.line_count
        s["words"] += g.word_count
        s["characters"] += g.character_count
        s["bytes"] += g.byte_count
        totals["groups"] += 1
        totals["lines"] += g.line_count
        totals["words"] += g.word_count
        totals["characters"] += g.character_count
        totals["bytes"] += g.byte_count
    return {"totals": totals, "by_source": dict(by_source)}


def shingle_set(text: str, n: int) -> set[str]:
    toks = re.findall(r"\S+", text.lower())
    if len(toks) < n:
        return set()
    return {" ".join(toks[i : i + n]) for i in range(len(toks) - n + 1)}


def shingle_overlap_report(
    groups: Sequence[Group],
    *,
    n: int,
    max_pairs: int,
) -> dict[str, Any]:
    """Optional diagnostic: Jaccard-style shingle overlap between split aggregates."""
    split_text: dict[str, str] = {s: "" for s in SPLITS}
    for g in groups:
        if g.split in split_text:
            split_text[g.split] += "\n".join(lr.text for lr in g.lines) + "\n"
    sets = {s: shingle_set(t, n) for s, t in split_text.items()}
    pairs: list[dict[str, Any]] = []
    names = list(SPLITS)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            sa, sb = sets[a], sets[b]
            if not sa or not sb:
                inter = 0
                union = len(sa | sb)
                j = 0.0
            else:
                inter = len(sa & sb)
                union = len(sa | sb)
                j = inter / union if union else 0.0
            pairs.append(
                {
                    "split_a": a,
                    "split_b": b,
                    "shingle_size": n,
                    "intersection": inter,
                    "union": union,
                    "jaccard": round(j, 6),
                    "size_a": len(sa),
                    "size_b": len(sb),
                }
            )
    pairs.sort(key=lambda p: -p["jaccard"])
    return {
        "enabled": True,
        "shingle_size": n,
        "pairs": pairs[:max_pairs],
        "note": (
            "Diagnostic only. High overlap may reflect formulaic religious language "
            "rather than exact-line leakage. No fuzzy matches are removed."
        ),
    }


def formulaic_repetition_report(groups: Sequence[Group], top_k: int = 15) -> dict[str, Any]:
    """Report frequent short normalized lines (likely formulaic, not cross-split dups)."""
    # Within each split, count normalized forms that appear many times
    # (shouldn't after exact dedup of full lines — report near-empty)
    by_split: dict[str, list[tuple[int, str]]] = {}
    for split in SPLITS:
        c: Counter[str] = Counter()
        for g in groups:
            if g.split != split:
                continue
            for lr in g.lines:
                if not lr.text.strip():
                    continue
                # full-line uniqueness is expected; track first 40-char prefix patterns
                pref = normalize_line(lr.text)[:40]
                if len(pref) >= 12:
                    c[pref] += 1
        by_split[split] = [(n, p) for p, n in c.most_common(top_k) if n > 1]
    return {
        "description": (
            "Prefix-frequency diagnostic for formulaic phrasing. Exact full-line "
            "duplicates were removed at corpus promotion within sources."
        ),
        "by_split_prefix_counts_gt1": by_split,
    }


def build_outputs(
    groups: list[Group],
    *,
    out_root: Path,
    source_ids: Sequence[str],
    combined_order: Sequence[str],
) -> dict[str, Any]:
    # Collect lines per split per source preserving original order within source
    split_source_lines: dict[str, dict[str, list[str]]] = {
        s: {sid: [] for sid in source_ids} for s in SPLITS
    }
    split_docs: dict[str, list[dict[str, Any]]] = {s: [] for s in SPLITS}
    assignments: list[dict[str, Any]] = []

    # Process groups in stable order: by source order then start_line
    source_rank = {sid: i for i, sid in enumerate(source_ids)}
    ordered = sorted(
        groups,
        key=lambda g: (source_rank.get(g.source_id, 999), g.start_line, g.group_id),
    )

    for g in ordered:
        assert g.split is not None
        assignments.append(
            {
                "group_id": g.group_id,
                "source_id": g.source_id,
                "split": g.split,
                "line_count": g.line_count,
                "character_count": g.character_count,
                "word_count": g.word_count,
                "byte_count": g.byte_count,
                "start_line": g.start_line,
                "end_line": g.end_line,
                "assignment_method": g.assignment_method,
                "source_document_id": g.source_document_id,
                "reassigned_for_leakage": g.reassigned_for_leakage,
            }
        )
        for lr in g.lines:
            split_source_lines[g.split][g.source_id].append(lr.text)
            split_docs[g.split].append(
                {
                    "doc_id": lr.doc_id,
                    "source_id": lr.source_id,
                    "line_index": lr.line_index,
                    "group_id": g.group_id,
                    "split": g.split,
                    "text_sha256": lr.text_sha256,
                    "n_chars": lr.n_chars,
                }
            )

    file_checksums: dict[str, str] = {}
    for split in SPLITS:
        split_dir = out_root / split
        split_dir.mkdir(parents=True, exist_ok=True)
        for sid in source_ids:
            lines = split_source_lines[split][sid]
            body = "\n".join(lines)
            if lines:
                body += "\n"
            rel = f"{split}/{sid}.txt"
            p = out_root / rel
            write_text_atomic(p, body)
            file_checksums[rel] = sha256_file(p)

        # combined deterministic: fixed source order
        combined_parts: list[str] = []
        for sid in combined_order:
            if sid not in split_source_lines[split]:
                continue
            combined_parts.extend(split_source_lines[split][sid])
        cbody = "\n".join(combined_parts)
        if combined_parts:
            cbody += "\n"
        crel = f"{split}/combined.txt"
        write_text_atomic(out_root / crel, cbody)
        file_checksums[crel] = sha256_file(out_root / crel)

        drel = f"metadata/{split}_documents.jsonl"
        write_jsonl_atomic(out_root / drel, split_docs[split])
        file_checksums[drel] = sha256_file(out_root / drel)

    arel = "metadata/split_assignments.jsonl"
    write_jsonl_atomic(out_root / arel, assignments)
    file_checksums[arel] = sha256_file(out_root / arel)

    return {
        "file_checksums": file_checksums,
        "assignments": assignments,
        "split_docs_counts": {s: len(split_docs[s]) for s in SPLITS},
    }


def render_report(
    *,
    config: dict[str, Any],
    stats: dict[str, Any],
    leakage: dict[str, Any],
    shingles: dict[str, Any],
    formulaic: dict[str, Any],
    manifest: dict[str, Any],
    grouping_limitations: list[str],
) -> str:
    lines = [
        f"# Split report — {config.get('corpus_name')} {config.get('corpus_version')} / split {config.get('split_version')}",
        "",
        f"_Generated at {manifest.get('created_at')} by {TOOL_NAME} {TOOL_VERSION}_",
        "",
        "## 1. Methodology",
        "",
        "- Volume metric: Unicode character counts (not tokenizer-dependent).",
        f"- Target proportions: train={config['proportions']['train']}, "
        f"validation={config['proportions']['validation']}, "
        f"test={config['proportions']['test']}.",
        f"- Assignment: `{config['assignment']['method']}` with salt "
        f"`{config['assignment']['salt']}` and modulus "
        f"{config['assignment']['bucket_modulus']}.",
        "- Assignment does **not** use Python's built-in `hash()`.",
        "- Source files written separately; `combined.txt` concatenates sources in "
        f"fixed order: {config.get('combined_source_order')}.",
        "",
        "## 2. Grouping strategy by source",
        "",
        f"- Global strategy: `{config['grouping']['strategy']}`",
        f"- Target group size: ~{config['grouping']['target_group_characters']} Unicode characters",
        "",
    ]
    for sid, meta in (config.get("grouping", {}).get("sources") or {}).items():
        lines.append(f"### {sid}")
        lines.append("")
        lines.append(f"- Preferred: `{meta.get('preferred')}`")
        lines.append(f"- Used: `{meta.get('available')}`")
        lines.append(f"- Limitation: {meta.get('limitation')}")
        lines.append("")
    lines.extend(
        [
            "## 3. Limitations",
            "",
        ]
    )
    for lim in grouping_limitations:
        lines.append(f"- {lim}")
    lines.extend(
        [
            "- Contiguous blocks reduce adjacent-verse / adjacent-line leakage risk "
            "but are **not** recovered Bible chapters or Wikipedia articles.",
            "- Formulaic religious phrasing may share n-gram shingles across splits "
            "without exact-line leakage.",
            "",
            "## 4. Split sizes by source",
            "",
        ]
    )
    for split in SPLITS:
        st = stats[split]
        lines.append(f"### {split}")
        lines.append("")
        lines.append(
            f"- Totals: groups={st['totals']['groups']}, lines={st['totals']['lines']}, "
            f"words={st['totals']['words']}, characters={st['totals']['characters']}, "
            f"bytes={st['totals']['bytes']}"
        )
        for sid, ss in sorted(st["by_source"].items()):
            lines.append(
                f"- `{sid}`: groups={ss['groups']}, lines={ss['lines']}, "
                f"words={ss['words']}, characters={ss['characters']}, bytes={ss['bytes']}"
            )
        lines.append("")
    # proportions
    total_chars = sum(stats[s]["totals"]["characters"] for s in SPLITS) or 1
    lines.extend(["## 5. Character and word distributions", ""])
    for split in SPLITS:
        c = stats[split]["totals"]["characters"]
        w = stats[split]["totals"]["words"]
        lines.append(
            f"- **{split}:** characters={c} ({c / total_chars:.4f}), words={w}"
        )
    lines.extend(
        [
            "",
            "## 6. Group/document counts",
            "",
            f"- Total groups: {sum(stats[s]['totals']['groups'] for s in SPLITS)}",
            f"- Grouping unit: contiguous character blocks (source_document_id == group_id)",
            "",
            "## 7. Exact overlap checks",
            "",
            f"- Exact cross-split non-empty lines: **{leakage['exact_cross_split_count']}**",
            f"- Reassignments for exact conflicts: {leakage['exact_reassign_events']}",
            "",
            "## 8. Normalized overlap checks",
            "",
            f"- Normalization: `{leakage['normalization']}`",
            f"- Normalized cross-split non-empty lines after resolution: "
            f"**{leakage['normalized_cross_split_count']}**",
            f"- Reassignments for normalized conflicts: {leakage['normalized_reassign_events']}",
            "",
            "## 9. Optional shingle diagnostics",
            "",
            f"- Enabled: {shingles.get('enabled')}",
            f"- Shingle size: {shingles.get('shingle_size')}",
            f"- Note: {shingles.get('note')}",
            "",
        ]
    )
    for p in shingles.get("pairs") or []:
        lines.append(
            f"- {p['split_a']} vs {p['split_b']}: jaccard={p['jaccard']}, "
            f"intersection={p['intersection']}, |A|={p['size_a']}, |B|={p['size_b']}"
        )
    lines.extend(
        [
            "",
            "### Formulaic repetition (separate from leakage)",
            "",
            formulaic.get("description", ""),
            "",
            "## 10. Corpus reconciliation",
            "",
            f"- Input lines: {manifest.get('input_line_total')}",
            f"- Output lines (all splits): {manifest.get('output_line_total')}",
            f"- Match: {manifest.get('input_line_total') == manifest.get('output_line_total')}",
            f"- Input characters: {manifest.get('input_character_total')}",
            f"- Output characters: {manifest.get('output_character_total')}",
            "",
            "## 11. Checksums",
            "",
            f"- Config SHA-256: `{manifest.get('config_sha256')}`",
            f"- Processed corpus build_manifest SHA-256: "
            f"`{manifest.get('processed_build_manifest_sha256')}`",
            f"- Split output root: `{manifest.get('output_root')}`",
            f"- See `metadata/checksums.json` inside the split directory.",
            "",
            "## 12. Frozen-split declaration",
            "",
            f"- **Frozen:** `{manifest.get('frozen')}`",
            f"- Split version: `{manifest.get('split_version')}`",
            f"- Corpus version: `{manifest.get('corpus_version')}`",
            f"- Created at: `{manifest.get('created_at')}`",
            f"- Git commit: `{manifest.get('git_commit')}`",
            "- Do not overwrite in place. Use a new version path + `--force-new-version` only when intentionally replacing policy.",
            "",
            "## 13. Rules for future tokenizer experiments",
            "",
            "- Train tokenizers **only** on `train/`.",
            "- Vocabulary selection **only** from `train/`.",
            "- Morphological-rule development may use train + separate development resources; **never test text**.",
            "- Validation may guide model selection / early stopping.",
            "- Test is for **final comparison only**.",
            "- Raw perplexity is **not** directly comparable across tokenizers.",
            "- Primary cross-tokenizer LM metric: **bits per character** or **bits per byte**.",
            "- External benchmarks (e.g. FLORES) remain **separate** from these corpus splits.",
            "",
        ]
    )
    return "\n".join(lines)


def freeze_marker_path(out_root: Path) -> Path:
    return out_root / "metadata" / "FROZEN_SPLIT.json"


def ensure_not_frozen(out_root: Path, *, force_new_version: bool) -> None:
    marker = freeze_marker_path(out_root)
    if marker.is_file() and not force_new_version:
        raise FileExistsError(
            f"Frozen split exists at {out_root}. Refusing to overwrite. "
            "Create a new version path or pass --force-new-version (discouraged for v0.1)."
        )
    if out_root.exists() and any(out_root.iterdir()) and not force_new_version:
        # Non-empty without marker still protected if README/checksums present
        if (out_root / "metadata" / "checksums.json").is_file():
            raise FileExistsError(
                f"Existing split outputs at {out_root}. Refusing to overwrite without "
                "--force-new-version."
            )


def run_build(
    *,
    config: dict[str, Any],
    config_path: Path,
    repo_root: Path,
    force_new_version: bool = False,
) -> dict[str, Any]:
    corpus_root = repo_root / config["processed_corpus_root"]
    out_root = repo_root / config["output_root"]
    ensure_not_frozen(out_root, force_new_version=force_new_version)

    if force_new_version and out_root.exists():
        shutil.rmtree(out_root)

    build_manifest_path = corpus_root / "metadata" / "build_manifest.json"
    if not build_manifest_path.is_file():
        raise FileNotFoundError(f"Missing processed build_manifest: {build_manifest_path}")
    processed_manifest_sha = sha256_file(build_manifest_path)
    config_sha = sha256_file(config_path)

    # Verify processed corpus file checksums if present
    checksums_path = corpus_root / "metadata" / "checksums.json"
    if checksums_path.is_file():
        expected = load_json(checksums_path)
        for rel, exp in expected.items():
            if not rel.startswith("corpus/"):
                continue
            p = corpus_root / rel
            if p.is_file():
                actual = sha256_file(p)
                if actual != exp:
                    raise ValueError(
                        f"Processed corpus checksum mismatch for {rel}: "
                        f"expected {exp}, got {actual}"
                    )

    docs_idx = load_documents_index(corpus_root / "metadata" / "documents.jsonl")
    source_ids = list(config.get("sources") or ["bible", "wikipedia"])
    target_chars = int(config["grouping"]["target_group_characters"])

    all_groups: list[Group] = []
    input_lines = 0
    input_chars = 0
    for sid in source_ids:
        recs = load_source_lines(corpus_root, sid, docs_idx)
        input_lines += len(recs)
        input_chars += sum(r.n_chars for r in recs)
        blocks = form_contiguous_char_blocks(
            recs, target_chars=target_chars, source_id=sid
        )
        all_groups.extend(blocks)

    assign_groups(
        all_groups,
        salt=str(config["assignment"]["salt"]),
        modulus=int(config["assignment"]["bucket_modulus"]),
        proportions=config["proportions"],
    )

    leakage_cfg = config.get("leakage") or {}
    exact_log = resolve_cross_split_line_conflicts(all_groups, use_normalized=False)
    norm_log = resolve_cross_split_line_conflicts(all_groups, use_normalized=True)

    # Final leakage counts (should be 0 after resolution)
    def cross_split_count(normalized: bool) -> int:
        key_splits: dict[str, set[str]] = defaultdict(set)
        for g in all_groups:
            assert g.split
            for lr in g.lines:
                if not lr.text.strip():
                    continue
                key = normalize_line(lr.text) if normalized else lr.text
                if key:
                    key_splits[key].add(g.split)
        return sum(1 for splits in key_splits.values() if len(splits) > 1)

    leakage = {
        "normalization": leakage_cfg.get("normalization"),
        "exact_cross_split_count": cross_split_count(False),
        "normalized_cross_split_count": cross_split_count(True),
        "exact_reassign_events": len(exact_log),
        "normalized_reassign_events": len(norm_log),
        "reassignment_log": exact_log + norm_log,
    }

    if leakage["exact_cross_split_count"] or leakage["normalized_cross_split_count"]:
        raise RuntimeError(
            "Leakage remains after conflict resolution: "
            f"exact={leakage['exact_cross_split_count']} "
            f"normalized={leakage['normalized_cross_split_count']}"
        )

    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "metadata").mkdir(parents=True, exist_ok=True)

    built = build_outputs(
        all_groups,
        out_root=out_root,
        source_ids=source_ids,
        combined_order=list(config.get("combined_source_order") or source_ids),
    )

    stats = {s: group_stats(all_groups, s) for s in SPLITS}
    stats["all"] = group_stats(all_groups, None)
    output_lines = sum(stats[s]["totals"]["lines"] for s in SPLITS)
    output_chars = sum(stats[s]["totals"]["characters"] for s in SPLITS)

    shingle_cfg = (leakage_cfg.get("optional_shingle_diagnostics") or {})
    if shingle_cfg.get("enabled", True):
        shingles = shingle_overlap_report(
            all_groups,
            n=int(shingle_cfg.get("shingle_size", 5)),
            max_pairs=int(shingle_cfg.get("max_report_pairs", 20)),
        )
    else:
        shingles = {"enabled": False}

    formulaic = formulaic_repetition_report(all_groups)

    created_at = utc_now_iso()
    manifest = {
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "created_at": created_at,
        "frozen": True,
        "split_version": config.get("split_version", "v0.1"),
        "corpus_name": config.get("corpus_name"),
        "corpus_version": config.get("corpus_version"),
        "config_path": str(
            config_path.relative_to(repo_root)
            if config_path.is_relative_to(repo_root)
            else config_path
        ),
        "config_sha256": config_sha,
        "processed_corpus_root": config["processed_corpus_root"],
        "processed_build_manifest_sha256": processed_manifest_sha,
        "output_root": config["output_root"],
        "git_commit": git_commit(repo_root),
        "assignment": config.get("assignment"),
        "proportions_target": config.get("proportions"),
        "grouping": {
            "strategy": config["grouping"]["strategy"],
            "target_group_characters": target_chars,
            "n_groups": len(all_groups),
        },
        "input_line_total": input_lines,
        "output_line_total": output_lines,
        "input_character_total": input_chars,
        "output_character_total": output_chars,
        "stats": stats,
        "leakage": {
            k: leakage[k]
            for k in (
                "normalization",
                "exact_cross_split_count",
                "normalized_cross_split_count",
                "exact_reassign_events",
                "normalized_reassign_events",
            )
        },
        "shingle_diagnostics": shingles,
        "tokenizer_policy": config.get("tokenizer_policy"),
        "file_checksums": built["file_checksums"],
    }

    write_json_atomic(out_root / "metadata" / "checksums.json", built["file_checksums"])
    write_json_atomic(freeze_marker_path(out_root), {
        "frozen": True,
        "split_version": manifest["split_version"],
        "corpus_version": manifest["corpus_version"],
        "created_at": created_at,
        "config_sha256": config_sha,
        "processed_build_manifest_sha256": processed_manifest_sha,
        "tool": manifest["tool"],
    })
    write_json_atomic(out_root / "metadata" / "split_manifest.json", manifest)

    readme = f"""# Corpus splits — {manifest['corpus_name']} {manifest['corpus_version']} / {manifest['split_version']}

**Frozen:** yes  
**Created:** {created_at}

## Layout

- `train/`, `validation/`, `test/` — each with `bible.txt`, `wikipedia.txt`, `combined.txt`
- `metadata/split_assignments.jsonl` — group → split map
- `metadata/*_documents.jsonl` — line-level membership
- `metadata/FROZEN_SPLIT.json` — freeze marker

## Tokenizer / LM rules

1. Train tokenizers **only** on `train/`.
2. Do **not** use `validation/` or `test/` for tokenizer training or vocabulary selection.
3. Validation is for model selection; test is for final comparison only.
4. Prefer bits/character or bits/byte for cross-tokenizer LM comparison (raw perplexity is not comparable).
5. External benchmarks (e.g. FLORES) are separate from these splits.

## Grouping note

Document-level Bible book/chapter and Wikipedia article IDs are **not** available in the
processed corpus. Groups are **contiguous character blocks** (~{target_chars} chars).
This is a documented fallback, not recovered structure.

Config: `{manifest['config_path']}`  
Config SHA-256: `{config_sha}`
"""
    write_text_atomic(out_root / "README.md", readme)
    manifest["file_checksums"]["README.md"] = sha256_file(out_root / "README.md")
    # refresh checksums file with README
    write_json_atomic(out_root / "metadata" / "checksums.json", manifest["file_checksums"])

    limitations = [
        "No Bible book/chapter/verse identifiers in processed text.",
        "No Wikipedia article/document boundaries in processed text or documents.jsonl.",
        "documents.jsonl entries are line-level (source_id:line_index) only.",
        "Contiguous character blocks used as safest reproducible grouping without inventing metadata.",
    ]
    report = render_report(
        config=config,
        stats=stats,
        leakage=leakage,
        shingles=shingles,
        formulaic=formulaic,
        manifest=manifest,
        grouping_limitations=limitations,
    )
    report_path = repo_root / config["report_path"]
    write_text_atomic(report_path, report)
    manifest_path = repo_root / config["manifest_path"]
    # repo-level manifest is a pointer + stats (not the full nested file list only)
    write_json_atomic(manifest_path, manifest)

    return {
        "output_root": str(out_root),
        "manifest_path": str(manifest_path),
        "report_path": str(report_path),
        "stats": stats,
        "leakage": leakage,
        "manifest": manifest,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build frozen corpus splits (train/val/test).")
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/data/split_v0_1.json"),
    )
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--force-new-version",
        action="store_true",
        help="Allow replacing an existing split directory (prefer a new version path instead).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    config_path = args.config if args.config.is_absolute() else root / args.config
    try:
        config = load_json(config_path)
        result = run_build(
            config=config,
            config_path=config_path,
            repo_root=root,
            force_new_version=bool(args.force_new_version),
        )
    except (OSError, ValueError, FileExistsError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"Split build complete → {result['output_root']}")
    print(f"  manifest: {result['manifest_path']}")
    print(f"  report:   {result['report_path']}")
    for s in SPLITS:
        t = result["stats"][s]["totals"]
        print(
            f"  {s}: lines={t['lines']} chars={t['characters']} groups={t['groups']}"
        )
    print(
        f"  leakage exact={result['leakage']['exact_cross_split_count']} "
        f"normalized={result['leakage']['normalized_cross_split_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
