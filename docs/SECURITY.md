# Security model

The automatic PR workflow uses `pull_request_target` so it can run for first-time contributors without owner approval. This event is privileged.

The workflow is safe only if all of the following remain true:

1. It checks out the trusted base commit, never the contributor branch.
2. It accepts exactly one newly added `submissions/*.yaml` file.
3. It fetches that file through the GitHub API and treats it as untrusted data.
4. It uses `yaml.safe_load` plus a restrictive JSON Schema.
5. It accepts only a public Hugging Face Dataset ID, a full commit SHA, and a safe relative package path.
6. It never executes files from the candidate repository.
7. The validation/merge workflow has no Hugging Face token and no OIDC permission.
8. Publication happens in a separate `workflow_dispatch` run on trusted `main`.
9. Publication reruns validation from scratch before using Hugging Face OIDC.

Never add a step that checks out `${{ github.event.pull_request.head.sha }}` in the privileged workflow. Never run candidate scripts, notebooks, setup files, or arbitrary commands.
