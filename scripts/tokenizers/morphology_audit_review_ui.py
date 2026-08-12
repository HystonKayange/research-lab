#!/usr/bin/env python3
"""Human-only re-review UI for the 20 audit-flagged morphology items.

Decisions: KEEP | REVISE | WHOLE | EXCLUDE | UNCERTAIN

- Never loads BPE/Unigram, holdout, or LM test
- Never modifies annotator_a_full_200.jsonl
- Saves decisions incrementally to a separate decisions JSONL

Usage:
  python scripts/tokenizers/morphology_audit_review_ui.py --port 8766

  Open http://127.0.0.1:8766/
"""

from __future__ import annotations

import argparse
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

TOOL_NAME = "morphology_audit_review_ui"
TOOL_VERSION = "0.1.0"

DECISIONS = ("KEEP", "REVISE", "WHOLE", "EXCLUDE", "UNCERTAIN")
NOTE_REQUIRED = {"REVISE", "EXCLUDE", "UNCERTAIN"}


def refuse_forbidden(path: Path | str) -> None:
    s = str(path).replace("\\", "/")
    if "/locked/" in s and "/released/" not in s:
        raise RuntimeError(f"refusing locked holdout path: {path}")
    if "/test/" in s:
        raise RuntimeError(f"refusing test path: {path}")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_decisions(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(path):
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
        for iid, row in sorted(rows_by_id.items()):
            if iid not in order:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def reconstructs(surface: str, seg: str) -> bool:
    return seg.replace("+", "") == surface


class ReviewState:
    def __init__(
        self,
        items: list[dict[str, Any]],
        *,
        annotator_id: str,
        decisions_path: Path,
    ) -> None:
        self.items = items
        self.order = [str(r["item_id"]) for r in items]
        self.by_id = {str(r["item_id"]): r for r in items}
        self.annotator_id = annotator_id
        self.decisions_path = decisions_path
        self.decisions = load_decisions(decisions_path)
        self.lock = threading.Lock()
        for row in self.decisions.values():
            aid = row.get("annotator_id")
            if aid and aid != annotator_id:
                raise SystemExit(
                    f"Decisions file {decisions_path} has annotator_id={aid}, "
                    f"expected {annotator_id}"
                )

    def progress(self) -> tuple[int, int]:
        done = sum(1 for i in self.order if i in self.decisions)
        return done, len(self.order)

    def save_decision(self, item_id: str, fields: dict[str, Any]) -> None:
        with self.lock:
            if item_id not in self.by_id:
                raise KeyError(item_id)
            src = self.by_id[item_id]
            decision = str(fields["decision"]).upper()
            if decision not in DECISIONS:
                raise ValueError(f"invalid decision: {decision}")
            note = (fields.get("note") or "").strip()
            if decision in NOTE_REQUIRED and not note:
                raise ValueError(f"short human note required for {decision}")

            revised = (fields.get("revised_segmentation") or "").strip()
            surface = str(src.get("surface_form") or "")

            if decision == "KEEP":
                final_seg = src.get("current_proposed_segmentation")
            elif decision == "WHOLE":
                final_seg = surface
            elif decision == "EXCLUDE":
                final_seg = surface  # stored as whole surface; apply script marks exclude
            elif decision == "UNCERTAIN":
                final_seg = revised or src.get("current_proposed_segmentation")
            elif decision == "REVISE":
                if not revised:
                    raise ValueError("REVISE requires revised_segmentation")
                if not reconstructs(surface, revised):
                    raise ValueError(
                        f"revised segmentation does not reconstruct surface: "
                        f"{revised!r} → {revised.replace('+','')!r} vs {surface!r}"
                    )
                final_seg = revised
            else:
                raise ValueError(decision)

            rec = {
                "item_id": item_id,
                "surface_form": surface,
                "source": src.get("source"),
                "context": src.get("context"),
                "original_proposed_segmentation": src.get("current_proposed_segmentation"),
                "original_alternative_segmentation": src.get(
                    "current_alternative_segmentation"
                ),
                "original_uncertain": src.get("uncertain"),
                "original_confidence": src.get("confidence"),
                "audit_priority": src.get("audit_priority"),
                "audit_categories": src.get("audit_categories"),
                "audit_reasons": src.get("audit_reasons"),
                "decision": decision,
                "revised_segmentation": revised or None,
                "final_segmentation": final_seg,
                "note": note or None,
                "annotator_id": self.annotator_id,
                "applied_to_full_200": False,
                "updated_at": utc_now_iso(),
                "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            }
            self.decisions[item_id] = rec
            atomic_write_jsonl(self.decisions_path, self.decisions, self.order)


def page(state: ReviewState, index: int, message: str = "", error: bool = False) -> str:
    n = len(state.order)
    index = max(0, min(index, n - 1))
    iid = state.order[index]
    src = state.by_id[iid]
    dec = state.decisions.get(iid) or {}
    done, total = state.progress()

    cur_dec = str(dec.get("decision") or "")
    note_val = str(dec.get("note") or "")
    rev_val = str(dec.get("revised_segmentation") or "")

    reasons = src.get("audit_reasons") or []
    cats = src.get("audit_categories") or []
    reasons_html = (
        "<ul>" + "".join(f"<li>{html.escape(str(r))}</li>" for r in reasons) + "</ul>"
        if reasons
        else "<p><i>none</i></p>"
    )
    cats_html = ", ".join(html.escape(str(c)) for c in cats) or "—"

    radios = []
    for d in DECISIONS:
        chk = " checked" if cur_dec == d else ""
        radios.append(
            f'<label class="dec"><input type="radio" name="decision" value="{d}"{chk} required/> '
            f"<b>{d}</b></label>"
        )

    msg_cls = "err" if error else "msg"
    msg_html = f'<p class="{msg_cls}">{html.escape(message)}</p>' if message else ""

    pending_ids = [i for i in state.order if i not in state.decisions]
    pending_note = (
        f"Pending: {', '.join(pending_ids[:8])}"
        + ("…" if len(pending_ids) > 8 else "")
        if pending_ids
        else "All 20 decisions saved."
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Morphology audit re-review — {html.escape(state.annotator_id)}</title>
<style>
 body {{ font-family: system-ui, sans-serif; max-width: 920px; margin: 1rem auto; padding: 0 1rem; }}
 .meta {{ color: #444; font-size: 0.95rem; }}
 .box {{ border: 1px solid #ccc; border-radius: 8px; padding: 1rem; margin: 1rem 0; }}
 .surface {{ font-size: 1.7rem; font-weight: 650; }}
 .seg {{ font-family: ui-monospace, monospace; background: #f4f6f8; padding: 0.35rem 0.5rem; border-radius: 4px; }}
 label.dec {{ display: block; margin: 0.35rem 0; }}
 input[type=text], textarea {{ width: 100%; box-sizing: border-box; font-size: 1rem; }}
 .row {{ margin: 0.65rem 0; }}
 .nav a, .nav button {{ margin-right: 0.5rem; }}
 .msg {{ background: #eef8ee; padding: 0.5rem 0.75rem; border-radius: 6px; }}
 .err {{ background: #fdeeee; padding: 0.5rem 0.75rem; border-radius: 6px; }}
 .warn {{ background: #fff6e5; padding: 0.6rem 0.75rem; border-radius: 6px; font-size: 0.92rem; }}
 .flags span {{ display: inline-block; background: #eef; margin: 0.15rem 0.25rem 0 0; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.85rem; }}
</style></head><body>
<h1>Audit re-review (human only)</h1>
<p class="meta">Annotator: <b>{html.escape(state.annotator_id)}</b> ·
Item <b>{index+1}/{n}</b> · Decisions saved <b>{done}/{total}</b><br/>
Decisions file: <code>{html.escape(str(state.decisions_path))}</code><br/>
{html.escape(pending_note)}</p>
{msg_html}
<p class="warn">
<strong>Does not modify</strong> <code>annotator_a_full_200.jsonl</code>.
No BPE/Unigram/Claude hints. No holdout. No LM test.
REVISE / EXCLUDE / UNCERTAIN require a short note.
Apply later with <code>apply_morphology_human_review.py</code> only after 20/20.
</p>
<div class="box">
  <div class="surface">{html.escape(str(src.get("surface_form") or ""))}</div>
  <p><b>item_id:</b> {html.escape(iid)} · <b>source:</b> {html.escape(str(src.get("source") or ""))}
  · <b>audit priority:</b> {html.escape(str(src.get("audit_priority")))}</p>
  <p><b>context:</b> {html.escape(str(src.get("context") or ""))}</p>
  <p><b>current segmentation:</b> <span class="seg">{html.escape(str(src.get("current_proposed_segmentation") or ""))}</span></p>
  <p><b>current alternative:</b> <span class="seg">{html.escape(str(src.get("current_alternative_segmentation") or "—"))}</span></p>
  <p class="flags">
    <span>uncertain={html.escape(str(src.get("uncertain")))}</span>
    <span>confidence={html.escape(str(src.get("confidence")))}</span>
    <span>no_seg={html.escape(str(src.get("no_segmentation_required")))}</span>
    <span>mixed={html.escape(str(src.get("mixed_language")))}</span>
    <span>ocr={html.escape(str(src.get("spelling_or_ocr_issue")))}</span>
    <span>insuff_ctx={html.escape(str(src.get("insufficient_context")))}</span>
  </p>
  <p><b>audit categories:</b> {cats_html}</p>
  <p><b>audit reasons:</b></p>
  {reasons_html}
</div>
<form method="POST" action="/save">
  <input type="hidden" name="item_id" value="{html.escape(iid)}"/>
  <input type="hidden" name="index" value="{index}"/>
  <div class="row"><b>Decision</b>{"".join(radios)}</div>
  <div class="row"><label>revised_segmentation (required for REVISE; optional for UNCERTAIN if keeping form)</label>
    <input type="text" name="revised_segmentation" value="{html.escape(rev_val)}"
      placeholder="e.g. si+zi+dza+mveka+nso"/></div>
  <div class="row"><label>note (required for REVISE, EXCLUDE, UNCERTAIN)</label>
    <textarea name="note" rows="3" placeholder="Short human rationale">{html.escape(note_val)}</textarea></div>
  <div class="nav">
    <button type="submit" name="action" value="save">Save decision</button>
    <button type="submit" name="action" value="save_next">Save &amp; next</button>
    <a href="/?i={max(0, index-1)}">Previous</a>
    <a href="/?i={min(n-1, index+1)}">Next (no save)</a>
    <a href="/status">Status JSON</a>
  </div>
</form>
<p class="meta">{html.escape(TOOL_NAME)} {html.escape(TOOL_VERSION)} · local only · full-200 immutable</p>
</body></html>"""


def make_handler(state: ReviewState):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/status":
                done, total = state.progress()
                payload = {
                    "done": done,
                    "total": total,
                    "complete": done == total,
                    "decisions_path": str(state.decisions_path),
                    "item_ids_done": sorted(state.decisions.keys()),
                    "item_ids_pending": [i for i in state.order if i not in state.decisions],
                    "full_200_modified": False,
                }
                data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
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
            fields = {
                "decision": qs.get("decision", [""])[0].strip(),
                "revised_segmentation": qs.get("revised_segmentation", [""])[0],
                "note": qs.get("note", [""])[0],
            }
            try:
                state.save_decision(item_id, fields)
                msg = f"Saved decision for {item_id}: {fields['decision'].upper()}"
                err = False
            except Exception as e:  # noqa: BLE001
                msg = f"Save failed: {e}"
                err = True
                self._html(page(state, index, message=msg, error=True))
                return
            if action == "save_next" and not err:
                index = min(index + 1, len(state.order) - 1)
            self._html(page(state, index, message=msg, error=err))

        def _html(self, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Human audit re-review UI (20 items)")
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--queue",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/review/"
            "annotator_a_audit_review_20.jsonl"
        ),
    )
    p.add_argument(
        "--decisions",
        type=Path,
        default=Path(
            "data/research/morphology_benchmark_v0.1/development/review/"
            "annotator_a_audit_review_20_decisions.jsonl"
        ),
    )
    p.add_argument("--annotator-id", type=str, default="annotator_a")
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=8766)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    root = (args.repo_root or Path(__file__).resolve().parents[2]).resolve()
    queue_path = (root / args.queue).resolve() if not args.queue.is_absolute() else args.queue
    dec_path = (
        (root / args.decisions).resolve() if not args.decisions.is_absolute() else args.decisions
    )
    refuse_forbidden(queue_path)
    refuse_forbidden(dec_path)

    items = load_jsonl(queue_path)
    if not items:
        raise SystemExit(f"empty or missing queue: {queue_path}")
    # strip any accidental tokenizer fields
    cleaned = []
    for row in items:
        cleaned.append(
            {
                k: v
                for k, v in row.items()
                if not any(x in k.lower() for x in ("bpe", "unigram", "claude", "tokenizer"))
            }
        )
    state = ReviewState(cleaned, annotator_id=args.annotator_id, decisions_path=dec_path)
    dec_path.parent.mkdir(parents=True, exist_ok=True)
    if not dec_path.exists():
        dec_path.write_text("", encoding="utf-8")

    handler = make_handler(state)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(
        f"{TOOL_NAME} {TOOL_VERSION} · http://{args.host}:{args.port}/ · "
        f"queue={len(state.order)} · decisions→{dec_path}"
    )
    print("full-200 will NOT be modified by this UI")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
        server.server_close()


if __name__ == "__main__":
    main()
