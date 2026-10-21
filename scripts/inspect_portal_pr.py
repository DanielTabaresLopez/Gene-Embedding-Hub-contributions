from __future__ import annotations

import argparse
import dataclasses
import re

from huggingface_hub import HfApi

from gene_registry.hf_pr import compare_repo_trees, extract_pr_commits, require_additions_only, render_synthetic_diff
from gene_registry.portal import inspect_portal_diff
from gene_registry.util import load_yaml, write_json
from gene_registry.models import ValidationResult
from gene_registry.report import write_report
from scripts.build_hf_pr_diff import repository_files


def inspect(api, repo_id, pr_number, policy, expected_revision=None):
    details = api.get_discussion_details(repo_id=repo_id, repo_type="dataset", discussion_num=pr_number)
    info = dataclasses.asdict(details) if dataclasses.is_dataclass(details) else details
    if info.get("status") != "open":
        raise ValueError("The submission PR must be open/ready for review")
    target = info.get("target_branch", info.get("changes", {}).get("base"))
    if target not in (None, "main", "refs/heads/main"):
        raise ValueError("The submission PR must target main")
    base, head = extract_pr_commits(info)
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("Invalid PR commit SHA")
    if expected_revision and head != expected_revision:
        raise ValueError("The PR changed since it was queued; its new revision will be processed separately")
    original = repository_files(api, repo_id, "dataset", base)
    proposed = repository_files(api, repo_id, "dataset", head)
    changes = compare_repo_trees(original, proposed)
    require_additions_only(changes)
    result = inspect_portal_diff(render_synthetic_diff(changes))
    sizes = {c["path"]: proposed[c["path"]]["size"] for c in changes}
    if any(not isinstance(size, int) or size < 0 for size in sizes.values()):
        raise ValueError("Could not establish every proposed file's download size")
    if sum(sizes.values()) > policy["limits"]["max_candidate_download_bytes"]:
        raise ValueError("Proposed package exceeds the total download size limit")
    yaml_path = f"{result['package_path']}/submission.yaml"
    if sizes[yaml_path] > policy["limits"]["max_submission_yaml_bytes"]:
        raise ValueError("submission.yaml exceeds the configured size limit")
    author = info.get("author", "")
    author = author.get("name", "") if isinstance(author, dict) else author
    if not isinstance(author, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,96}", author):
        raise ValueError("Could not establish the actual PR author's username")
    return {**result, "head_sha": head, "base_sha": base, "pr_number": pr_number,
            "pr_author": author, "download_bytes": sum(sizes.values())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--pr-number", required=True, type=int)
    parser.add_argument("--expected-revision", default="")
    parser.add_argument("--policy", default="config/policy.yaml")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = inspect(HfApi(token=False), args.repo_id, args.pr_number,
                         load_yaml(args.policy), args.expected_revision or None)
    except Exception as exc:
        outcome = "FAIL" if isinstance(exc, ValueError) else "ERROR"
        result = ValidationResult(outcome=outcome)
        result.add("pr.inspection", "FAIL", f"{type(exc).__name__}: {exc}")
        write_report(result, "dist/reports")
        raise SystemExit(2 if outcome == "FAIL" else 3)
    write_json(args.output, result)
    print(f"Inspected PR #{args.pr_number}: {result['embedding_id']} at {result['head_sha']}")


if __name__ == "__main__":
    main()
