# Cleaning holdout validation report

**Status:** `pending_human_labels`  
**Records:** 250  

This set is a **blind holdout**. The original 367-record review is the **development validation set** only.

Label `data/reports/cleaning_holdout_sample.jsonl`, then run:

```bash
python3 scripts/data/summarize_cleaning_holdout.py \
  --config configs/data/cleaning_holdout.json \
  --sample data/reports/cleaning_holdout_sample.jsonl
```
