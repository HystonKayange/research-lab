# Training eligibility review

**Status:** pending human review  
**Generated:** 2026-08-04T03:35:32.782579Z  
**Note:** This checklist is an aid only. No automated licensing decision was made.

## Decision table

| Source | Provenance known | License known | Allowed for training | Holdout only | Decision | Evidence needed |
| ------ | ---------------: | ------------: | -------------------: | -----------: | -------- | --------------- |
| bible | unknown | unknown | not yet verified | not yet verified | pending human review | Origin URL/dump date; license text; redistribution + training rights; attribution rules |
| existing_corpus | unknown | unknown | not yet verified | not yet verified | pending human review | Origin URL/dump date; license text; redistribution + training rights; attribution rules |
| wikipedia | unknown | unknown | not yet verified | not yet verified | pending human review | Origin URL/dump date; license text; redistribution + training rights; attribution rules |

## Reviewer checklist (per source)

- [ ] Confirm source origin
- [ ] Confirm license or permission
- [ ] Confirm redistribution rights
- [ ] Confirm training rights
- [ ] Confirm whether attribution is required
- [ ] Confirm whether derived datasets may be published
- [ ] Record decision in `data/metadata/sources.jsonl` (`allowed_for_training`, `holdout_only`, `license`, `source_url`)

## Guidance

Do not set `allowed_for_training` to true without documented rights. When uncertain, prefer holdout or exclude. Audit statistics do not substitute for legal review.

