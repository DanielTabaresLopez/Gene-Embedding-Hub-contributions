import pytest

from gene_registry.hf_pr import (
    compare_repo_trees,
    extract_pr_commits,
    render_synthetic_diff,
    require_additions_only,
)


def test_extract_pr_commits() -> None:
    info = {
        "is_pull_request": True,
        "events": [
            {
                "type": "commit",
                "oid": "head123",
                "_event": {
                    "data": {
                        "oid": "head123",
                        "parents": ["parent123"],
                    }
                },
            }
        ],
    }

    parent, head = extract_pr_commits(info)

    assert parent == "parent123"
    assert head == "head123"


def test_compare_repo_trees() -> None:
    parent = {
        "unchanged.txt": {"blob_id": "a"},
        "modified.txt": {"blob_id": "b"},
        "deleted.txt": {"blob_id": "c"},
    }

    proposed = {
        "unchanged.txt": {"blob_id": "a"},
        "modified.txt": {"blob_id": "different"},
        "added.txt": {"blob_id": "d"},
    }

    assert compare_repo_trees(
        parent,
        proposed,
    ) == [
        {
            "path": "added.txt",
            "action": "ADDED",
        },
        {
            "path": "deleted.txt",
            "action": "DELETED",
        },
        {
            "path": "modified.txt",
            "action": "MODIFIED",
        },
    ]


def test_additions_only_passes() -> None:
    changes = [
        {
            "path": "incoming/example/README.md",
            "action": "ADDED",
        }
    ]

    require_additions_only(changes)

    assert render_synthetic_diff(changes) == (
        "diff --git "
        "a/incoming/example/README.md "
        "b/incoming/example/README.md\n"
    )


def test_modifications_are_rejected() -> None:
    changes = [
        {
            "path": "data/community_contributions/community_registry.json",
            "action": "MODIFIED",
        }
    ]

    with pytest.raises(
        ValueError,
        match="may only add new files",
    ):
        require_additions_only(changes)
