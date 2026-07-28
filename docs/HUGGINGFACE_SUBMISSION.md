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
├── metadata.json
├── README.md
└── submission.yaml
~~~

The embedding ID must contain 3–80 lowercase letters, numbers,
dots, underscores, or hyphens. It must begin with a letter or
number.

Start from `portal_template/submission.yaml`.

## Browser submission

1. Open the Gene Embeddings Space.
2. Click **Upload an embedding**.
3. Sign in to Hugging Face.
4. Upload the five files under:

   ~~~text
   incoming/<embedding_id>/
   ~~~

5. Enter a descriptive commit message.
6. Select **Open as a pull request**.
7. Do not commit directly to `main`.
8. Ensure the resulting Pull Request is Open or Ready for review,
   not Draft.

## Command-line alternative

~~~bash
hf upload \
  embeddingsSSRF/gene_embeddings_staging \
  ./<embedding_id> \
  incoming/<embedding_id> \
  --repo-type dataset \
  --create-pr \
  --commit-message "Submit <embedding_id>"
~~~

Programmatic submissions may initially be created as Draft.
Change the status to Open or Ready for review before processing.

## Categories

Recommended catalog categories are:

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
displayed under `Other`. The originally submitted value is
preserved in the provenance and validation report.

## Validation and central storage

GitHub Actions:

1. inspect the proposed Hugging Face repository tree;
2. ensure the PR adds exactly one permitted package folder;
3. validate the matrix, genes, metadata, provenance, licensing,
   and attestations;
4. copy a strict-PASS package into the library Dataset;
5. update the registry and static Space;
6. comment on and close the Hugging Face Pull Request.

Accepted packages are centrally archived under:

~~~text
data/embeddings/<embedding_id>/
~~~

The original `incoming/` proposal is not merged into `main`.

Failed submissions are not published.

## Privacy

Do not place personal email addresses, patient information,
patient-level data, credentials, access tokens, or other
sensitive information in the submission.

## Staging status

The current Space button targets the staging Dataset. While that
Dataset is private, only organization members or users with
access can submit.

During the current staging checkpoint, a maintainer starts the
processor manually. Scheduled discovery of new open Pull Requests
will be enabled after the interface is verified.
