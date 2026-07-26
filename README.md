# Gene Embeddings Automatic Contribution Registry

This repository is the automation layer for a gene-embedding library hosted on Hugging Face.

## Architecture

- **Hugging Face Dataset**: stores approved embedding packages.
- **Hugging Face Static Space**: browses the catalog and links to contribution instructions.
- **GitHub Pull Requests**: contributors add one small YAML submission file.
- **GitHub Actions**: validates, auto-merges, publishes to Hugging Face, and updates the Space.

The automatic workflow treats inclusion as **technical policy compliance**, not independent scientific or legal endorsement.

Start with [`docs/SETUP.md`](docs/SETUP.md).
