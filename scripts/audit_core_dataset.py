from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, hf_hub_download


DATASET_ID = "embeddingsSSRF/gene_embeddings"

MANIFEST_CANDIDATES = (
    "data/manifest.csv",
    "manifest.csv",
)

PACKAGE_ROOT = "data/embeddings/"


def compact_value(value: Any, max_length: int = 140) -> str:
    """Return a compact representation suitable for an audit report."""
    rendered = repr(value)

    if len(rendered) > max_length:
        return rendered[: max_length - 3] + "..."

    return rendered


def find_manifest(files: set[str]) -> str | None:
    for candidate in MANIFEST_CANDIDATES:
        if candidate in files:
            return candidate

    return None


def package_id_from_path(path: str) -> str | None:
    if not path.startswith(PACKAGE_ROOT):
        return None

    relative = path[len(PACKAGE_ROOT) :]
    parts = relative.split("/", maxsplit=1)

    if len(parts) < 2 or not parts[0]:
        return None

    return parts[0]


def is_metadata_file(path: str) -> bool:
    filename = Path(path).name.lower()

    return (
        filename == "metadata.json"
        or filename.endswith("_metadata.json")
    )


def main() -> int:
    api = HfApi()

    account = api.whoami()
    print("Authenticated as:", account["name"])
    print("Dataset:", DATASET_ID)
    print()

    repo_info = api.repo_info(
        repo_id=DATASET_ID,
        repo_type="dataset",
    )

    print("Dataset revision:", repo_info.sha)

    files = set(
        api.list_repo_files(
            repo_id=DATASET_ID,
            repo_type="dataset",
            revision=repo_info.sha,
        )
    )

    print("Total repository files:", len(files))

    package_ids = sorted(
        {
            package_id
            for path in files
            if (package_id := package_id_from_path(path))
        }
    )

    metadata_files = sorted(
        path
        for path in files
        if path.startswith(PACKAGE_ROOT)
        and is_metadata_file(path)
    )

    metadata_by_package: dict[str, list[str]] = {}

    for path in metadata_files:
        package_id = package_id_from_path(path)

        if package_id is not None:
            metadata_by_package.setdefault(
                package_id,
                [],
            ).append(path)

    print("Package folders:", len(package_ids))
    print("Metadata files:", len(metadata_files))
    print()

    manifest_path = find_manifest(files)

    manifest_rows: list[dict[str, str]] = []
    manifest_columns: list[str] = []

    if manifest_path is None:
        print("Manifest: NOT FOUND")
    else:
        print("Manifest:", manifest_path)

        downloaded_manifest = Path(
            hf_hub_download(
                repo_id=DATASET_ID,
                repo_type="dataset",
                revision=repo_info.sha,
                filename=manifest_path,
            )
        )

        with downloaded_manifest.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)
            manifest_columns = list(reader.fieldnames or [])
            manifest_rows = list(reader)

        print("Manifest rows:", len(manifest_rows))
        print("Manifest columns:")

        for column in manifest_columns:
            print(" -", column)

    print()
    print("First package folders:")

    for package_id in package_ids[:10]:
        metadata_paths = metadata_by_package.get(
            package_id,
            [],
        )

        print(
            f" - {package_id}: "
            f"{len(metadata_paths)} metadata file(s)"
        )

        for metadata_path in metadata_paths:
            print("     ", metadata_path)

    print()
    print("Sample manifest rows:")

    for index, row in enumerate(
        manifest_rows[:3],
        start=1,
    ):
        print(f"Row {index}:")

        for key, value in row.items():
            print(
                f"  {key}: {compact_value(value)}"
            )

    sample_metadata: list[dict[str, Any]] = []

    print()
    print("Sample metadata structures:")

    for metadata_path in metadata_files[:5]:
        downloaded_metadata = Path(
            hf_hub_download(
                repo_id=DATASET_ID,
                repo_type="dataset",
                revision=repo_info.sha,
                filename=metadata_path,
            )
        )

        try:
            metadata = json.loads(
                downloaded_metadata.read_text(
                    encoding="utf-8",
                )
            )
        except Exception as exc:
            print(
                f" - {metadata_path}: "
                f"FAILED TO PARSE: {exc}"
            )
            continue

        if not isinstance(metadata, dict):
            print(
                f" - {metadata_path}: "
                f"top-level type is "
                f"{type(metadata).__name__}"
            )
            continue

        print(" -", metadata_path)
        print("   Keys:")

        for key in sorted(metadata):
            print("    -", key)

        selected_values = {
            key: metadata.get(key)
            for key in (
                "embedding_id",
                "display_name",
                "embedding_name",
                "name",
                "modality",
                "broad_modality",
                "detailed_modality",
                "n_genes",
                "n_dimensions",
                "embedding_dim",
                "coverage",
                "coverage_pct",
                "status",
                "qc_status",
                "source_license",
                "license",
                "original_method",
                "model_checkpoint",
            )
            if key in metadata
        }

        print("   Selected values:")

        for key, value in selected_values.items():
            print(
                f"    {key}: "
                f"{compact_value(value)}"
            )

        sample_metadata.append(
            {
                "path": metadata_path,
                "keys": sorted(metadata),
                "selected_values": selected_values,
            }
        )

    package_file_counts = Counter()

    for path in files:
        package_id = package_id_from_path(path)

        if package_id is not None:
            package_file_counts[package_id] += 1

    report = {
        "dataset_id": DATASET_ID,
        "dataset_revision": repo_info.sha,
        "total_repository_files": len(files),
        "package_folder_count": len(package_ids),
        "package_ids": package_ids,
        "metadata_file_count": len(metadata_files),
        "metadata_files": metadata_files,
        "manifest_path": manifest_path,
        "manifest_row_count": len(manifest_rows),
        "manifest_columns": manifest_columns,
        "sample_manifest_rows": manifest_rows[:3],
        "sample_metadata": sample_metadata,
        "package_file_counts": dict(
            sorted(package_file_counts.items())
        ),
    }

    output = Path("reports/core_dataset_audit.json")
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("Audit JSON written to:", output)

    print()
    print("Summary")
    print("-------")
    print("Package folders:", len(package_ids))
    print("Manifest rows:", len(manifest_rows))
    print("Metadata files:", len(metadata_files))

    if len(package_ids) != 68:
        print(
            "WARNING: expected 68 core package folders, "
            f"found {len(package_ids)}"
        )

    if manifest_rows and len(manifest_rows) != 68:
        print(
            "WARNING: expected 68 manifest rows, "
            f"found {len(manifest_rows)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
