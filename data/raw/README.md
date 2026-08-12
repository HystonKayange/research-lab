# Raw data — immutable

Files under `data/raw/` are **immutable source material**.

## Rules

1. **Never edit** files in this directory (or its subdirectories).
2. **Never write** cleaned, normalized, tokenized, or otherwise processed output here.
3. **Never overwrite** a raw file in place. If a better source arrives, add a new versioned path and document it in `data/metadata/sources.jsonl`.
4. All transformations belong under `data/interim/`, `data/processed/`, or `data/splits/`.
5. Before any pipeline step, verify integrity with SHA-256 checksums (see `data/metadata/inventory.json` and `scripts/data/build_inventory.py`).

Treating raw data as read-only is required for reproducible Chichewa LM and tokenizer experiments.
