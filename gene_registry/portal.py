from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any


PORTAL_ROOT = "incoming"

REQUIRED_PORTAL_FILES = {
    "embeddings.npz",
    "genes.tsv",
    "metadata.json",
    "README.md",
    "submission.yaml",
}

OPTIONAL_PORTAL_FILES = {
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.md",
}

ALLOWED_PORTAL_FILES = REQUIRED_PORTAL_FILES | OPTIONAL_PORTAL_FILES

DIFF_PATH_RE = re.compile(
    r"^diff --git a/(.+?) b/(.+?)$",
    flags=re.MULTILINE,
)


def changed_paths_from_diff(diff_text: str) -> set[str]:
    paths: set[str] = set()

    for left, right in DIFF_PATH_RE.findall(diff_text):
        paths.add(left)
        paths.add(right)

    return paths


def inspect_portal_diff(diff_text: str) -> dict[str, Any]:
    changed_paths = changed_paths_from_diff(diff_text)

    if not changed_paths:
        raise ValueError(
            "The Pull Request does not contain detectable file changes."
        )

    embedding_ids: set[str] = set()
    filenames: set[str] = set()

    for raw_path in sorted(changed_paths):
        path = PurePosixPath(raw_path)
        parts = path.parts

        if not parts or parts[0] != PORTAL_ROOT:
            raise ValueError(
                "Pull Requests may change only files under "
                f"incoming/<embedding_id>/: {raw_path}"
            )

        if len(parts) != 3:
            raise ValueError(
                "Every changed file must be directly inside "
                f"incoming/<embedding_id>/: {raw_path}"
            )

        _, embedding_id, filename = parts

        if not re.fullmatch(
            r"[a-z0-9][a-z0-9._-]{2,79}",
            embedding_id,
        ):
            raise ValueError(
                f"Invalid embedding ID in path: {embedding_id!r}"
            )

        if filename not in ALLOWED_PORTAL_FILES:
            raise ValueError(
                f"Unexpected submission file: {raw_path}"
            )

        embedding_ids.add(embedding_id)
        filenames.add(filename)

    if len(embedding_ids) != 1:
        raise ValueError(
            "A Pull Request must contain exactly one embedding folder."
        )

    missing = sorted(REQUIRED_PORTAL_FILES - filenames)

    if missing:
        raise ValueError(
            f"Required submission files are missing: {missing}"
        )

    embedding_id = next(iter(embedding_ids))

    return {
        "embedding_id": embedding_id,
        "package_path": f"{PORTAL_ROOT}/{embedding_id}",
        "changed_files": sorted(changed_paths),
        "required_files": sorted(REQUIRED_PORTAL_FILES),
    }
