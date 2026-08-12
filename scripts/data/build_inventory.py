#!/usr/bin/env python3
"""Build a machine-readable inventory of raw corpus files.

Scans a raw-data root, computes per-file statistics and SHA-256 checksums,
and writes a deterministic JSON inventory. Does not modify source files.

Requires Python 3.11+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHUNK_SIZE = 1024 * 1024  # 1 MiB


def sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file without loading it entirely into memory."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def detect_encoding(raw: bytes) -> str:
    """Best-effort encoding detection using the standard library only.

    Tries UTF-8 (with and without BOM), then reports latin-1 as a
    last-resort decode label when UTF-8 fails. Does not guess exotic
    encodings.
    """
    if raw.startswith(b"\xef\xbb\xbf"):
        try:
            raw.decode("utf-8-sig")
            return "utf-8-sig"
        except UnicodeDecodeError:
            pass
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        # latin-1 always decodes; label indicates fallback, not certainty
        return "latin-1-fallback"


def count_lines_and_chars(raw: bytes, encoding: str) -> tuple[int, int]:
    """Return (line_count, character_count).

    Line count matches ``wc -l``: number of newline (\\n) bytes.
    Character count is the length of the decoded Unicode string when
    decoding succeeds; for latin-1-fallback, length of latin-1 decode.
    """
    line_count = raw.count(b"\n")
    decode_enc = "utf-8-sig" if encoding == "utf-8-sig" else (
        "latin-1" if encoding == "latin-1-fallback" else "utf-8"
    )
    text = raw.decode(decode_enc)
    return line_count, len(text)


def source_id_from_path(path: Path, raw_dir: Path) -> str:
    """Map a file under raw_dir to a source_id (immediate subdirectory name).

    Files directly under raw_dir get source_id \"unassigned\".
    """
    try:
        rel = path.relative_to(raw_dir)
    except ValueError:
        return "unknown"
    parts = rel.parts
    if len(parts) >= 2:
        return parts[0]
    return "unassigned"


def discover_files(raw_dir: Path) -> list[Path]:
    """Recursively discover regular files under raw_dir, excluding READMEs.

    Sorted by relative path for deterministic output.
    """
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"Raw data directory does not exist: {raw_dir}")

    files: list[Path] = []
    for p in sorted(raw_dir.rglob("*")):
        if not p.is_file():
            continue
        # Skip documentation placed alongside raw data
        if p.name.upper() in {"README.MD", "README.TXT", "README"}:
            continue
        if p.name.startswith("."):
            continue
        files.append(p)
    return files


def invent_file(
    path: Path,
    raw_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Build inventory record for one file. Reads file for stats only."""
    raw = path.read_bytes()
    size_bytes = len(raw)
    checksum = hashlib.sha256(raw).hexdigest()
    encoding = detect_encoding(raw)
    line_count, char_count = count_lines_and_chars(raw, encoding)
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    try:
        rel_path = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        rel_path = path.as_posix()

    return {
        "source_id": source_id_from_path(path, raw_dir),
        "relative_path": rel_path,
        "filename": path.name,
        "size_bytes": size_bytes,
        "line_count": line_count,
        "character_count": char_count,
        "sha256": checksum,
        "encoding": encoding,
        "modification_timestamp": mtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    }


def build_inventory(
    raw_dir: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Scan raw_dir and return a full inventory document."""
    raw_dir = raw_dir.resolve()
    if repo_root is None:
        # Assume scripts/data/build_inventory.py → repo root is parents[2]
        repo_root = Path(__file__).resolve().parents[2]
    else:
        repo_root = repo_root.resolve()

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    files = discover_files(raw_dir)

    records: list[dict[str, Any]] = []
    for path in files:
        records.append(invent_file(path, raw_dir, repo_root))

    # Stable sort by relative_path
    records.sort(key=lambda r: r["relative_path"])

    total_size = sum(r["size_bytes"] for r in records)
    total_lines = sum(r["line_count"] for r in records)
    total_chars = sum(r["character_count"] for r in records)

    return {
        "inventory_generated_at": generated_at,
        "raw_dir": str(raw_dir.relative_to(repo_root)) if raw_dir.is_relative_to(repo_root) else str(raw_dir),
        "file_count": len(records),
        "files": records,
        "totals": {
            "file_count": len(records),
            "size_bytes": total_size,
            "line_count": total_lines,
            "character_count": total_chars,
        },
    }


def write_inventory(inventory: dict[str, Any], output: Path) -> None:
    """Write inventory JSON with stable formatting."""
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(inventory, indent=2, ensure_ascii=False, sort_keys=False)
    # Trailing newline for POSIX text files
    output.write_text(text + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a SHA-256 inventory of raw corpus files (read-only).",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Root directory of immutable raw sources (default: data/raw)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/metadata/inventory.json"),
        help="Path for inventory JSON (default: data/metadata/inventory.json)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root for relative paths (default: inferred from script location)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        inventory = build_inventory(args.raw_dir, repo_root=args.repo_root)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"error: failed to read raw data: {e}", file=sys.stderr)
        return 1

    try:
        write_inventory(inventory, args.output)
    except OSError as e:
        print(f"error: failed to write inventory: {e}", file=sys.stderr)
        return 1

    totals = inventory["totals"]
    print(
        f"Wrote inventory for {totals['file_count']} file(s) "
        f"({totals['size_bytes']} bytes) → {args.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
