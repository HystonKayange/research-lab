# Public reproducibility guide v0.2

This guide rebuilds presentation artifacts from existing development/validation
reports. It does not authorize new tokenizer evaluations, training, holdout access,
LM-test access, weight selection, ablations, or a successor method.

## What a public checkout can reproduce

- The v0.2 publication snapshot, three figures, and seven-page working paper.
- The sample flow and content hash of the frozen 162-item development benchmark.
- Descriptive counts from the candidates already stored in the oracle JSON.
- The recorded primary/secondary LM results and success-criterion outcomes.

The commands below use stored scores rather than recomputing scientific metrics.
They neither run a tokenizer nor choose a new candidate. Candidate-union counts
are descriptive set operations on stored pieces; they do not change the oracle.

## Build in a separate environment

Python 3.12 and the DejaVu font family are used for the presentation build. On
Debian/Ubuntu the font package is `fonts-dejavu-core`. The recorded document-build
dependencies are separate from the historical training environment.

```sh
python3 -m venv .venv-publication
.venv-publication/bin/python -m pip install -r requirements-publication.txt
.venv-publication/bin/python scripts/publication/build_publication_snapshot.py
.venv-publication/bin/python scripts/publication/build_paper_pdf.py
```

Outputs:

- `data/reports/publication_snapshot_v0_2.json`
- `data/reports/figures/paper_v0_2/f1_candidate_availability.{png,svg}`
- `data/reports/figures/paper_v0_2/f2_oracle_changes.{png,svg}`
- `data/reports/figures/paper_v0_2/f3_primary_lm.{png,svg}`
- `docs/research/papers/unigram_undersegments_chichewa_v0_2.pdf`

The PDF is built from the corresponding Markdown file, not a second hard-coded
copy. ReportLab's invariant mode fixes generated timestamps; SVG IDs are seeded.
Exact output bytes can still depend on the recorded library versions and fonts.

## Input boundaries and content integrity

The snapshot generator has a fixed input allowlist: Phase-C results, Phase-F
results, the stored oracle, the failure diagnostic, final adjudication report,
canonical 200 and active 195 annotations, and the frozen active v0.2 annotations.
Every input is hashed before and after the build. The expected active benchmark
hash is:

```text
73b948d782b6e979814de051ffad315ca282cbff5fc7f8c5de15b0c864852f67
```

Do not regenerate historical Phase-C, Phase-F, oracle, annotation-quality, policy,
or freeze-manifest files merely to update their dates or Git IDs. Historical
exact self-agreement 0.52 and boundary F1 0.841 remain original-protocol evidence,
not estimates of agreement under the final rubric.

## Interpretation checks in this revision

1. Sample flow is 200 → five earlier exclusions → 195 → 33 Level-B exclusions → 162.
2. Reported macro metrics omit undefined values separately for each metric.
   Unigram P/R/F1 counts are 152/160/150; F1-oracle counts are 162/160/160.
3. The selected oracle still misses 2/71/41 left/right/internal gold offsets.
   Candidate-union absence is instead 0/27/22. Those quantities answer different
   questions; union coverage does not imply one jointly correct segmentation.
4. 125 paths change, but only 115 show a strict improvement in defined baseline
   F1; ten baseline F1 values are undefined.
5. Empty normalized-piece warnings in the original Phase-C record are disclosed:
   one BPE item and three Unigram items. The frozen scorer is preserved.
6. Zero development changes do not imply identical text encoding everywhere.
   The recorded whitespace-path difference is disclosed for TPC interpretation.

## What requires more than this checkout

Full training/evaluation reproducibility is narrower than presentation
reproducibility. Model checkpoints and the large regenerable boundary-statistics
table are not public tracked files. Original source archives were not retained;
the moving Wikipedia download URL does not establish an immutable original dump.
Consult frozen configuration/provenance records before making a fresh experimental
reproduction plan. This guide does not run those historical entrypoints.

The eight removed private artifacts and an original-history bundle remain in the
owner's private local storage. They are not prerequisites for the presentation
build. Do not ask another contributor to publish them to make the build succeed.

## Git history and prior public exposure

The owner-approved rewrite changed commit IDs while preserving retained scientific
file bytes. Use `data/reports/public_history_rewrite_2026_11_10.json` to resolve old
IDs recorded inside historical reports. The local freeze tag was remapped; it was
not published as a new public tag.

Protected artifacts were previously public. Existing clones/downloads/caches may
retain them. “Locked” means the research protocol has not authorized their use in
this revision; it does not mean the text is historically secret or an unseen test
set has been restored. Future confirmatory plans must account for this limitation.

## Publication and licensing decisions

The report is a working draft requiring author approval. Original software code
is available under the [scoped MIT license](../../LICENSE). See
[DATA_AND_LICENSES.md](../../DATA_AND_LICENSES.md) and the source-specific
attribution records before redistributing text, annotations, or trained artifacts.
