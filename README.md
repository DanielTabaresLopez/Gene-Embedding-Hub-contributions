# Gene Embeddings Automatic Contribution Registry

This repository is the trusted automation layer for a
gene-embedding library hosted on Hugging Face.

## Architecture

- **Hugging Face core Dataset** stores the centrally curated core
  collection.
- **Library-owned Hugging Face Dataset** receives community
  submissions as Hugging Face Pull Requests and permanently
  stores accepted packages.
- **Hugging Face Static Space** browses the combined core and
  community catalog and links contributors to the Hub uploader.
- **GitHub Actions** inspects Hugging Face PR repository trees,
  validates submitted packages, updates the registry and Space,
  and closes accepted PRs without merging the original
  submission folders.
- **Contributors** need a Hugging Face account but do not need a
  GitHub account, GitHub fork, separate Dataset, or commit SHA.

The automatic workflow treats inclusion as **technical policy
compliance**, not independent scientific or legal endorsement.

Contributor instructions are available in
[`docs/HUGGINGFACE_SUBMISSION.md`](docs/HUGGINGFACE_SUBMISSION.md).

Maintainer setup documentation is available in
[`docs/SETUP.md`](docs/SETUP.md).
