from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi
from gene_registry.processing_state import marker, retry_decision, validator_fingerprint


DISPATCHED_MARKER_PREFIX = (
    "<!-- gene-embeddings-auto-dispatched:"
)


def get_value(
    value: Any,
    key: str,
    default: Any = None,
) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)

    return getattr(value, key, default)


def author_name(value: Any) -> str:
    author = get_value(value, "author")

    if isinstance(author, str):
        return author

    name = get_value(author, "name")

    if name:
        return str(name)

    return str(author or "")


def event_content(event: Any) -> str:
    content = get_value(event, "content")

    if content:
        return str(content)

    raw_event = get_value(event, "_event", {}) or event
    data = get_value(raw_event, "data", {}) or {}
    latest = get_value(data, "latest", {}) or {}
    raw = get_value(latest, "raw")

    return str(raw or "")


def latest_head_sha(details: Any) -> str:
    commits: list[str] = []

    for event in get_value(
        details,
        "events",
        [],
    ) or []:
        if get_value(event, "type") != "commit":
            continue

        raw_event = (
            get_value(event, "_event", {})
            or event
        )

        data = (
            get_value(raw_event, "data", {})
            or {}
        )

        oid = (
            get_value(event, "oid")
            or get_value(data, "oid")
        )

        if oid:
            commits.append(str(oid))

    if not commits:
        raise ValueError(
            "No commit event was found in the "
            "Hugging Face Pull Request."
        )

    return commits[-1]


def dispatched_marker(head_sha: str) -> str:
    return (
        f"{DISPATCHED_MARKER_PREFIX}"
        f"{head_sha} -->"
    )


def already_dispatched(
    details: Any,
    head_sha: str,
) -> bool:
    marker = dispatched_marker(head_sha)

    return any(
        marker in event_content(event)
        for event in (
            get_value(details, "events", [])
            or []
        )
    )


def discover_next_submission(
    api: HfApi,
    repo_id: str,
    repo_type: str,
    validator_version: str | None = None,
    now=None,
) -> dict[str, Any]:
    discussions = sorted(
        api.get_repo_discussions(
            repo_id=repo_id,
            repo_type=repo_type,
        ),
        key=lambda item: int(
            get_value(item, "num", 0)
        ),
    )

    skipped: list[dict[str, Any]] = []

    for discussion in discussions:
        number = int(
            get_value(discussion, "num", 0)
        )

        if not get_value(
            discussion,
            "is_pull_request",
            False,
        ):
            continue

        status = str(
            get_value(discussion, "status", "")
        ).lower()

        if status != "open":
            continue

        details = api.get_discussion_details(
            repo_id=repo_id,
            repo_type=repo_type,
            discussion_num=number,
        )

        target_branch = get_value(
            details,
            "target_branch",
        )

        if target_branch not in {
            None,
            "refs/heads/main",
        }:
            skipped.append(
                {
                    "pr_number": number,
                    "reason": (
                        "unsupported target branch"
                    ),
                    "target_branch": target_branch,
                }
            )
            continue

        head_sha = latest_head_sha(details)

        if validator_version:
            events = [
                {"content": event_content(event),
                 "created_at": get_value(event, "created_at", get_value(event, "createdAt"))}
                for event in (get_value(details, "events", []) or [])
            ]
            eligible, reason = retry_decision(events, head_sha, validator_version, now)
        else:
            eligible = not already_dispatched(details, head_sha)
            reason = "current revision already dispatched"
        if not eligible:
            skipped.append(
                {
                    "pr_number": number,
                    "reason": reason,
                    "head_sha": head_sha,
                }
            )
            continue

        author = (
            author_name(details)
            or author_name(discussion)
        )

        if not author:
            raise ValueError(
                f"Could not determine author of PR #{number}."
            )

        return {
            "found": True,
            "repo_id": repo_id,
            "repo_type": repo_type,
            "pr_number": number,
            "pr_author": author,
            "head_sha": head_sha,
            "title": str(
                get_value(
                    discussion,
                    "title",
                    "",
                )
            ),
            "validator_version": validator_version,
            "marker": (marker("dispatched", head_sha, validator_version)
                       if validator_version else dispatched_marker(head_sha)),
            "skipped": skipped,
        }

    return {
        "found": False,
        "repo_id": repo_id,
        "repo_type": repo_type,
        "skipped": skipped,
    }


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
        "--output",
        required=True,
    )

    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN")

    api = HfApi(
        token=token,
    )

    result = discover_next_submission(
        api=api,
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        validator_version=validator_fingerprint(),
    )

    output = Path(args.output)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    if result["found"]:
        print(
            "Eligible Hugging Face PR:",
            result["pr_number"],
        )
        print(
            "Author:",
            result["pr_author"],
        )
        print(
            "Head commit:",
            result["head_sha"],
        )
    else:
        print(
            "No undispatched open Hugging Face "
            "submission PR was found."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
