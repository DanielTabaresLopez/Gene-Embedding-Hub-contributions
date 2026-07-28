# Contributing a gene embedding

Contributors submit directly to the library-owned Hugging Face
Dataset as a Hugging Face Pull Request.

A GitHub account, GitHub fork, personal Dataset, and commit SHA
are not required.

## 1. Prepare the package

Create one uniquely named folder:

```text
<embedding_id>/
├── embeddings.npz
├── genes.tsv
├── metadata.json
├── README.md
└── submission.yaml
```

Start from `portal_template/submission.yaml`.

The embedding ID must contain 3–80 lowercase letters, numbers,
dots, underscores, or hyphens and must begin with a letter or
number.

## 2. Upload to Hugging Face

Upload the folder under:

```text
incoming/<embedding_id>/
```

Select **Open as a pull request**. Do not commit directly to
`main`.

Ensure that the Pull Request is Open or Ready for review rather
than Draft.

## 3. Validation and publication

The trusted GitHub workflow inspects the proposed repository tree
and validates the five-file package.

A strict PASS is copied into the central Dataset under:

```text
data/embeddings/<embedding_id>/
```

The community registry and static Space catalog are then updated.
The raw `incoming/` proposal is closed without being merged into
`main`.

Failed submissions are not published.

## 4. Privacy

Do not upload personal email addresses, credentials, access
tokens, patient information, patient-level data, or other
sensitive material.

See `docs/HUGGINGFACE_SUBMISSION.md` for the complete guide.
