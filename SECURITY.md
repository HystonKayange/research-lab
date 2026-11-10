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

Earlier public commits included the protected research files. On 2026-11-10 the
repository owner approved removing all eight paths from published Git history and
replacing historical author/committer emails with the owner's GitHub noreply
address. Ten commits were rewritten. The only published ref was `main`; the
morphology freeze tag existed only locally and was remapped locally without
publishing a new tag. The push used an explicit lease on the original remote ID.

All 4,940 retained file versions were verified byte-for-byte unchanged. The frozen
development benchmark keeps its original SHA-256. Historical report bodies, result
files, and scientific measurements remain unchanged. Their original Git IDs can
be resolved using the [rewrite record](data/reports/public_history_rewrite_2026_11_10.json).
Historical filesystem paths remain part of those reports. Names and commit dates
were preserved; author and committer email fields now use the noreply address.

A private original-history bundle, uncommitted-work archive, validation record,
and commit map are stored outside public tracking under `.git/security-archive/`.
Never publish these backups or merge an old branch into the rewritten history.
Collaborators with older clones should make a fresh clone and transfer reviewed
local changes rather than merge the old history.

The rewrite removes these paths from the published branch history. It cannot
recall existing clones, forks, downloads, or GitHub cached/unreferenced views. A
GitHub Support request may be needed to address server-side cached references.
Do not describe this as complete removal of already published data. See
[GitHub's removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

No credentials were identified in the completed text/history scans. Binary assets
and protected dataset contents were not inspected for secrets, and neither locked
set was opened for scientific analysis or evaluation during the rewrite.

## Reporting an exposure

Do not paste a suspected credential or private dataset into a public issue or pull
request. Contact the repository owner privately. If a real credential is exposed,
revoke or rotate it before addressing historical copies; deleting a file alone
does not invalidate the credential.
