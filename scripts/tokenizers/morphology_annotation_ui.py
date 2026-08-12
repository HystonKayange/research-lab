#!/usr/bin/env python3
"""Lightweight offline morphology annotation interface (stdlib only).

- Never loads locked holdout or LM test
- Incremental JSONL save with no silent overwrites of other annotators
- Resume support
- Alternative analyses + uncertain / no-analysis
- Export JSONL and CSV

Usage:
  .venv/bin/python scripts/tokenizers/morphology_annotation_ui.py \\
    --items data/research/morphology_benchmark_v0.1/development/pilot_40.jsonl \\
    --annotator-id annotator_a --port 8765
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common import utc_now_iso  # noqa: E402

TOOL_NAME = "morphology_annotation_ui"
TOOL_VERSION = "0.1.0"

PHENOMENON_OPTIONS = [
    "no_meaningful_segmentation",
    "uncertain_segmentation",
    "multiple_plausible_analyses",
    "insufficient_context",
    "non_chichewa_or_mixed",
    "spelling_or_ocr_issue",
    "apparent_inflectional_boundary",
    "apparent_derivational_boundary",
    "apparent_stem_or_root",
    "unresolved_analysis",
    "apparent_prefix",
    "apparent_suffix",
    "locative_like",
    "negation_like",
    "noun_class_like",
    "other",
]


def refuse_locked(path: Path | str) -> None:
    s = str(path).replace("\\", "/")
    if "/locked/" in s and "/released/" not in s:
        raise RuntimeError(f"refusing locked holdout path: {path}")
    if "/test/" in s:
        raise RuntimeError(f"refusing test path: {path}")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_annotations_state(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        iid = row.get("item_id")
        if iid:
            out[str(iid)] = row
    return out


def atomic_write_jsonl(path: Path, rows_by_id: dict[str, dict[str, Any]], order: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for iid in order:
            if iid in rows_by_id:
                f.write(json.dumps(rows_by_id[iid], ensure_ascii=False) + "\n")
        # any extras
        for iid, row in sorted(rows_by_id.items()):
            if iid not in order:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def export_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "item_id",
        "surface_form",
        "context",
        "proposed_segmentation",
        "alternative_segmentation",
        "boundary_positions",
        "phenomenon_tags",
        "no_segmentation_required",
        "mixed_language",
        "spelling_or_ocr_issue",
        "insufficient_context",
        "uncertain",
        "confidence",
        "annotator_id",
        "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            row = dict(r)
            tags = row.get("phenomenon_tags")
            if isinstance(tags, list):
                row["phenomenon_tags"] = "|".join(tags)
            w.writerow(row)


class AnnotationState:
    def __init__(
        self,
        items: list[dict[str, Any]],
        *,
        annotator_id: str,
        save_path: Path,
        export_csv_path: Path,
    ) -> None:
        self.items = items
        self.order = [str(r["item_id"]) for r in items]
        self.by_id = {str(r["item_id"]): r for r in items}
        self.annotator_id = annotator_id
        self.save_path = save_path
        self.export_csv_path = export_csv_path
        self.annotations = load_annotations_state(save_path)
        self.lock = threading.Lock()
        self.hide_tokenizer_hints = False
        # ensure save path does not mix annotators
        for row in self.annotations.values():
            aid = row.get("annotator_id")
            if aid and aid != annotator_id:
                raise SystemExit(
                    f"Save file {save_path} contains annotator_id={aid}, "
                    f"expected {annotator_id}. Use a different --save path."
                )

    def get_ann(self, item_id: str) -> dict[str, Any]:
        return self.annotations.get(item_id) or {}

    def save_item(self, item_id: str, fields: dict[str, Any]) -> None:
        with self.lock:
            if item_id not in self.by_id:
                raise KeyError(item_id)
            src = self.by_id[item_id]
            rec = {
                "item_id": item_id,
                "surface_form": src.get("surface_form"),
                "context": src.get("context"),
                "source": src.get("source"),
                "split": src.get("split"),
                "line_ref": src.get("line_ref"),
                "bpe_tokens": src.get("bpe_tokens"),
                "unigram_tokens": src.get("unigram_tokens"),
                "automatic_tags": src.get("automatic_tags"),
                "candidate_strata": src.get("candidate_strata"),
                "proposed_segmentation": fields.get("proposed_segmentation") or None,
                "alternative_segmentation": fields.get("alternative_segmentation") or None,
                "boundary_positions": fields.get("boundary_positions") or None,
                "phenomenon_tags": fields.get("phenomenon_tags") or [],
                "no_segmentation_required": fields.get("no_segmentation_required"),
                "mixed_language": fields.get("mixed_language"),
                "spelling_or_ocr_issue": fields.get("spelling_or_ocr_issue"),
                "insufficient_context": fields.get("insufficient_context"),
                "uncertain": fields.get("uncertain"),
                "confidence": fields.get("confidence"),
                "annotator_id": self.annotator_id,
                "notes": fields.get("notes") or None,
                "adjudication_status": "annotated",
                "updated_at": utc_now_iso(),
                "source_item_preserved": True,
            }
            self.annotations[item_id] = rec
            atomic_write_jsonl(self.save_path, self.annotations, self.order)
            export_csv(
                self.export_csv_path,
                [self.annotations[i] for i in self.order if i in self.annotations],
            )

    def progress(self) -> tuple[int, int]:
        done = sum(1 for i in self.order if i in self.annotations)
        return done, len(self.order)


def bool_from_form(qs: dict[str, list[str]], key: str) -> bool | None:
    if key not in qs:
        return None
    v = qs[key][0].strip().lower()
    if v in ("", "unset"):
        return None
    return v in ("true", "1", "on", "yes")


def page(state: AnnotationState, index: int, message: str = "") -> str:
    n = len(state.order)
    index = max(0, min(index, n - 1))
    iid = state.order[index]
    src = state.by_id[iid]
    ann = state.get_ann(iid)
    done, total = state.progress()
    tags_selected = set(ann.get("phenomenon_tags") or [])
    if isinstance(ann.get("phenomenon_tags"), str):
        tags_selected = {t for t in ann["phenomenon_tags"].split("|") if t}

    def val(key: str, default: str = "") -> str:
        v = ann.get(key)
        if v is None:
            return default
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, list):
            return "|".join(str(x) for x in v)
        return str(v)

    def bool_select(name: str) -> str:
        cur = ann.get(name)
        opts = [("", "unset"), ("true", "true"), ("false", "false")]
        parts = [f'<select name="{name}">']
        for ov, lab in opts:
            sel = ""
            if cur is None and ov == "":
                sel = " selected"
            elif cur is True and ov == "true":
                sel = " selected"
            elif cur is False and ov == "false":
                sel = " selected"
            parts.append(f'<option value="{html.escape(ov)}"{sel}>{lab}</option>')
        parts.append("</select>")
        return "".join(parts)

    tag_boxes = []
    for t in PHENOMENON_OPTIONS:
        chk = " checked" if t in tags_selected else ""
        tag_boxes.append(
            f'<label class="tag"><input type="checkbox" name="phenomenon_tags" value="{html.escape(t)}"{chk}/> {html.escape(t)}</label>'
        )

    hide = getattr(state, "hide_tokenizer_hints", False)
    auto = ", ".join(src.get("automatic_tags") or []) if not hide else ""
    bpe = " ".join(src.get("bpe_tokens") or []) if not hide else ""
    uni = " ".join(src.get("unigram_tokens") or []) if not hide else ""
    hints_block = ""
    if not hide and (bpe or uni or auto):
        hints_block = (
            f'<p class="meta"><b>BPE:</b> {html.escape(bpe)}<br/>'
            f"<b>Unigram:</b> {html.escape(uni)}<br/>"
            f"<b>auto tags (hints only):</b> {html.escape(auto)}</p>"
        )
    else:
        hints_block = (
            '<p class="meta"><b>Tokenizer hints:</b> hidden '
            "(independent annotation mode).</p>"
        )

    msg_html = f'<p class="msg">{html.escape(message)}</p>' if message else ""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Morphology annotation — {html.escape(state.annotator_id)}</title>
<style>
 body {{ font-family: system-ui, sans-serif; max-width: 920px; margin: 1rem auto; padding: 0 1rem; }}
 .meta {{ color: #444; font-size: 0.95rem; }}
 .box {{ border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin: 1rem 0; }}
 .surface {{ font-size: 1.6rem; font-weight: 600; }}
 label.tag {{ display: inline-block; margin: 0.2rem 0.4rem 0.2rem 0; font-size: 0.9rem; }}
 input[type=text], textarea {{ width: 100%; box-sizing: border-box; }}
 .row {{ margin: 0.5rem 0; }}
 .nav a, .nav button {{ margin-right: 0.5rem; }}
 .msg {{ background: #eef8ee; padding: 0.5rem 0.75rem; border-radius: 6px; }}
 .warn {{ background: #fff6e5; padding: 0.5rem; border-radius: 6px; font-size: 0.9rem; }}
</style></head><body>
<h1>Morphology annotation (offline)</h1>
<p class="meta">Annotator: <b>{html.escape(state.annotator_id)}</b> ·
Item {index+1}/{n} · Saved {done}/{total} ·
Save: <code>{html.escape(str(state.save_path))}</code></p>
{msg_html}
<p class="warn">Do not force morphology on names/foreign forms. Locked holdout and LM test are never loaded.
Guidelines: docs/research/MORPHOLOGY_ANNOTATION_GUIDELINES_v0_1.md</p>
<div class="box">
  <div class="surface">{html.escape(str(src.get("surface_form") or ""))}</div>
  <p><b>item_id:</b> {html.escape(iid)} · <b>source:</b> {html.escape(str(src.get("source") or ""))}</p>
  <p><b>context:</b> {html.escape(str(src.get("context") or ""))}</p>
  {hints_block}
</div>
<form method="POST" action="/save">
  <input type="hidden" name="item_id" value="{html.escape(iid)}"/>
  <input type="hidden" name="index" value="{index}"/>
  <div class="row"><label>proposed_segmentation (use + between segments)</label>
    <input type="text" name="proposed_segmentation" value="{html.escape(val("proposed_segmentation"))}"/></div>
  <div class="row"><label>alternative_segmentation</label>
    <input type="text" name="alternative_segmentation" value="{html.escape(val("alternative_segmentation"))}"/></div>
  <div class="row"><label>boundary_positions (optional, comma-separated)</label>
    <input type="text" name="boundary_positions" value="{html.escape(val("boundary_positions"))}"/></div>
  <div class="row"><label>phenomenon_tags</label><div>{"".join(tag_boxes)}</div></div>
  <div class="row">no_segmentation_required {bool_select("no_segmentation_required")}</div>
  <div class="row">mixed_language {bool_select("mixed_language")}</div>
  <div class="row">spelling_or_ocr_issue {bool_select("spelling_or_ocr_issue")}</div>
  <div class="row">insufficient_context {bool_select("insufficient_context")}</div>
  <div class="row">uncertain {bool_select("uncertain")}</div>
  <div class="row"><label>confidence (1–5)</label>
    <input type="text" name="confidence" value="{html.escape(val("confidence"))}"/></div>
  <div class="row"><label>notes</label>
    <textarea name="notes" rows="3">{html.escape(val("notes"))}</textarea></div>
  <div class="nav">
    <button type="submit" name="action" value="save">Save</button>
    <button type="submit" name="action" value="save_next">Save &amp; next</button>
    <a href="/?i={max(0, index-1)}">Previous</a>
    <a href="/?i={min(n-1, index+1)}">Next (no save)</a>
    <a href="/export">Force export CSV</a>
  </div>
</form>
<p class="meta">{html.escape(TOOL_NAME)} {html.escape(TOOL_VERSION)} · local only</p>
</body></html>"""


def make_handler(state: AnnotationState):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/export":
                with state.lock:
                    rows = [
                        state.annotations[i]
                        for i in state.order
                        if i in state.annotations
                    ]
                    export_csv(state.export_csv_path, rows)
                body = page(state, 0, message=f"Exported CSV → {state.export_csv_path}")
                self._html(body)
                return
            if parsed.path not in ("/", "/index"):
                self.send_error(404)
                return
            qs = parse_qs(parsed.query)
            i = int(qs.get("i", ["0"])[0] or 0)
            self._html(page(state, i))

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/save":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            qs = parse_qs(raw, keep_blank_values=True)
            item_id = qs.get("item_id", [""])[0]
            index = int(qs.get("index", ["0"])[0] or 0)
            action = qs.get("action", ["save"])[0]
            tags = qs.get("phenomenon_tags", [])
            fields = {
                "proposed_segmentation": qs.get("proposed_segmentation", [""])[0].strip(),
                "alternative_segmentation": qs.get("alternative_segmentation", [""])[0].strip(),
                "boundary_positions": qs.get("boundary_positions", [""])[0].strip(),
                "phenomenon_tags": tags,
                "no_segmentation_required": bool_from_form(qs, "no_segmentation_required"),
                "mixed_language": bool_from_form(qs, "mixed_language"),
                "spelling_or_ocr_issue": bool_from_form(qs, "spelling_or_ocr_issue"),
                "insufficient_context": bool_from_form(qs, "insufficient_context"),
                "uncertain": bool_from_form(qs, "uncertain"),
                "confidence": qs.get("confidence", [""])[0].strip() or None,
                "notes": qs.get("notes", [""])[0],
            }
            try:
                state.save_item(item_id, fields)
                msg = f"Saved {item_id}"
            except Exception as e:  # noqa: BLE001
                msg = f"Save failed: {e}"
                self._html(page(state, index, message=msg))
                return
            if action == "save_next":
                index = min(index + 1, len(state.order) - 1)
            self._html(page(state, index, message=msg))

        def _html(self, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Offline morphology annotation UI")
    p.add_argument(
        "--items",
        type=Path,
        default=Path("data/research/morphology_benchmark_v0.1/development/pilot_40.jsonl"),
    )
    p.add_argument("--annotator-id", type=str, required=True)
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("--save", type=Path, default=None, help="Annotation JSONL path")
    p.add_argument("--export-csv", type=Path, default=None)
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument(
        "--hide-tokenizer-hints",
        action="store_true",
        help="Do not display BPE/Unigram or automatic tags (required for remaining 160).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve() if args.repo_root else Path.cwd()
    items_path = args.items if args.items.is_absolute() else root / args.items
    refuse_locked(items_path)
    items = load_jsonl(items_path)
    for it in items:
        iid = str(it.get("item_id") or "")
        if iid.startswith("morph_hold_"):
            raise SystemExit("Holdout items must not be loaded into the annotation UI")
    if args.hide_tokenizer_hints:
        # strip any tokenizer/auto fields from in-memory items so UI cannot show them
        stripped = []
        for it in items:
            stripped.append(
                {
                    "item_id": it.get("item_id"),
                    "surface_form": it.get("surface_form"),
                    "context": it.get("context") or "",
                    "source": it.get("source") or "",
                    "split": it.get("split"),
                    "line_ref": it.get("line_ref"),
                }
            )
        items = stripped

    save = args.save
    if save is None:
        save = (
            root
            / "data/research/morphology_benchmark_v0.1/development/annotations"
            / f"{args.annotator_id}_annotations.jsonl"
        )
    elif not save.is_absolute():
        save = root / save
    refuse_locked(save)

    export_csv_path = args.export_csv
    if export_csv_path is None:
        export_csv_path = save.with_suffix(".csv")
    elif not export_csv_path.is_absolute():
        export_csv_path = root / export_csv_path

    state = AnnotationState(
        items,
        annotator_id=args.annotator_id,
        save_path=save,
        export_csv_path=export_csv_path,
    )
    state.hide_tokenizer_hints = bool(args.hide_tokenizer_hints)
    handler = make_handler(state)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(
        f"Annotation UI for {args.annotator_id} at http://{args.host}:{args.port}/ "
        f"({len(items)} items)\nSave → {save}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
