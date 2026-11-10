# Data, attribution, and license scope

## Original code and paper

No project-wide license has yet been selected for original code. The repository is
public, but should not be advertised as an open-source licensed release until the
owner makes that choice. The v0.2 paper is an unpublished working draft. Its
publication venue and final license remain undecided.

A future code license must not be represented as relicensing third-party text,
figures, libraries, annotations whose rights are unresolved, or trained artifacts.
Third-party packages retain their own licenses.

## Included text sources

The project's recorded text sources are Chichewa Wikipedia and the Chichewa Bible
translation distributed through eBible/Biblica. The source records identify both
under CC BY-SA 4.0. The official Bible page states copyright © 2002, 2016 Biblica,
Inc. and supplies license, attribution, modification, and trademark conditions.
Wikipedia contributors retain their rights in their contributions.

Source-specific notices and extraction/cleaning disclosures are retained in:

- [Source attribution](data/processed/chichewa_corpus_v0.1/reports/SOURCE_ATTRIBUTION.md)
- [Structured Bible provenance](data/metadata/source_provenance/bible.json)
- [Structured Wikipedia provenance](data/metadata/source_provenance/wikipedia.json)
- [Manual acquisition record](configs/data/source_acquisition_manifest.json)

Use those source-specific notices when redistributing applicable text. A generic
credit to this repository does not replace attribution, the applicable license
notice, or a modification notice. The corpus is not branded as a Biblica product.

Authoritative references checked for this publication review on 2026-11-10:

- [Official eBible source and conditions](https://ebible.org/details.php?id=nya)
- [Wikimedia Terms of Use, Section 7](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content)
- [CC BY-SA 4.0 deed and legal-code link](https://creativecommons.org/licenses/by-sa/4.0/)

These notices document source terms; they do not establish a new grant from this
project for material it does not own. The status of model weights and other
derived artifacts is not settled here by choosing a code license.

## Annotation and benchmark rights

Native-speaker labels and corpus-derived sentence contexts are distinct material.
The current review verifies the annotation provenance and frozen hashes, not a
separate license grant or contributor consent. Before a formal dataset release,
the owner must confirm the annotation license and permission to redistribute
labels and accompanying contexts. No new license is inferred from a blank field.

## Withheld and previously public material

The LM-test artifacts, morphology sealed payload/metadata, and tokenizer test
metrics listed in the history-cleanup record are excluded from the current public
history and new commits. Their local copies remain unchanged. They were previously
public, and existing copies may persist. The cleanup does not make the underlying
public corpus confidential or prove that later evaluation would use unseen text.

The legacy composite source is excluded from training as a redundant composite;
its retained raw artifact is not independently relicensed by this project.
