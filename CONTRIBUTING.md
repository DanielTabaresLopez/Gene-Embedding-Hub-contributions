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
- The repository must remain public during validation and after acceptance.

- `broad_modality` is a contributor-defined catalog category of 2–80 characters. New category names are accepted automatically, but the value must match exactly between the submission YAML and `metadata.json`.

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

## 5. Community package storage and availability

Accepted community matrices remain in the contributor-owned public Hugging Face
Dataset at the submitted immutable commit SHA. The central library stores the
catalog entry, provenance, checksums and validation reports, but does not create
a second copy of `embeddings.npz`.

The submitted Dataset and immutable revision must remain publicly accessible
after acceptance. An entry may be marked unavailable or removed from the active
catalog if its source package is later deleted or made private.
