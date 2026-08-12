# Holdout stage-2 validation

**Status:** complete  
**Records:** 40/40 labeled (all `boilerplate_or_noise` — categories, blanks, digits)

## Stage 2 only

| metric | value | 95% Wilson CI |
|--------|------:|---------------|
| removal precision | 100% | [91.2%, 100%] |
| false-removal rate | 0% | [0%, 8.8%] |
| useful-text retention | n/a | no useful labels in this chunk |

## Combined stage 1 + 2 (n=120)

| metric | value | 95% Wilson CI | target | CI stop rule |
|--------|------:|---------------|--------|--------------|
| removal precision | 98.8% | [93.3%, 99.8%] | ≥90% | pass (low≥80%) |
| false-removal rate | 1.25% | [0.2%, 6.7%] | ≤10% | pass (high≤20%) |
| useful-text retention | 95.5% | [78.2%, 99.2%] | ≥90% | **fail** (low 78.2% < 80%) |

**Stopping recommendation:** `release_next_chunk` — useful-retention CI still wide (only 22 useful labels total from stage 1; stage 2 added no kept lines).

Stage 2 was almost all obvious Category/blank/digit removals (no kept-sample stress test).
