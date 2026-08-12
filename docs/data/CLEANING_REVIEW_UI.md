# Cleaning review UI

Local human-annotation tool for Wikipedia cleaning review samples.

**Purpose:** let a native Chichewa speaker label review records safely without hand-editing JSONL.

## Dataset roles

| Set | File | Role |
|-----|------|------|
| Development validation | `data/reports/cleaning_review_sample.jsonl` | Original ~367 records used to analyze v1 and design v2. **Not** independent final validation. |
| Blind holdout | `data/reports/cleaning_holdout_sample.jsonl` | Fresh ~250 records with **no overlap** with the development set. Label these for generalization estimates. |

Default UI path points at the development sample; pass `--sample data/reports/cleaning_holdout_sample.jsonl` for holdout annotation (schema uses `v2_decision` / `v2_rule_id` — extend UI if needed, or edit JSONL carefully).

**Does not:** auto-label, call APIs, modify raw/interim corpora, change cleaning rules, promote to `data/processed/`, create splits, or train models.

---

## Start the tool

From the repository root:

```bash
python scripts/data/run_cleaning_review.py \
  --sample data/reports/cleaning_review_sample.jsonl \
  --host 127.0.0.1 \
  --port 8765
```

Open in a browser:

```text
http://127.0.0.1:8765
```

Options:

| Flag | Default | Meaning |
|------|---------|---------|
| `--sample` | `data/reports/cleaning_review_sample.jsonl` | Review JSONL path |
| `--backup-dir` | `data/reports/cleaning_review_backups/` | Timestamped backups |
| `--host` | `127.0.0.1` | Bind address (local only by default) |
| `--port` | `8765` | Port |
| `--autosave-every` | `10` | Checkpoint save after N edits |

Stop with **Ctrl+C**. If there are unsaved changes, the tool attempts a final save.

---

## How to label

1. Read the **decision** (`removed` / `kept`), **rule**, and **excerpt**.
2. Choose a label with a button or number key (`1`–`6`).
3. Optionally type **notes**, then **Apply notes** (or include notes when choosing a label — the UI sends the notes box with each label click).
4. Use **Next / Prev** to move. Change a prior label anytime.
5. Press **S** or **Save** periodically.

On startup the tool resumes at the **first unlabeled** record. Existing labels are never erased on load.

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `1` | `valid_chichewa` |
| `2` | `useful_mixed_chichewa` |
| `3` | `boilerplate_or_noise` |
| `4` | `foreign_language` |
| `5` | `duplicate` |
| `6` | `uncertain` |
| `←` | Previous (filtered view) |
| `→` | Next (filtered view) |
| `S` | Save checkpoint |
| `U` | Toggle “unlabeled only” filter |

When focus is in the notes box, shortcuts are disabled so typing works; press Escape to blur.

---

## Label definitions

| Label | Meaning |
|-------|---------|
| `valid_chichewa` | Usable Chichewa content |
| `useful_mixed_chichewa` | Mostly Chichewa; minor noise/foreign still useful |
| `boilerplate_or_noise` | Nav, chrome, stubs, garbage |
| `foreign_language` | Predominantly non-Chichewa |
| `duplicate` | Non-informative duplicate |
| `uncertain` | Cannot decide confidently |

### Metric mapping (after summarizer)

**Removed**

- False removal: `valid_chichewa` or `useful_mixed_chichewa`
- Correct removal: `boilerplate_or_noise`, `foreign_language`, or `duplicate`
- `uncertain` excluded from precision by default

**Kept**

- Useful text: `valid_chichewa` or `useful_mixed_chichewa`
- Noise: `boilerplate_or_noise` or `duplicate`
- Foreign leakage: `foreign_language`
- Boilerplate leakage: `boilerplate_or_noise`

---

## Filters and navigation

- **Unlabeled only** — focus remaining work
- **Decision** — `removed` / `kept` / all
- **Rule** — filter removals by `rule_id`
- **Jump** — go to filtered position number (1-based)

Header shows totals: labeled, unlabeled, uncertain.

---

## Saving and backups

**Mutable fields only:** `review_label`, `review_notes`.

Immutable fields (`review_id`, `source_id`, `original_line_number`, `decision`, `rule_id`, `excerpt`, `text_sha256`, plus protected metadata) are snapshotted on load and re-checked on every save.

Save procedure:

1. Validate all records and immutable snapshot.
2. Write a temporary file in the same directory.
3. Re-read and re-validate the temp file.
4. Copy the previous sample to  
   `data/reports/cleaning_review_backups/cleaning_review_sample.<UTC-timestamp>.jsonl`  
   (on explicit save / checkpoint — not every single click).
5. Atomically replace the sample file.

A failed save **does not** truncate or replace the existing JSONL.

**Autosave:** after every N edits (`--autosave-every`, default 10), a checkpoint save runs if dirty.

The UI shows:

- unsaved vs saved
- last successful save time
- save errors
- completion when unlabeled count is 0

---

## Resume

Restart the same command anytime. Labels already on disk are loaded. Default cursor is the first unlabeled record.

---

## After all 367 labels

When complete, the UI shows label distribution and this command (it does **not** run it automatically):

```bash
python scripts/data/summarize_cleaning_review.py \
  --config configs/data/cleaning_review.json \
  --sample data/reports/cleaning_review_sample.jsonl
```

That updates:

- `data/metadata/cleaning_validation.json`
- `data/reports/cleaning_validation_report.md`

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Port in use | Choose another `--port` |
| Sample missing | Rebuild with `build_cleaning_review_sample.py` (do not invent labels) |
| Invalid label on load | Fix only `review_label` / `review_notes` in a backup; do not alter hashes |
| Lost work | Check `data/reports/cleaning_review_backups/` |
| Save error | Read UI error text; prior file should still be intact |
| Wrong file edited | Confirm `--sample` path before starting |

---

## Safety notes

- Bind to `127.0.0.1` for local-only review.
- Do not commit secrets; this tool stores only labels/notes.
- Do not edit `data/raw/` or interim cleaned corpora through this UI (it only opens the review JSONL).
