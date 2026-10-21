from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def extract_pr_commits(
    discussion_info: Mapping[str, Any],
) -> tuple[str, str]:
    if not discussion_info.get("is_pull_request", discussion_info.get("isPullRequest")):
        raise ValueError(
            "The selected Hugging Face discussion is not a Pull Request."
        )

    commit_events = [
        event
        for event in discussion_info.get("events", [])
        if event.get("type") == "commit"
    ]

    if not commit_events:
        raise ValueError(
            "No commit event was found in the Hugging Face Pull Request."
        )

    first, latest = commit_events[0], commit_events[-1]
    event_data = latest.get("data") or latest.get("_event", {}).get("data", {})
    first_data = first.get("data") or first.get("_event", {}).get("data", {})

    head_sha = (
        latest.get("oid")
        or event_data.get("oid")
    )

    # Compare the final tree with the base of the whole PR. Using the parent
    # of the LAST commit incorrectly rejects contributors who fix their YAML.
    parents = first_data.get("parents", first.get("parents", []))

    if not head_sha:
        raise ValueError(
            "Could not determine the Pull Request head commit."
        )

    if len(parents) != 1:
        raise ValueError(
            "Expected exactly one parent commit for the Pull Request; "
            f"found {parents!r}."
        )

    return str(parents[0]), str(head_sha)


def compare_repo_trees(
    parent_files: Mapping[str, Any],
    proposed_files: Mapping[str, Any],
) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []

    all_paths = sorted(
        set(parent_files) | set(proposed_files)
    )

    for path in all_paths:
        parent_value = parent_files.get(path)
        proposed_value = proposed_files.get(path)

        if parent_value == proposed_value:
            continue

        if path not in parent_files:
            action = "ADDED"
        elif path not in proposed_files:
            action = "DELETED"
        else:
            action = "MODIFIED"

        changes.append(
            {
                "path": path,
                "action": action,
            }
        )

    return changes


def require_additions_only(
    changes: list[dict[str, str]],
) -> None:
    unsafe = [
        change
        for change in changes
        if change["action"] != "ADDED"
    ]

    if unsafe:
        formatted = ", ".join(
            f"{change['action']} {change['path']}"
            for change in unsafe
        )

        raise ValueError(
            "Portal Pull Requests may only add new files. "
            f"Detected: {formatted}"
        )


def render_synthetic_diff(
    changes: list[dict[str, str]],
) -> str:
    return "".join(
        f"diff --git a/{change['path']} b/{change['path']}\n"
        for change in changes
    )
