# Publication review v0.2

Scope: presentation and release-readiness improvements from existing results.
StatBound V1, λ*=0.25, gold, scoring rules, and success criteria remain frozen.
Neither locked set was opened, and no scientific experiment was rerun.

## Material corrections

| Issue in v0.1 presentation | v0.2 treatment |
|---|---|
| Sample flow jumped from 200 to 162 + 33 | States five prior exclusions, followed by 195 Level-B source items and 33 further exclusions |
| “Native-speaker adjudicated” could imply all revised labels were independently human-checked | States original native labels, 133 accepted policy revisions, and explicit native decisions on 11 exceptions; no independent reannotation of all revisions is claimed |
| “Still missing after oracle” treated as absence from n-best | Separates selected-path misses 2/71/41 from candidate-union absence 0/27/22 |
| Positional bins described as grammatical labels | Defines offsets and precedence; treats prefix/FV interpretations cautiously |
| Macro means described as averages over all 162 | Gives metric-specific defined-item counts; distinguishes paired and unpaired deltas |
| 125 changed paths described as 125 F1 improvements | Reports 115 strict defined improvements and ten undefined baseline comparisons |
| All extra-cut cases called linguistically bad | Describes mechanical non-gold cuts without inventing native-speaker judgments |
| Reconstruction success implied entirely clean scoring | Discloses one BPE and three Unigram empty-piece warnings in the original scorer |
| Max-compat failure presented as proof every calibration must fail | Restricts the claim to observed score alignment and the frozen V1 decision |
| “Test locked” could imply historical secrecy | Discloses prior public artifacts and limits of history cleanup |
| Markdown/PDF had separately maintained narratives | PDF is generated directly from the new Markdown source |

These corrections change the interpretation and documentation, not the recorded
scores. The new union counts are set operations on already stored candidate
pieces. They do not generate candidates, select a new path, or rescore a system.

## Citation checks

The revised draft includes 13 references with primary publisher/ACL links and a
portable BibTeX file. For ACL entries, bibliographic records and abstracts were
checked; this is not a claim of a new full-text systematic review. Mchombo is a
background reference, with a publisher front-matter link; the operational rules
come from the already frozen policy, not an invented new reading of that book.

The Latin reference's author is **Marisa Hudspeth**, and its full title is
*Contextual morphologically-guided tokenization for Latin encoder models*;
v0.1's author initial/title were incomplete. SentencePiece's system paper is now
separately credited. Incomplete background citations not used by the revised
argument are omitted rather than assigned guessed dates or venues.

Verified primary links are present in the draft and
`docs/research/papers/references_v0_2.bib`. Source terms for text redistribution
were separately checked against eBible, Wikimedia, and Creative Commons; see
`DATA_AND_LICENSES.md`. No blanket legal status is inferred for trained weights.

## Existing local provenance records

The previously local policy, recommendation-only re-audit, policy application,
human-review packets, blank original exception CSV, and self-review records are
archived as historical provenance without relabeling or rerunning analysis.
Native adjudications and final gold remain in their frozen v0.2 files. Earlier
recommendations remain recommendations, not a competing current gold standard.

The pre-existing completed single-annotator self-review reports retain exact
agreement 0.52 and their original unrounded boundary F1. Publishing those existing
files does not recompute the measurements or create human–human IAA. Original
annotation file bytes and all pre-existing local source-file bytes are preserved.
Loose independent research drafts and the unreviewed annotation-application helper
remain outside this publication commit.

## Release status

Presentation build and artifact consistency checks can be completed from public
reports alone. The seven-page v0.2 draft is still a **working draft**, not a
submission or an automatically issued dataset/software release.

Owner decisions that remain before a formal release:

- Select the original-code license; none is silently imposed by this review.
- Confirm annotation license/contributor permission and context redistribution.
- Approve the revised scientific claims and venue-specific assistance disclosure.
- Decide any future confirmatory protocol with awareness of prior public exposure.

The frozen scorer's empty-piece and undefined-value behavior is a disclosed
scientific limitation. A methodological correction, if desired later, needs a
separate versioned protocol and cannot retroactively replace the V1 outcomes.
