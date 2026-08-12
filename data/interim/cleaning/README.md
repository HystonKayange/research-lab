# Interim cleaning outputs

These files are **intermediate** cleaning artifacts.

## Status

- Generated from immutable `data/raw/` sources
- **Not** final `data/processed/` training corpora
- **Not** approved for training (license/eligibility unresolved)
- Safe to delete and regenerate from config + raw

Tool: `clean_sources` v1.0.0
Generated: 2026-08-04T04:05:42.596146Z

Each source subdirectory contains:

- `cleaned.txt` — lines kept after configured rules
- `removal_log.jsonl` — one record per removed line (rule id + excerpt)
- `transform_log.jsonl` — content-changing transforms on kept lines

Do not edit files under `data/raw/`.
