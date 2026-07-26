# Contributing a gene embedding

## 1. Prepare a public Hugging Face Dataset

Your candidate repository must contain one package directory with:

```text
<package_path>/
├── embeddings.npz
├── genes.tsv
├── metadata.json
└── README.md
```

Required package contract:

- `embeddings.npz` contains exactly one array named `embeddings`.
- The array is a two-dimensional `float32` matrix.
- `genes.tsv` contains a unique, non-empty `ensembl_gene_id` column.
- Rows of `genes.tsv` correspond exactly to rows of `embeddings`.
- The repository is public while validation runs.

## 2. Freeze the candidate

Open the candidate Dataset's **Files and versions** page and copy its full 40-character commit SHA. Do not submit `main`.

## 3. Run the same validator locally or in a temporary notebook

```bash
python -m pip install -e .
python -m gene_registry.cli validate \
  --submission submissions/my_embedding.yaml \
  --policy config/policy.yaml \
  --master-genes reference/master_gene_ids.txt \
  --schema-dir schemas \
  --output-dir validation-output
```

This pre-check is optional. GitHub reruns the validator independently.

## 4. Open a Pull Request

1. Fork this GitHub repository.
2. Copy `submissions/_template.yaml` to `submissions/<embedding_id>.yaml`.
3. Fill every field and all attestations.
4. Change **only that one submission file**.
5. Open a Pull Request to `main`.

The trusted workflow reads the YAML as data, downloads the frozen Hugging Face package, and applies the automatic acceptance policy. A strict PASS is merged and published automatically. A failure remains open for correction.
