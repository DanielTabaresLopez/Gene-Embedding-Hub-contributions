from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any


LEGACY_PORTAL_ROOT = "incoming"

RESERVED_ROOT_FOLDERS = {
    "data",
    "incoming",
}

REQUIRED_PORTAL_FILES = {
    "embeddings.npz",
    "genes.tsv",
    "README.md",
    "submission.yaml",
}

OPTIONAL_PORTAL_FILES = {
    "metadata.json",
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.md",
}

ALLOWED_PORTAL_FILES = (
    REQUIRED_PORTAL_FILES
    | OPTIONAL_PORTAL_FILES
)

DIFF_PATH_RE = re.compile(
    r"^diff --git a/(.+?) b/(.+?)$",
    flags=re.MULTILINE,
)


def changed_paths_from_diff(
    diff_text: str,
) -> set[str]:
    paths: set[str] = set()

    for left, right in DIFF_PATH_RE.findall(
        diff_text
    ):
        paths.add(left)
        paths.add(right)

    return paths


def parse_submission_path(
    raw_path: str,
) -> tuple[str, str, str]:
    path = PurePosixPath(raw_path)
    if path.is_absolute() or ".." in path.parts or "\\" in raw_path:
        raise ValueError(f"Unsafe submission path: {raw_path!r}")
    parts = path.parts

    if len(parts) == 2:
        embedding_id, filename = parts

        if embedding_id in RESERVED_ROOT_FOLDERS:
            raise ValueError(
                "Reserved repository folder cannot be "
                f"used as an embedding ID: {embedding_id!r}"
            )

        package_path = embedding_id

    elif (
        len(parts) == 3
        and parts[0] == LEGACY_PORTAL_ROOT
    ):
        _, embedding_id, filename = parts

        package_path = (
            f"{LEGACY_PORTAL_ROOT}/"
            f"{embedding_id}"
        )

    else:
        raise ValueError(
            "Every changed file must be directly inside "
            "<embedding_id>/, or inside the legacy "
            "incoming/<embedding_id>/ layout: "
            f"{raw_path}"
        )

    if not re.fullmatch(
        r"[a-z0-9][a-z0-9._-]{2,79}",
        embedding_id,
    ):
        raise ValueError(
            "Invalid embedding ID in path: "
            f"{embedding_id!r}"
        )

    if filename not in ALLOWED_PORTAL_FILES:
        raise ValueError(
            f"Unexpected submission file: {raw_path}"
        )

    return (
        embedding_id,
        filename,
        package_path,
    )


def inspect_portal_diff(
    diff_text: str,
) -> dict[str, Any]:
    changed_paths = changed_paths_from_diff(
        diff_text
    )

    if not changed_paths:
        raise ValueError(
            "The Pull Request does not contain "
            "detectable file changes."
        )

    embedding_ids: set[str] = set()
    filenames: set[str] = set()
    package_paths: set[str] = set()

    for raw_path in sorted(changed_paths):
        (
            embedding_id,
            filename,
            package_path,
        ) = parse_submission_path(raw_path)

        embedding_ids.add(embedding_id)
        filenames.add(filename)
        package_paths.add(package_path)

    if (
        len(embedding_ids) != 1
        or len(package_paths) != 1
    ):
        raise ValueError(
            "A Pull Request must contain exactly "
            "one embedding folder."
        )

    missing = sorted(
        REQUIRED_PORTAL_FILES - filenames
    )

    if missing:
        raise ValueError(
            "Required submission files are "
            f"missing: {missing}"
        )

    embedding_id = next(iter(embedding_ids))
    package_path = next(iter(package_paths))

    return {
        "embedding_id": embedding_id,
        "package_path": package_path,
        "changed_files": sorted(
            changed_paths
        ),
        "required_files": sorted(
            REQUIRED_PORTAL_FILES
        ),
    }
