# Submit a gene embedding through Hugging Face

Contributors submit directly to the library-owned Hugging Face
Dataset. No GitHub account, GitHub fork, separate Dataset, or
commit SHA is required.

A Hugging Face account is required.

## Required folder

Prepare one folder named with a unique embedding ID:

~~~text
<embedding_id>/
├── embeddings.npz
├── genes.tsv
├── README.md
└── submission.yaml
~~~

Contributors do not need to upload `metadata.json`. Older packages
that contain it remain accepted for compatibility, but the publication
workflow replaces it with an automatically generated authoritative
version.

The required provenance fields are `species`,
`identifier_before_mapping`, and `mapping_method`, because they explain
how the identifiers in `genes.tsv` were obtained. Contributor details,
method, checkpoint, publication, source data, release, pooling,
source-license identifier, and terms URL are optional.

The embedding ID must contain 3–80 lowercase letters, numbers,
dots, underscores, or hyphens. It must begin with a letter or
number.

Start from `portal_template/submission.yaml`.

## Browser submission

1. Open the Gene Embeddings Space.
2. Click **Upload an embedding**.
3. Sign in to Hugging Face.
4. Upload the four files under:

   ~~~text
   <embedding_id>/
   ~~~

5. Enter a descriptive commit message.
6. Select **Open as a pull request**.
7. Do not commit directly to `main`.
8. Ensure the resulting Pull Request is Open or Ready for review,
   not Draft.

## Command-line alternative

~~~bash
hf upload \
  BoevaLab/Gene-Embedding-Hub-contributions-staging \
  ./<embedding_id> \
  <embedding_id> \
  --repo-type dataset \
  --create-pr \
  --commit-message "Submit <embedding_id>"
~~~

Programmatic submissions may initially be created as Draft.
Change the status to Open or Ready for review before processing.

## Categories

Recommended catalog categories are:

- Biomedical text
- DNA sequence
- Expression
- Functional
- Knowledge graph
- Multimodal
- Networks
- Protein sequence
- RNA sequence
- Regulatory genomics
- Single-cell

Matching is case-insensitive. Previous category labels are translated to their current names. A different value is accepted but
displayed under `Other`. The originally submitted value is
preserved in the provenance and validation report.

## Validation and central storage

GitHub Actions:

1. inspect the proposed Hugging Face repository tree;
2. ensure the PR adds exactly one permitted package folder;
3. validate the matrix, genes, metadata, provenance, licensing,
   and attestations;
4. copy a PASS package into the library Dataset;
5. update the registry and static Space;
6. comment on and close the Hugging Face Pull Request.

Accepted packages are centrally archived under:

~~~text
data/community_contributions/<embedding_id>/
~~~

The original proposal folder is not merged into staging `main`.

Failed submissions are not published.

## Privacy

Do not place personal email addresses, patient information,
patient-level data, credentials, access tokens, or other
sensitive information in the submission.

## Automatic processing and corrections

The staging Dataset is public. Open PRs are discovered automatically; scheduling
can be delayed by GitHub. A draft must first be marked ready for review.
A correction can be committed to the same PR: the complete proposed package is
validated at one immutable commit. Technical rejection reports identify the
blocking checks. Infrastructure failures include a workflow link and can be
retried after six hours, up to three attempts for the same PR revision and
validator version. Changes to the data or trusted validator allow fresh validation.
An interrupted release can resume when the PR revision and all package checksums
match the previously recorded attempt. Routine submissions update catalogue data
without replacing the static interface.

## Submission template and completed example

Use `submission.yaml` as the editable submission template. Keep the
section headers `scientific`, `provenance`, `licensing`, and
`attestations` unchanged, and replace the values nested inside them.

`submission.example.yaml` is a completed real-world example based on
the ESM-2 embedding processed in this project. It uses actual
scientific and provenance values and intentionally omits optional fields
whose exact values were not verified. It must not be submitted unchanged.

## Mapping identifiers to the master gene table

Before creating `genes.tsv`, convert the identifiers used by the source
embedding into the project's unversioned Ensembl gene IDs. Use unique
mappings only, report unmapped and ambiguous identifiers, and average
source rows that map to the same final gene.

See [`GENE_MAPPING_TUTORIAL.md`](GENE_MAPPING_TUTORIAL.md) for the
complete workflow, master-table download link, supported identifier
columns, symbol-priority rules, and code examples.
