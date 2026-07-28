# Submit a gene embedding through Hugging Face

Contributors submit directly to the library-owned Hugging Face
Dataset. No GitHub account, GitHub fork, separate Dataset, or
commit SHA is needed.

## Required folder

Prepare one folder named with a unique embedding ID:

~~~text
<embedding_id>/
├── embeddings.npz
├── genes.tsv
├── metadata.json
├── README.md
└── submission.yaml
~~~

The embedding ID must use lowercase letters, numbers, dots,
underscores, or hyphens.

Start from `portal_template/submission.yaml`.

## Upload as a Hugging Face Pull Request

Upload the complete folder to:

~~~text
incoming/<embedding_id>
~~~

Select the option to create a Pull Request rather than committing
directly to `main`.

Command-line example:

~~~bash
hf upload \
  embeddingsSSRF/gene_embeddings_staging \
  ./<embedding_id> \
  incoming/<embedding_id> \
  --repo-type dataset \
  --create-pr \
  --commit-message "Submit <embedding_id>"
~~~

## Categories

Recommended catalog categories:

- DNA
- Expression
- Functional Genomics
- Knowledge
- Literature
- Multimodal
- Network
- Protein
- RNA
- Regulatory
- Single-cell

Matching is case-insensitive. A different value is accepted but
displayed under `Other`. The submitted value remains preserved.

## Automatic processing

GitHub Actions will:

1. inspect the Pull Request structure;
2. validate the package and metadata;
3. post the result on the Hugging Face Pull Request;
4. copy a strict-PASS package into the library Dataset;
5. update the registry and static Space;
6. close the Pull Request after publication.

Failed submissions are not published.
