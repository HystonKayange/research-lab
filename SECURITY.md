# Repository publication safeguards

This is a public research repository. Never commit service credentials, API tokens,
private keys, credential stores, or environment files containing secrets. An
`.env.example` may contain placeholders only. Keep operational secrets outside the
repository and supply them through the environment or a private secret store.

## Enforced checks

- GitHub secret scanning and push protection are enabled for this repository.
- `.gitignore` covers common credential stores, environment files, and private keys.
- The publication checker rejects sensitive filenames and protected research paths
  before it reads their contents. It scans other tracked text for provider tokens,
  private keys, credential assignments, authentication URLs, and bearer tokens.
- The checker reports paths, line numbers, and detector names; it never prints a
  matched credential. It does not send candidate credentials to external APIs.
- GitHub Actions runs the checker on pushes and pull requests. A local pre-commit
  hook runs the staged version of the check when `core.hooksPath` is `.githooks`.

Install the scanner separately from scientific dependencies:

```sh
python3 -m venv .venv-security
.venv-security/bin/python -m pip install -r requirements-security.txt
git config core.hooksPath .githooks
.venv-security/bin/python scripts/security/check_public_repository.py --staged
```

Entropy-only and public-IP detectors are excluded because the research record
contains hashes, generated IDs, and OS version strings. Provider-specific and
credential-context detectors remain enabled. This is a safeguard, not a guarantee
that every possible secret will be recognized.

## Protected research artifacts

LM-test split texts and document metadata, tokenizer test metrics, and the sealed
morphology-holdout payload/metadata are private local artifacts. Public lock notices
and documentation may remain tracked. These protections do not authorize anyone
to open a locked set or perform a scientific evaluation.

The publication cleanup removes these artifacts from the Git index while keeping
the existing local files. Their contents and the frozen development benchmark,
policies, historical results, and self-review measurements are unchanged.

The train and validation corpora and other research artifacts remain public. Since
the splits originate from public corpora, withholding test split files is not a
claim that the underlying source text is confidential or unrecoverable.

## Previously published history

Earlier public commits included the protected research files. Removing them from
the current branch does **not** erase them from older commits, existing clones,
forks, downloads, or caches. Author identities and historical filesystem paths
also remain in the historical record. No credentials were identified in the
completed text/history scan; binary assets and locked contents were not inspected.

Purging old copies requires a separately reviewed history rewrite, changing commit
IDs and the research freeze tag. Such a rewrite has not been performed. Keep a
private archival copy and provenance mapping if a rewrite is approved. Do not
describe this cleanup as complete removal of already published data.

## Reporting an exposure

Do not paste a suspected credential or private dataset into a public issue or pull
request. Contact the repository owner privately. If a real credential is exposed,
revoke or rotate it before addressing historical copies; deleting a file alone
does not invalidate the credential.
