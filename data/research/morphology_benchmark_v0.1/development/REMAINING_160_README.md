# Remaining 160 — Annotator A

Single native-speaker annotator (`annotator_a`).

## Files

- Pool: `data/research/morphology_benchmark_v0.1/development/remaining_160.jsonl`
- Annotation CSV (no BPE/Unigram): `data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_remaining_160.csv`
- Progress JSONL (create/update while annotating): `data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_remaining_160_annotations.jsonl`
- Merged full 200: `data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_full_200.jsonl`

## Annotate (UI, no tokenizer hints)

```bash
.venv/bin/python scripts/tokenizers/morphology_annotation_ui.py \
  --items data/research/morphology_benchmark_v0.1/development/remaining_160.jsonl \
  --annotator-id annotator_a \
  --save data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_remaining_160_annotations.jsonl \
  --export-csv data/research/morphology_benchmark_v0.1/development/annotations/annotator_a_remaining_160_progress.csv \
  --hide-tokenizer-hints \
  --port 8765
```

Or fill the CSV and convert with merge script.

## Merge after remaining complete

```bash
.venv/bin/python scripts/tokenizers/merge_annotator_a_full_200.py
```

Pilot: pilot annotations are never overwritten.

Guidelines: `docs/research/MORPHOLOGY_ANNOTATION_GUIDELINES_v0_1.md`
