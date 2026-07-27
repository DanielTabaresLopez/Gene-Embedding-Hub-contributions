# Gene Embeddings Automatic Contribution Registry

This repository is the automation layer for a gene-embedding library hosted on Hugging Face.

## Architecture

- **Hugging Face core Dataset**: stores the centrally curated core collection.
- **Contributor Hugging Face Datasets**: retain accepted community matrices at immutable revisions.
- **Hugging Face registry Dataset**: stores community provenance, checksums and validation reports without duplicating matrices.
- **Hugging Face Static Space**: browses the combined core and community catalog.
- **GitHub Pull Requests**: contributors add one small YAML submission file.
- **GitHub Actions**: validates, auto-merges, registers accepted submissions and updates the Space.

The automatic workflow treats inclusion as **technical policy compliance**, not independent scientific or legal endorsement.

Start with [`docs/SETUP.md`](docs/SETUP.md).
