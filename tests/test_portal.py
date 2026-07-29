import pytest

from gene_registry.portal import (
    inspect_portal_diff,
)


def make_diff(paths: list[str]) -> str:
    return "\n".join(
        f"diff --git a/{path} b/{path}"
        for path in paths
    )


def valid_paths() -> list[str]:
    root = "incoming/example_embedding"

    return [
        f"{root}/embeddings.npz",
        f"{root}/genes.tsv",
        f"{root}/metadata.json",
        f"{root}/README.md",
        f"{root}/submission.yaml",
    ]


def test_valid_portal_submission() -> None:
    result = inspect_portal_diff(
        make_diff(valid_paths())
    )

    assert (
        result["embedding_id"]
        == "example_embedding"
    )

    assert (
        result["package_path"]
        == "incoming/example_embedding"
    )


def test_rejects_changes_outside_folder() -> None:
    paths = (
        valid_paths()
        + ["data/community_contributions/community_registry.json"]
    )

    with pytest.raises(
        ValueError,
        match="may change only files",
    ):
        inspect_portal_diff(
            make_diff(paths)
        )


def test_rejects_missing_required_file() -> None:
    paths = [
        path
        for path in valid_paths()
        if not path.endswith(
            "submission.yaml"
        )
    ]

    with pytest.raises(
        ValueError,
        match="missing",
    ):
        inspect_portal_diff(
            make_diff(paths)
        )


def test_rejects_multiple_embeddings() -> None:
    paths = (
        valid_paths()
        + [
            "incoming/second_embedding/"
            "embeddings.npz"
        ]
    )

    with pytest.raises(
        ValueError,
        match="exactly one embedding folder",
    ):
        inspect_portal_diff(
            make_diff(paths)
        )
