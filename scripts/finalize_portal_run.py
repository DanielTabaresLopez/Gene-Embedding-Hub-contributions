"""Post a revision-specific result; never close a newer revision of the PR."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from huggingface_hub import HfApi
from gene_registry.processing_state import marker, validator_fingerprint
from scripts.discover_hf_submission import latest_head_sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--requested-revision", default="")
    parser.add_argument("--published", choices=["true", "false"], required=True)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    inspection = Path("hf-pr-state/inspection.json")
    info = json.loads(inspection.read_text()) if inspection.exists() else {}
    head = info.get("head_sha") or args.requested_revision
    report_path = Path("dist/reports/validation_report.json")
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    published = args.published == "true"
    outcome = "PUBLISHED" if published else ("REJECTED" if report.get("outcome") == "FAIL" else "ERROR")
    summary_path = Path("dist/reports/validation_summary.md")
    body = summary_path.read_text() if summary_path.exists() else "The workflow stopped before package validation completed."
    if published:
        body += "\n\nPublication: the validated package, registry and catalogue are updated."
    elif outcome == "ERROR":
        body += "\n\nPublication did not finish. An interrupted publication can be retried; see the failed step below."
    else:
        body += "\n\nThis revision was not accepted. Correct the reported checks and commit the changes to this PR."
    body += f"\n\n[Workflow details and diagnostic artifacts]({args.run_url})\n"
    if head:
        body += f"\nRevision: `{head}`\n" + marker("processed", head, validator_fingerprint(), outcome)
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_PR_TOKEN is required to report the result")
    api = HfApi(token=token)
    details = api.get_discussion_details(repo_id=args.repo_id, repo_type="dataset", discussion_num=args.pr_number)
    current_head = latest_head_sha(details)
    if published and current_head == head and details.status == "open":
        # Close first; only a successful close makes the final publication marker
        # terminal for discovery. If close fails, a later retry can finish it.
        api.change_discussion_status(repo_id=args.repo_id, repo_type="dataset",
                                     discussion_num=args.pr_number, new_status="closed")
    api.comment_discussion(repo_id=args.repo_id, repo_type="dataset", discussion_num=args.pr_number, comment=body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
