#!/usr/bin/env python3
"""Local human-annotation UI for Wikipedia cleaning review samples.

Stdlib-only HTTP app. Reviewers may change only review_label and review_notes.
Immutable fields are validated on load and on every save.

Does not label automatically, call external APIs, modify raw/interim corpora,
or change cleaning rules.

Example:
  python scripts/data/run_cleaning_review.py \\
    --sample data/reports/cleaning_review_sample.jsonl \\
    --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import threading
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

TOOL_NAME = "run_cleaning_review"
TOOL_VERSION = "1.0.0"

ALLOWED_LABELS = frozenset(
    {
        "valid_chichewa",
        "useful_mixed_chichewa",
        "boilerplate_or_noise",
        "foreign_language",
        "duplicate",
        "uncertain",
    }
)

IMMUTABLE_FIELDS = (
    "review_id",
    "source_id",
    "original_line_number",
    "decision",
    "rule_id",
    "excerpt",
    "text_sha256",
)

# Additional fields that may exist and must also remain unchanged if present
PROTECTED_OPTIONAL_FIELDS = (
    "rule_type",
    "rule_description",
    "metrics",
)

MUTABLE_FIELDS = frozenset({"review_label", "review_notes"})

REQUIRED_FIELDS = IMMUTABLE_FIELDS + ("review_label", "review_notes")


class ReviewError(Exception):
    """User-facing / validation error."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def validate_record(rec: Any, index: int) -> dict[str, Any]:
    if not isinstance(rec, dict):
        raise ReviewError(f"Record {index}: expected object, got {type(rec).__name__}")
    for field in REQUIRED_FIELDS:
        if field not in rec:
            raise ReviewError(f"Record {index}: missing required field {field!r}")
    if not isinstance(rec["review_id"], str) or not rec["review_id"]:
        raise ReviewError(f"Record {index}: invalid review_id")
    if rec["source_id"] != "wikipedia" and not isinstance(rec["source_id"], str):
        raise ReviewError(f"Record {index}: invalid source_id")
    if not isinstance(rec["original_line_number"], int):
        raise ReviewError(f"Record {index}: original_line_number must be int")
    if rec["decision"] not in ("removed", "kept"):
        raise ReviewError(f"Record {index}: decision must be 'removed' or 'kept'")
    if rec["decision"] == "removed" and rec.get("rule_id") is None:
        raise ReviewError(f"Record {index}: removed records require rule_id")
    if rec["decision"] == "kept" and rec.get("rule_id") is not None:
        # kept may have rule_id null only
        pass
    if not isinstance(rec["excerpt"], str):
        raise ReviewError(f"Record {index}: excerpt must be string")
    if not isinstance(rec["text_sha256"], str) or len(rec["text_sha256"]) != 64:
        raise ReviewError(f"Record {index}: text_sha256 must be 64-char hex string")
    label = rec.get("review_label")
    if label is not None and label not in ALLOWED_LABELS:
        raise ReviewError(
            f"Record {index}: invalid review_label {label!r}; "
            f"allowed={sorted(ALLOWED_LABELS)}"
        )
    notes = rec.get("review_notes")
    if notes is not None and not isinstance(notes, str):
        raise ReviewError(f"Record {index}: review_notes must be string or null")
    return rec


def load_sample(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ReviewError(f"Sample file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ReviewError(f"Cannot read sample: {e}") from e
    records: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise ReviewError(f"Malformed JSONL at line {i}: {e}") from e
        records.append(validate_record(obj, i))
    if not records:
        raise ReviewError("Sample file contains no records")
    ids = [r["review_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ReviewError("Duplicate review_id values in sample")
    return records


def snapshot_immutable(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    snaps: list[dict[str, Any]] = []
    for rec in records:
        snap = {f: copy.deepcopy(rec[f]) for f in IMMUTABLE_FIELDS}
        for f in PROTECTED_OPTIONAL_FIELDS:
            if f in rec:
                snap[f] = copy.deepcopy(rec[f])
        snaps.append(snap)
    return snaps


def assert_immutable_intact(
    original: list[dict[str, Any]],
    current: list[dict[str, Any]],
) -> None:
    if len(original) != len(current):
        raise ReviewError(
            f"Record count changed: was {len(original)}, now {len(current)}"
        )
    for i, (o, c) in enumerate(zip(original, current)):
        for field in IMMUTABLE_FIELDS:
            if o.get(field) != c.get(field):
                raise ReviewError(
                    f"Immutable field {field!r} changed at index {i} "
                    f"(review_id={o.get('review_id')})"
                )
        for field in PROTECTED_OPTIONAL_FIELDS:
            if field in o and o.get(field) != c.get(field):
                raise ReviewError(
                    f"Protected field {field!r} changed at index {i} "
                    f"(review_id={o.get('review_id')})"
                )


def apply_annotation(
    records: list[dict[str, Any]],
    original_snapshot: list[dict[str, Any]],
    index: int,
    label: str | None,
    notes: str | None,
) -> None:
    if index < 0 or index >= len(records):
        raise ReviewError(f"Index out of range: {index}")
    if label is not None and label not in ALLOWED_LABELS:
        raise ReviewError(f"Invalid label: {label!r}")
    if notes is not None and not isinstance(notes, str):
        raise ReviewError("notes must be a string or null")
    # Only mutate allowed fields
    records[index]["review_label"] = label
    records[index]["review_notes"] = notes
    assert_immutable_intact(original_snapshot, records)
    validate_record(records[index], index)


def serialize_jsonl(records: list[dict[str, Any]]) -> str:
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    return "\n".join(lines) + ("\n" if lines else "")


def atomic_save(
    path: Path,
    records: list[dict[str, Any]],
    original_snapshot: list[dict[str, Any]],
    backup_dir: Path,
    *,
    create_backup: bool = True,
) -> dict[str, Any]:
    """Validate and atomically write JSONL; optional timestamped backup first."""
    assert_immutable_intact(original_snapshot, records)
    for i, rec in enumerate(records):
        validate_record(rec, i)

    # Preserve order: already list order
    payload = serialize_jsonl(records)

    # Re-parse payload to ensure round-trip validity
    reloaded: list[dict[str, Any]] = []
    for i, line in enumerate(payload.splitlines(), start=1):
        if not line.strip():
            continue
        reloaded.append(validate_record(json.loads(line), i))
    assert_immutable_intact(original_snapshot, reloaded)

    path = path.resolve()
    backup_dir = backup_dir.resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path: Path | None = None
    if create_backup and path.is_file():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = backup_dir / f"cleaning_review_sample.{ts}.jsonl"
        # Avoid clobber if same-second: add counter
        n = 1
        while backup_path.exists():
            backup_path = backup_dir / f"cleaning_review_sample.{ts}.{n}.jsonl"
            n += 1
        shutil.copy2(path, backup_path)

    # Write temp in same directory for atomic replace
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".cleaning_review_",
        suffix=".jsonl.tmp",
        dir=str(parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            try:
                import os

                os.fsync(f.fileno())
            except OSError:
                pass
        # Final validation of temp file on disk
        disk_records = load_sample(tmp_path)
        assert_immutable_intact(original_snapshot, disk_records)
        tmp_path.replace(path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    return {
        "saved_at": utc_now_iso(),
        "path": str(path),
        "backup_path": str(backup_path) if backup_path else None,
        "n_records": len(records),
    }


class ReviewSession:
    """In-memory review session with filters and dirty tracking."""

    def __init__(
        self,
        sample_path: Path,
        backup_dir: Path,
        autosave_every: int = 10,
    ) -> None:
        self.sample_path = sample_path.resolve()
        self.backup_dir = backup_dir.resolve()
        self.autosave_every = max(1, autosave_every)
        self.lock = threading.RLock()

        self.records = load_sample(self.sample_path)
        self.original_snapshot = snapshot_immutable(self.records)
        self.dirty = False
        self.last_save_at: str | None = None
        self.last_save_error: str | None = None
        self.last_backup_path: str | None = None
        self.edits_since_save = 0

        # Filters
        self.filter_unlabeled_only = False
        self.filter_decision: str | None = None  # removed|kept|None
        self.filter_rule_id: str | None = None

        self.view_index = 0  # index into filtered list
        self._sync_view_to_first_unlabeled()

    def _sync_view_to_first_unlabeled(self) -> None:
        indices = self.filtered_indices()
        for vi, ri in enumerate(indices):
            if self.records[ri].get("review_label") is None:
                self.view_index = vi
                return
        self.view_index = 0 if indices else 0

    def counts(self) -> dict[str, int]:
        labeled = 0
        unlabeled = 0
        uncertain = 0
        for r in self.records:
            lab = r.get("review_label")
            if lab is None:
                unlabeled += 1
            else:
                labeled += 1
                if lab == "uncertain":
                    uncertain += 1
        return {
            "total": len(self.records),
            "labeled": labeled,
            "unlabeled": unlabeled,
            "uncertain": uncertain,
        }

    def label_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {lab: 0 for lab in sorted(ALLOWED_LABELS)}
        dist["null"] = 0
        for r in self.records:
            lab = r.get("review_label")
            if lab is None:
                dist["null"] += 1
            elif lab in dist:
                dist[lab] += 1
        return dist

    def rule_ids(self) -> list[str]:
        ids = sorted(
            {
                r["rule_id"]
                for r in self.records
                if r.get("rule_id") is not None
            }
        )
        return ids

    def filtered_indices(self) -> list[int]:
        out: list[int] = []
        for i, r in enumerate(self.records):
            if self.filter_unlabeled_only and r.get("review_label") is not None:
                continue
            if self.filter_decision and r.get("decision") != self.filter_decision:
                continue
            if self.filter_rule_id is not None:
                if r.get("rule_id") != self.filter_rule_id:
                    continue
            out.append(i)
        return out

    def current_record_index(self) -> int | None:
        indices = self.filtered_indices()
        if not indices:
            return None
        if self.view_index < 0:
            self.view_index = 0
        if self.view_index >= len(indices):
            self.view_index = len(indices) - 1
        return indices[self.view_index]

    def set_filters(
        self,
        *,
        unlabeled_only: bool | None = None,
        decision: str | None | object = ...,
        rule_id: str | None | object = ...,
    ) -> None:
        if unlabeled_only is not None:
            self.filter_unlabeled_only = bool(unlabeled_only)
        if decision is not ...:
            if decision is None or decision == "":
                self.filter_decision = None
            elif decision in ("removed", "kept"):
                self.filter_decision = str(decision)
            else:
                raise ReviewError("decision filter must be removed, kept, or empty")
        if rule_id is not ...:
            if rule_id is None or rule_id == "":
                self.filter_rule_id = None
            else:
                self.filter_rule_id = str(rule_id)
        # Clamp view
        indices = self.filtered_indices()
        if not indices:
            self.view_index = 0
        elif self.view_index >= len(indices):
            self.view_index = len(indices) - 1

    def navigate(self, action: str, jump_to: int | None = None) -> None:
        indices = self.filtered_indices()
        if not indices:
            self.view_index = 0
            return
        if action == "next":
            self.view_index = min(self.view_index + 1, len(indices) - 1)
        elif action == "prev":
            self.view_index = max(self.view_index - 1, 0)
        elif action == "goto":
            if jump_to is None:
                raise ReviewError("goto requires jump_to (1-based filtered position)")
            # 1-based position in filtered list
            pos = int(jump_to) - 1
            if pos < 0 or pos >= len(indices):
                raise ReviewError(
                    f"jump_to out of range 1..{len(indices)}"
                )
            self.view_index = pos
        elif action == "goto_absolute":
            # 1-based absolute record number among all records
            if jump_to is None:
                raise ReviewError("goto_absolute requires jump_to")
            abs_i = int(jump_to) - 1
            if abs_i < 0 or abs_i >= len(self.records):
                raise ReviewError(
                    f"absolute index out of range 1..{len(self.records)}"
                )
            if abs_i in indices:
                self.view_index = indices.index(abs_i)
            else:
                # clear filters that hide it? Better error:
                raise ReviewError(
                    "Record not visible under current filters; clear filters first"
                )
        else:
            raise ReviewError(f"Unknown navigate action: {action}")

    def set_label(self, label: str | None, notes: str | None = None) -> None:
        ri = self.current_record_index()
        if ri is None:
            raise ReviewError("No record visible under current filters")
        # Preserve notes if not provided
        if notes is None:
            notes = self.records[ri].get("review_notes")
        apply_annotation(
            self.records, self.original_snapshot, ri, label, notes
        )
        self.dirty = True
        self.edits_since_save += 1
        self.last_save_error = None

    def set_notes(self, notes: str | None) -> None:
        ri = self.current_record_index()
        if ri is None:
            raise ReviewError("No record visible under current filters")
        label = self.records[ri].get("review_label")
        apply_annotation(
            self.records, self.original_snapshot, ri, label, notes
        )
        self.dirty = True
        self.edits_since_save += 1
        self.last_save_error = None

    def maybe_autosave(self) -> dict[str, Any] | None:
        if self.dirty and self.edits_since_save >= self.autosave_every:
            return self.save(create_backup=True)
        return None

    def save(self, *, create_backup: bool = True) -> dict[str, Any]:
        try:
            result = atomic_save(
                self.sample_path,
                self.records,
                self.original_snapshot,
                self.backup_dir,
                create_backup=create_backup,
            )
            self.dirty = False
            self.edits_since_save = 0
            self.last_save_at = result["saved_at"]
            self.last_backup_path = result.get("backup_path")
            self.last_save_error = None
            return result
        except Exception as e:
            self.last_save_error = str(e)
            raise

    def state_dict(self) -> dict[str, Any]:
        indices = self.filtered_indices()
        ri = self.current_record_index()
        rec = copy.deepcopy(self.records[ri]) if ri is not None else None
        counts = self.counts()
        complete = counts["unlabeled"] == 0 and counts["total"] > 0
        return {
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "sample_path": str(self.sample_path),
            "counts": counts,
            "label_distribution": self.label_distribution(),
            "complete": complete,
            "dirty": self.dirty,
            "last_save_at": self.last_save_at,
            "last_save_error": self.last_save_error,
            "last_backup_path": self.last_backup_path,
            "edits_since_save": self.edits_since_save,
            "autosave_every": self.autosave_every,
            "filters": {
                "unlabeled_only": self.filter_unlabeled_only,
                "decision": self.filter_decision,
                "rule_id": self.filter_rule_id,
            },
            "rule_ids": self.rule_ids(),
            "allowed_labels": sorted(ALLOWED_LABELS),
            "filtered_count": len(indices),
            "view_position": self.view_index + 1 if indices else 0,
            "view_total": len(indices),
            "absolute_index": (ri + 1) if ri is not None else None,
            "record": rec,
            "summarize_command": (
                "python scripts/data/summarize_cleaning_review.py \\\n"
                "  --config configs/data/cleaning_review.json \\\n"
                "  --sample data/reports/cleaning_review_sample.jsonl"
            ),
        }


# ---------------------------------------------------------------------------
# HTML UI
# ---------------------------------------------------------------------------


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Chichewa Cleaning Review</title>
<style>
  :root {
    --bg: #0f1419;
    --panel: #1a2332;
    --text: #e7ecf3;
    --muted: #9aa8b8;
    --accent: #3d9cf0;
    --ok: #3ecf8e;
    --warn: #f0b429;
    --bad: #f07178;
    --border: #2a3544;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.45;
  }
  header {
    padding: 0.75rem 1.25rem; border-bottom: 1px solid var(--border);
    background: var(--panel); display: flex; flex-wrap: wrap; gap: 0.75rem;
    align-items: center; justify-content: space-between;
  }
  header h1 { font-size: 1.05rem; margin: 0; font-weight: 600; }
  .status { font-size: 0.9rem; color: var(--muted); }
  .status .dirty { color: var(--warn); font-weight: 600; }
  .status .saved { color: var(--ok); }
  .status .err { color: var(--bad); }
  main { max-width: 960px; margin: 0 auto; padding: 1rem 1.25rem 3rem; }
  .panel {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1.1rem; margin-bottom: 1rem;
  }
  .meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.5rem 1rem; }
  .meta dt { color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; }
  .meta dd { margin: 0.1rem 0 0; font-weight: 500; word-break: break-word; }
  .badge {
    display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px;
    font-size: 0.8rem; font-weight: 600;
  }
  .badge.removed { background: #5a2a32; color: #ffc9cf; }
  .badge.kept { background: #1f4a38; color: #b6f0d2; }
  .excerpt {
    white-space: pre-wrap; word-break: break-word; font-size: 1.15rem;
    line-height: 1.55; padding: 0.85rem 1rem; background: #0c1016;
    border-radius: 8px; border: 1px solid var(--border); min-height: 4rem;
  }
  .labels { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.5rem; }
  button, select, input, textarea {
    font: inherit; color: var(--text); background: #121a24;
    border: 1px solid var(--border); border-radius: 8px; padding: 0.5rem 0.7rem;
  }
  button {
    cursor: pointer; background: #243044; border-color: #35485f;
  }
  button:hover { background: #2d3c54; }
  button.primary { background: var(--accent); border-color: #2d7ec4; color: #041018; font-weight: 600; }
  button.label-btn.active { outline: 2px solid var(--ok); }
  button.danger { background: #5a2a32; }
  textarea { width: 100%; min-height: 4rem; resize: vertical; }
  .row { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin-top: 0.6rem; }
  .filters label { font-size: 0.85rem; color: var(--muted); display: flex; gap: 0.35rem; align-items: center; }
  details { color: var(--muted); font-size: 0.85rem; }
  details summary { cursor: pointer; color: var(--accent); }
  .help kbd {
    background: #243044; border: 1px solid #3a4d66; border-radius: 4px;
    padding: 0.05rem 0.35rem; font-size: 0.8rem;
  }
  .complete-banner {
    background: #163528; border: 1px solid #2f6b4f; border-radius: 10px;
    padding: 1rem; margin-bottom: 1rem;
  }
  .complete-banner pre {
    background: #0c1016; padding: 0.75rem; border-radius: 6px; overflow-x: auto;
  }
  .counts span { margin-right: 0.85rem; }
</style>
</head>
<body>
<header>
  <h1>Chichewa cleaning review</h1>
  <div class="status" id="statusLine">Loading…</div>
</header>
<main>
  <div id="completeBanner" class="complete-banner" hidden></div>

  <div class="panel filters">
    <div class="row">
      <span class="counts" id="counts"></span>
    </div>
    <div class="row">
      <label><input type="checkbox" id="fltUnlabeled"/> Unlabeled only (<kbd>U</kbd>)</label>
      <label>Decision
        <select id="fltDecision">
          <option value="">All</option>
          <option value="removed">removed</option>
          <option value="kept">kept</option>
        </select>
      </label>
      <label>Rule
        <select id="fltRule"><option value="">All rules</option></select>
      </label>
      <label>Jump (filtered #)
        <input id="jumpTo" type="number" min="1" style="width:5rem"/>
      </label>
      <button type="button" id="btnJump">Go</button>
    </div>
    <div class="row">
      <button type="button" id="btnPrev">← Prev</button>
      <button type="button" id="btnNext">Next →</button>
      <button type="button" id="btnSave" class="primary">Save (<kbd>S</kbd>)</button>
      <span id="progress"></span>
    </div>
  </div>

  <div class="panel" id="recordPanel">
    <dl class="meta" id="meta"></dl>
    <h2 style="font-size:0.9rem;color:var(--muted);margin:1rem 0 0.4rem;">Excerpt</h2>
    <div class="excerpt" id="excerpt"></div>
    <h2 style="font-size:0.9rem;color:var(--muted);margin:1rem 0 0.4rem;">Label</h2>
    <div class="labels" id="labels"></div>
    <h2 style="font-size:0.9rem;color:var(--muted);margin:1rem 0 0.4rem;">Notes (optional)</h2>
    <textarea id="notes" placeholder="Optional reviewer notes…"></textarea>
    <div class="row">
      <button type="button" id="btnApplyNotes">Apply notes</button>
    </div>
    <details style="margin-top:1rem;">
      <summary>Technical details</summary>
      <pre id="tech" style="white-space:pre-wrap;word-break:break-all;"></pre>
    </details>
  </div>

  <div class="panel help">
    <strong>Keyboard</strong>:
    <kbd>1</kbd> valid_chichewa ·
    <kbd>2</kbd> useful_mixed_chichewa ·
    <kbd>3</kbd> boilerplate_or_noise ·
    <kbd>4</kbd> foreign_language ·
    <kbd>5</kbd> duplicate ·
    <kbd>6</kbd> uncertain ·
    <kbd>←</kbd>/<kbd>→</kbd> prev/next ·
    <kbd>S</kbd> save ·
    <kbd>U</kbd> toggle unlabeled filter
  </div>
</main>
<script>
const LABELS = [
  ["1", "valid_chichewa"],
  ["2", "useful_mixed_chichewa"],
  ["3", "boilerplate_or_noise"],
  ["4", "foreign_language"],
  ["5", "duplicate"],
  ["6", "uncertain"],
];

let state = null;
let notesDirty = false;

async function api(path, opts) {
  const res = await fetch(path, {
    headers: {"Content-Type": "application/json"},
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function setStatus(state) {
  const el = document.getElementById("statusLine");
  let html = "";
  if (state.dirty) html += '<span class="dirty">Unsaved changes</span> · ';
  else html += '<span class="saved">All changes saved</span> · ';
  if (state.last_save_at) html += `Last save: ${state.last_save_at} · `;
  if (state.last_save_error) html += `<span class="err">Save error: ${esc(state.last_save_error)}</span> · `;
  html += state.complete ? '<span class="saved">COMPLETE</span>' : 'In progress';
  el.innerHTML = html;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  })[c]);
}

function render(stateIn) {
  state = stateIn;
  setStatus(state);
  const c = state.counts;
  document.getElementById("counts").innerHTML =
    `<span>Total <strong>${c.total}</strong></span>` +
    `<span>Labeled <strong>${c.labeled}</strong></span>` +
    `<span>Unlabeled <strong>${c.unlabeled}</strong></span>` +
    `<span>Uncertain <strong>${c.uncertain}</strong></span>`;

  document.getElementById("progress").textContent =
    state.view_total
      ? `View ${state.view_position} / ${state.view_total} (absolute #${state.absolute_index})`
      : "No records match filters";

  // filters
  document.getElementById("fltUnlabeled").checked = !!state.filters.unlabeled_only;
  document.getElementById("fltDecision").value = state.filters.decision || "";
  const ruleSel = document.getElementById("fltRule");
  const curRule = state.filters.rule_id || "";
  ruleSel.innerHTML = '<option value="">All rules</option>' +
    state.rule_ids.map(r => `<option value="${esc(r)}">${esc(r)}</option>`).join("");
  ruleSel.value = curRule;

  // complete banner
  const banner = document.getElementById("completeBanner");
  if (state.complete) {
    banner.hidden = false;
    const dist = state.label_distribution;
    const distLines = Object.entries(dist).map(([k,v]) => `${k}: ${v}`).join("\n");
    banner.innerHTML = `<strong>All records labeled.</strong>
      <p>Label distribution:</p>
      <pre>${esc(distLines)}</pre>
      <p>Generate validation metrics (manual step):</p>
      <pre>${esc(state.summarize_command)}</pre>
      <p>This tool does not run the summarizer automatically.</p>`;
  } else {
    banner.hidden = true;
  }

  const rec = state.record;
  const meta = document.getElementById("meta");
  const excerpt = document.getElementById("excerpt");
  const labels = document.getElementById("labels");
  const notes = document.getElementById("notes");
  const tech = document.getElementById("tech");

  if (!rec) {
    meta.innerHTML = "<p>No record to display under current filters.</p>";
    excerpt.textContent = "";
    labels.innerHTML = "";
    notes.value = "";
    tech.textContent = "";
    return;
  }

  meta.innerHTML = `
    <div><dt>Decision</dt><dd><span class="badge ${esc(rec.decision)}">${esc(rec.decision)}</span></dd></div>
    <div><dt>Rule</dt><dd>${esc(rec.rule_id ?? "—")}</dd></div>
    <div><dt>Original line</dt><dd>${esc(rec.original_line_number)}</dd></div>
    <div><dt>Source</dt><dd>${esc(rec.source_id)}</dd></div>
    <div><dt>Current label</dt><dd>${esc(rec.review_label ?? "(unlabeled)")}</dd></div>
    <div><dt>Review ID</dt><dd style="font-size:0.85rem">${esc(rec.review_id)}</dd></div>
  `;
  excerpt.textContent = rec.excerpt || "";
  if (!notesDirty) notes.value = rec.review_notes || "";

  labels.innerHTML = LABELS.map(([key, lab]) => {
    const active = rec.review_label === lab ? "active" : "";
    return `<button type="button" class="label-btn ${active}" data-label="${lab}">
      <kbd>${key}</kbd> ${lab}</button>`;
  }).join("");

  labels.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => setLabel(btn.dataset.label));
  });

  tech.textContent =
    `text_sha256: ${rec.text_sha256}\n` +
    `rule_type: ${rec.rule_type ?? ""}\n` +
    `rule_description: ${rec.rule_description ?? ""}\n` +
    `metrics: ${JSON.stringify(rec.metrics ?? {}, null, 2)}`;
}

async function refresh() {
  const data = await api("/api/state");
  notesDirty = false;
  render(data);
}

async function setLabel(label) {
  const notes = document.getElementById("notes").value;
  await api("/api/label", {
    method: "POST",
    body: JSON.stringify({label, notes, advance: true}),
  });
  notesDirty = false;
  await refresh();
}

async function save() {
  try {
    await api("/api/save", {method: "POST", body: "{}"});
    await refresh();
  } catch (e) {
    alert("Save failed: " + e.message);
    await refresh();
  }
}

async function nav(action, jump_to) {
  await api("/api/nav", {
    method: "POST",
    body: JSON.stringify({action, jump_to}),
  });
  notesDirty = false;
  await refresh();
}

async function applyFilters() {
  await api("/api/filters", {
    method: "POST",
    body: JSON.stringify({
      unlabeled_only: document.getElementById("fltUnlabeled").checked,
      decision: document.getElementById("fltDecision").value,
      rule_id: document.getElementById("fltRule").value,
    }),
  });
  notesDirty = false;
  await refresh();
}

document.getElementById("btnPrev").onclick = () => nav("prev");
document.getElementById("btnNext").onclick = () => nav("next");
document.getElementById("btnSave").onclick = () => save();
document.getElementById("btnJump").onclick = () => {
  const v = parseInt(document.getElementById("jumpTo").value, 10);
  nav("goto", v);
};
document.getElementById("fltUnlabeled").onchange = applyFilters;
document.getElementById("fltDecision").onchange = applyFilters;
document.getElementById("fltRule").onchange = applyFilters;
document.getElementById("notes").addEventListener("input", () => { notesDirty = true; });
document.getElementById("btnApplyNotes").onclick = async () => {
  const notes = document.getElementById("notes").value;
  await api("/api/notes", {method: "POST", body: JSON.stringify({notes})});
  notesDirty = false;
  await refresh();
};

document.addEventListener("keydown", (ev) => {
  const tag = (ev.target && ev.target.tagName) || "";
  if (tag === "TEXTAREA" || tag === "INPUT" || tag === "SELECT") {
    if (ev.key === "Escape") ev.target.blur();
    return;
  }
  if (ev.key === "ArrowRight") { ev.preventDefault(); nav("next"); }
  else if (ev.key === "ArrowLeft") { ev.preventDefault(); nav("prev"); }
  else if (ev.key === "s" || ev.key === "S") { ev.preventDefault(); save(); }
  else if (ev.key === "u" || ev.key === "U") {
    ev.preventDefault();
    const cb = document.getElementById("fltUnlabeled");
    cb.checked = !cb.checked;
    applyFilters();
  } else if (ev.key >= "1" && ev.key <= "6") {
    ev.preventDefault();
    const lab = LABELS[parseInt(ev.key, 10) - 1][1];
    setLabel(lab);
  }
});

refresh().catch(e => {
  document.getElementById("statusLine").innerHTML =
    `<span class="err">Failed to load: ${esc(e.message)}</span>`;
});
</script>
</body>
</html>
"""


def make_handler(session: ReviewSession):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            # quieter default logging
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj: Any) -> None:
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self._send(code, data, "application/json; charset=utf-8")

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length else b"{}"
            try:
                obj = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError as e:
                raise ReviewError(f"Invalid JSON body: {e}") from e
            if not isinstance(obj, dict):
                raise ReviewError("JSON body must be an object")
            return obj

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                body = HTML_PAGE.encode("utf-8")
                self._send(200, body, "text/html; charset=utf-8")
                return
            if parsed.path == "/api/state":
                with session.lock:
                    self._json(200, session.state_dict())
                return
            self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/label":
                    body = self._read_json()
                    label = body.get("label")
                    notes = body.get("notes")
                    advance = bool(body.get("advance", False))
                    with session.lock:
                        session.set_label(label, notes)
                        if advance:
                            # move to next unlabeled if filter allows, else next
                            session.navigate("next")
                        autosave = session.maybe_autosave()
                        state = session.state_dict()
                        if autosave:
                            state["autosaved"] = autosave
                    self._json(200, state)
                    return

                if parsed.path == "/api/notes":
                    body = self._read_json()
                    with session.lock:
                        session.set_notes(body.get("notes"))
                        session.maybe_autosave()
                        self._json(200, session.state_dict())
                    return

                if parsed.path == "/api/nav":
                    body = self._read_json()
                    with session.lock:
                        session.navigate(
                            body.get("action", "next"),
                            body.get("jump_to"),
                        )
                        self._json(200, session.state_dict())
                    return

                if parsed.path == "/api/filters":
                    body = self._read_json()
                    with session.lock:
                        session.set_filters(
                            unlabeled_only=body.get("unlabeled_only"),
                            decision=body.get("decision", ...),
                            rule_id=body.get("rule_id", ...),
                        )
                        self._json(200, session.state_dict())
                    return

                if parsed.path == "/api/save":
                    with session.lock:
                        result = session.save(create_backup=True)
                        state = session.state_dict()
                        state["save_result"] = result
                    self._json(200, state)
                    return

                self._json(404, {"error": "not found"})
            except ReviewError as e:
                self._json(400, {"error": str(e)})
            except OSError as e:
                self._json(500, {"error": f"I/O error: {e}"})
            except Exception as e:
                traceback.print_exc()
                self._json(500, {"error": f"Internal error: {e}"})

    return Handler


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Local human-annotation UI for cleaning review JSONL."
    )
    p.add_argument(
        "--sample",
        type=Path,
        default=Path("data/reports/cleaning_review_sample.jsonl"),
    )
    p.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("data/reports/cleaning_review_backups"),
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument(
        "--autosave-every",
        type=int,
        default=10,
        help="Create checkpoint save after this many edits (default 10).",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Resolve relative paths against this root (default: cwd).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    sample = args.sample if args.sample.is_absolute() else root / args.sample
    backup_dir = (
        args.backup_dir
        if args.backup_dir.is_absolute()
        else root / args.backup_dir
    )

    try:
        session = ReviewSession(
            sample_path=sample,
            backup_dir=backup_dir,
            autosave_every=args.autosave_every,
        )
    except ReviewError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    counts = session.counts()
    print(f"{TOOL_NAME} v{TOOL_VERSION}")
    print(f"  sample:    {sample}")
    print(f"  backups:   {backup_dir}")
    print(
        f"  records:   {counts['total']} "
        f"(labeled={counts['labeled']}, unlabeled={counts['unlabeled']})"
    )
    print(f"  open:      http://{args.host}:{args.port}/")
    print("  Press Ctrl+C to stop. Save with S or the Save button.")

    handler = make_handler(session)
    try:
        server = ThreadingHTTPServer((args.host, args.port), handler)
    except OSError as e:
        print(f"error: cannot bind {args.host}:{args.port}: {e}", file=sys.stderr)
        return 1

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down…")
        if session.dirty:
            print("Unsaved changes detected — attempting final save…")
            try:
                session.save(create_backup=True)
                print("Final save OK.")
            except Exception as e:
                print(f"Final save FAILED: {e}", file=sys.stderr)
                print("Your previous on-disk JSONL was not truncated.", file=sys.stderr)
                return 2
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
