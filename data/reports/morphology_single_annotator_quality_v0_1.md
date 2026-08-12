# Morphology single-annotator quality v0.1

_Generated 2026-08-06T06:10:22.699323Z_

## Research framing

- Development benchmark: **single native-speaker annotation** (`annotator_a`)
- Annotator count: **1**
- Human–AI pilot (chat / Claude assist): **exploratory only**, not gold
- **No human–human IAA claim** in this phase
- Morphology holdout: **locked**
- Stronger multi-annotator validation: **future work**

## Self-consistency review

- Blinded re-annotation set: **25** items (`self_review_25_blinded.jsonl`)
- Status: **awaiting pass-2 re-annotation**
- Comparison **not run** (pass-2 file missing or empty)

After Annotator A completes pass-2, re-run:

```bash
.venv/bin/python scripts/tokenizers/measure_annotation_self_consistency.py
```
