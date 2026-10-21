# Contributing an embedding

Use the [Hugging Face staging uploader](https://huggingface.co/datasets/BoevaLab/Gene-Embedding-Hub-contributions-staging/upload/main)
and select **Open as a pull request**.

Upload one folder named exactly as the unique `embedding_id`, containing:

- `embeddings.npz`: one two-dimensional float32 array named `embeddings`;
- `genes.tsv`: one row per matrix row, with unique unversioned `ensembl_gene_id` values;
- `README.md`: documentation of the representation;
- `submission.yaml`: fill in the current [template](portal_template/submission.yaml).

The [completed example](portal_template/submission.example.yaml) describes the
existing ESM-2 catalogue entry. Replace its ID and contents for your own embedding.
`metadata.json` is generated automatically after validation.

Read [the submission guide](docs/HUGGINGFACE_SUBMISSION.md) for categories,
identifier mapping, corrections and diagnostics. Accepted packages are stored in
`data/community_contributions/<embedding_id>/` and added to the current catalogue.
