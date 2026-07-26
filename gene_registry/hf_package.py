from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, snapshot_download

REQUIRED_FILES = ("embeddings.npz", "genes.tsv", "metadata.json", "README.md")
ALLOWED_FILES = set(REQUIRED_FILES) | {"LICENSE", "LICENSE.txt", "LICENSE.md"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _join(package_path: str, filename: str) -> str:
    return filename if package_path == "." else f"{package_path}/{filename}"


def inspect_candidate(submission: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    candidate = submission["candidate"]
    revision = candidate["revision"]
    if not SHA_RE.fullmatch(revision):
        raise ValueError("Candidate revision must be a full 40-character commit SHA")

    api = HfApi()
    info = api.repo_info(
        repo_id=candidate["repo_id"],
        repo_type="dataset",
        revision=revision,
        files_metadata=True,
    )
    if info.sha != revision:
        raise ValueError(f"Revision resolved to {info.sha}, not the submitted SHA")

    package_path = candidate["path"]
    prefix = "" if package_path == "." else package_path + "/"
    package_files: dict[str, int] = {}
    for sibling in info.siblings or []:
        name = sibling.rfilename
        if not name.startswith(prefix):
            continue
        relative = name[len(prefix):]
        if "/" in relative or not relative:
            continue
        package_files[relative] = int(sibling.size or 0)

    missing = sorted(set(REQUIRED_FILES) - set(package_files))
    extras = sorted(set(package_files) - ALLOWED_FILES)
    if missing:
        raise ValueError(f"Missing required package files: {missing}")
    if extras:
        raise ValueError(f"Unexpected top-level package files: {extras}")

    total = sum(package_files.values())
    maximum = int(policy["limits"]["max_candidate_download_bytes"])
    if total > maximum:
        raise ValueError(f"Candidate package is {total} bytes; policy limit is {maximum}")

    return {
        "repo_id": candidate["repo_id"],
        "revision": revision,
        "resolved_sha": info.sha,
        "path": package_path,
        "files": package_files,
        "total_download_bytes": total,
    }


def download_candidate(
    submission: dict[str, Any],
    destination: str | Path,
) -> Path:
    candidate = submission["candidate"]
    package_path = candidate["path"]
    patterns = [
        _join(package_path, name)
        for name in REQUIRED_FILES
    ]
    for optional in ("LICENSE", "LICENSE.txt", "LICENSE.md"):
        patterns.append(_join(package_path, optional))

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=candidate["repo_id"],
        repo_type="dataset",
        revision=candidate["revision"],
        allow_patterns=patterns,
        local_dir=destination,
    )
    return destination if package_path == "." else destination / package_path
