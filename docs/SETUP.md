# End-to-end setup

Replace the example repository names before enabling automatic publication.

## A. Create the public GitHub automation repository

Recommended name: `Gene-Embedding-Hub-contributions`.

1. Create it as **Public** so standard GitHub-hosted Actions do not consume paid minutes.
2. Upload the complete contents of this starter kit.
3. Add your supervisor as an administrator or maintainer.
4. Edit `config/project.yaml`, `space/app.js`, `space/README.md`, and both publication workflow files with the final GitHub, Dataset, and Space IDs.
5. Push to `main` and confirm the `Test trusted validator` workflow passes.

## B. Create or select Hugging Face repositories

You need:

- an authoritative Dataset, for example `BoevaLab/Gene-Embedding-Hub-dataset`;
- a free Static Space, for example `BoevaLab/Gene-Embeddings`.

The Dataset should be public before tokenless automatic publication is enabled. The Space README must use `sdk: static` and `app_file: index.html`.

Upload the current Space catalog once before the first contribution. `scripts/prepare_release.py` preserves the remote catalog and appends the accepted card.

## C. Configure Hugging Face Trusted Publishers

On the Dataset:

1. Open **Settings → Trusted Publishers**.
2. Add provider **GitHub Actions**.
3. Set repository to the exact GitHub automation repository, e.g. `DanielTabaresLopez/Gene-Embedding-Hub-contributions`.
4. Set branch to `main`.
5. Set workflow to `publish.yml`.

Repeat on the Static Space. These are two separate repo-scoped publishers, but both are restricted to the single workflow `publish.yml`.

## D. Configure GitHub Actions permissions

Open **Settings → Actions → General**.

- Allow GitHub Actions.
- Set default workflow permissions to read-only; each workflow requests its minimum permissions explicitly.
- Enable **Allow GitHub Actions to create and approve pull requests** if your account UI requires this for bot merging.
- Do not send secrets or write tokens to fork Pull Request workflows.

The contribution workflow uses `pull_request_target`, which runs trusted base code regardless of first-time contributor approval settings. Do not replace it with contributor-controlled workflow code.

## E. Configure branch rules

Create a rule for `main`:

- require changes through a Pull Request;
- require zero human approvals for submission PRs;
- block force pushes and deletion;
- do not require the `Validate and auto-accept candidate` job as a status check, because that same running job performs the merge after validation;
- allow repository administrators to repair the system.

Maintenance PRs that modify validator or workflow code should still be reviewed manually by owners.

## F. Bootstrap the Static Space

After configuring the Space Trusted Publisher, open **GitHub → Actions → Publish to Hugging Face → Run workflow**. Choose `mode = bootstrap_space` and `accepted_commit = main`. The workflow copies the static interface while preserving the Space's existing remote `catalog.json`.

Update the GitHub contribution links in `space/app.js` before running this bootstrap.

## G. Run an end-to-end staging test

1. Create separate staging Dataset and Static Space repositories.
2. Point `config/project.yaml` and workflow resource IDs to staging.
3. Run:

   ```bash
   python scripts/create_smoke_candidate.py \
     --output-dir /tmp/smoke/candidate_embedding \
     --embedding-id smoke_test_embedding
   ```

4. Upload that package to a public personal HF Dataset.
5. Copy its full commit SHA into a new `submissions/smoke_test_embedding.yaml` based on the template.
6. Open a Pull Request containing only that YAML.
7. Confirm the workflow comments a strict PASS, merges the PR, dispatches publication, adds the package to staging, and updates the staging Space.
8. Delete the smoke-test package from staging after the test.

## H. Switch to production

After the staging test succeeds:

1. Restore production IDs in `config/project.yaml`, `publish.yml`, and `reconcile.yml`.
2. Configure Trusted Publishers on the production Dataset and Space.
3. Push the change through an owner-reviewed maintenance PR.
4. Open one controlled real-candidate PR.
5. Verify the full automatic lifecycle.

## I. Operational behavior

- Failed validation leaves the PR open with a report. The contributor corrects the candidate, creates a new frozen HF commit, and updates the YAML; the workflow reruns.
- Strict PASS causes automatic squash merge and publication.
- The six-hourly reconciliation workflow publishes any merged submission missing from the HF community registry after a temporary platform failure.
- Existing legacy packages remain untouched. Automatic additions are tracked in `data/community_registry.json` and `data/community_manifest.csv` and live under the same `data/embeddings/` root.
