from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi

from gene_registry.hf_pr import (
    compare_repo_trees,
    extract_pr_commits,
    render_synthetic_diff,
    require_additions_only,
)


def lfs_sha256(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, dict):
        result = value.get("sha256")
    else:
        result = getattr(value, "sha256", None)

    return None if result is None else str(result)


def repository_files(
    api: HfApi,
    repo_id: str,
    repo_type: str,
    revision: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for item in api.list_repo_tree(
        repo_id=repo_id,
        repo_type=repo_type,
        revision=revision,
        recursive=True,
    ):
        blob_id = getattr(item, "blob_id", None)

        # Repository folders have no blob ID.
        if blob_id is None:
            continue

        xet_hash = getattr(item, "xet_hash", None)

        result[str(item.path)] = {
            "blob_id": str(blob_id),
            "size": getattr(item, "size", None),
            "xet_hash": (
                None
                if xet_hash is None
                else str(xet_hash)
            ),
            "lfs_sha256": lfs_sha256(
                getattr(item, "lfs", None)
            ),
        }

    return result


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-id",
        required=True,
    )
    parser.add_argument(
        "--repo-type",
        default="dataset",
    )
    parser.add_argument(
        "--pr-number",
        required=True,
        type=int,
    )
    parser.add_argument(
        "--info-json",
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    parser.add_argument(
        "--summary-json",
        required=True,
    )

    args = parser.parse_args()

    info = json.loads(
        Path(args.info_json).read_text(
            encoding="utf-8"
        )
    )

    parent_sha, head_sha = extract_pr_commits(
        info
    )

    pr_revision = f"refs/pr/{args.pr_number}"
    api = HfApi()

    parent_files = repository_files(
        api=api,
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        revision=parent_sha,
    )

    proposed_files = repository_files(
        api=api,
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        revision=pr_revision,
    )

    changes = compare_repo_trees(
        parent_files,
        proposed_files,
    )

    if not changes:
        raise ValueError(
            "No changed files were detected by repository-tree comparison."
        )

    require_additions_only(changes)

    output = Path(args.output)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output.write_text(
        render_synthetic_diff(changes),
        encoding="utf-8",
    )

    summary = {
        "pr_number": args.pr_number,
        "author": info.get("author"),
        "status": info.get("status"),
        "parent_sha": parent_sha,
        "head_sha": head_sha,
        "pr_revision": pr_revision,
        "changes": changes,
    }

    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print("Parent commit:", parent_sha)
    print("PR head commit:", head_sha)
    print("PR revision:", pr_revision)
    print("Changed files:")

    for change in changes:
        print(
            f" - {change['action']}: "
            f"{change['path']}"
        )

    print("Changed file count:", len(changes))
    print("Repository-tree comparison: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
