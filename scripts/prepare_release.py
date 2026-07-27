from __future__ import annotations

import argparse
import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from gene_registry.hf_package import download_candidate
from gene_registry.service import run_validation
from gene_registry.submission import load_and_validate_submission
from gene_registry.util import load_yaml, write_json


def load_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    value = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(value, list):
        raise ValueError(f"Expected a JSON list in {path}")

    if not all(isinstance(entry, dict) for entry in value):
        raise ValueError(f"Expected only JSON objects in {path}")

    return value


def candidate_urls(
    repo_id: str,
    revision: str,
    candidate_path: str,
) -> tuple[str, str]:
    base = f"https://huggingface.co/datasets/{repo_id}"

    normalized_path = candidate_path.strip("/")

    if normalized_path in ("", "."):
        return (
            f"{base}/tree/{revision}",
            f"{base}/blob/{revision}/metadata.json",
        )

    encoded_path = quote(normalized_path, safe="/")

    return (
        f"{base}/tree/{revision}/{encoded_path}",
        f"{base}/blob/{revision}/{encoded_path}/metadata.json",
    )


def manifest_columns(
    registry: list[dict[str, Any]],
    preferred: list[str],
) -> list[str]:
    known = set(preferred)

    additional = sorted(
        {
            key
            for row in registry
            for key in row
            if key not in known
        }
    )

    return preferred + additional


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--submission", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--master-genes", required=True)
    parser.add_argument("--schema-dir", required=True)
    parser.add_argument("--space-source", required=True)
    parser.add_argument("--existing-registry", required=True)
    parser.add_argument("--existing-catalog", required=True)
    parser.add_argument("--output-dir", required=True)

    args = parser.parse_args()

    project = load_yaml(args.project)

    storage_mode = project.get(
        "community_storage_mode",
        "external_reference",
    )

    if storage_mode != "external_reference":
        raise ValueError(
            "This workflow supports only external_reference storage; "
            f"received {storage_mode!r}"
        )

    submission = load_and_validate_submission(
        args.submission,
        Path(args.schema_dir) / "submission.schema.json",
    )

    embedding_id = submission["embedding_id"]
    candidate = submission["candidate"]

    candidate_repo = candidate["repo_id"]
    candidate_repo_type = candidate["repo_type"]
    candidate_revision = candidate["revision"]
    candidate_path = candidate["path"]

    if candidate_repo_type != "dataset":
        raise ValueError(
            "Community candidates must use a Hugging Face Dataset."
        )

    package_url, metadata_url = candidate_urls(
        repo_id=candidate_repo,
        revision=candidate_revision,
        candidate_path=candidate_path,
    )

    output = Path(args.output_dir)

    if output.exists():
        shutil.rmtree(output)

    (output / "dataset").mkdir(parents=True)
    (output / "space").mkdir(parents=True)

    with tempfile.TemporaryDirectory(
        prefix="candidate-release-"
    ) as temporary_directory:
        temporary_path = Path(temporary_directory)

        package_dir = download_candidate(
            submission,
            temporary_path / "candidate",
        )

        validation_dir = temporary_path / "validation"

        result = run_validation(
            submission_path=args.submission,
            policy_path=args.policy,
            master_genes_path=args.master_genes,
            schema_dir=args.schema_dir,
            output_dir=validation_dir,
            package_dir=package_dir,
        )

        if result.outcome != "PASS":
            raise SystemExit(
                "Refusing to publish a candidate without a strict PASS"
            )

        checksum = result.summary[
            "checksums_sha256"
        ]["embeddings.npz"]

        validation_root_relative = project[
            "dataset_validation_root"
        ].strip("/")

        validation_root = (
            output
            / "dataset"
            / validation_root_relative
            / embedding_id
        )

        validation_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            validation_dir / "validation_report.json",
            validation_root / "validation_report.json",
        )

        shutil.copy2(
            validation_dir / "validation_summary.md",
            validation_root / "validation_summary.md",
        )

        shutil.copy2(
            args.submission,
            validation_root / "submission.yaml",
        )

        source_reference = {
            "embedding_id": embedding_id,
            "contributor_name": submission["contributor"]["name"],
            "contributor_affiliation": submission[
                "contributor"
            ]["affiliation"],
            "storage_mode": storage_mode,
            "repo_id": candidate_repo,
            "repo_type": candidate_repo_type,
            "revision": candidate_revision,
            "path": candidate_path,
            "package_url": package_url,
            "metadata_url": metadata_url,
            "embeddings_sha256": checksum,
            "validation_outcome": result.outcome,
            "availability_status": "available_at_acceptance",
        }

        write_json(
            validation_root / "source_reference.json",
            source_reference,
        )

        registry = load_list(
            Path(args.existing_registry)
        )

        if any(
            entry.get("embedding_id") == embedding_id
            for entry in registry
        ):
            raise SystemExit(
                "Embedding ID already exists in community registry: "
                f"{embedding_id}"
            )

        if any(
            entry.get("embeddings_sha256") == checksum
            for entry in registry
        ):
            raise SystemExit(
                "An exact embeddings.npz checksum is already registered"
            )

        registry_entry = {
            "embedding_id": embedding_id,
            "display_name": submission["display_name"],
            "contributor_name": submission["contributor"]["name"],
            "contributor_affiliation": submission[
                "contributor"
            ]["affiliation"],
            "candidate_repo": candidate_repo,
            "candidate_repo_type": candidate_repo_type,
            "candidate_revision": candidate_revision,
            "candidate_path": candidate_path,
            "broad_modality": submission[
                "scientific"
            ]["broad_modality"],
            "detailed_modality": submission[
                "scientific"
            ]["detailed_modality"],
            "n_genes": result.summary["n_genes"],
            "n_dimensions": result.summary["n_dimensions"],
            "master_coverage_fraction": result.summary[
                "master_coverage_fraction"
            ],
            "source_license": submission[
                "licensing"
            ]["source_license"],
            "embeddings_sha256": checksum,
            "storage_mode": storage_mode,
            "package_url": package_url,
            "metadata_url": metadata_url,
            "validation_path": (
                f"{validation_root_relative}/{embedding_id}"
            ),
            "availability_status": "available_at_acceptance",
            "validation_outcome": result.outcome,
        }

        registry.append(registry_entry)
        registry.sort(
            key=lambda item: item["embedding_id"]
        )

        registry_target = (
            output
            / "dataset"
            / project["dataset_registry_file"]
        )

        write_json(registry_target, registry)

        manifest_target = (
            output
            / "dataset"
            / project["dataset_community_manifest_file"]
        )

        manifest_target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        columns = manifest_columns(
            registry,
            list(registry_entry),
        )

        with manifest_target.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=columns,
            )

            writer.writeheader()

            for row in registry:
                writer.writerow(
                    {
                        column: row.get(column, "")
                        for column in columns
                    }
                )

        catalog = load_list(
            Path(args.existing_catalog)
        )

        if any(
            item.get("id") == embedding_id
            for item in catalog
        ):
            raise SystemExit(
                "Embedding ID already exists in Space catalog: "
                f"{embedding_id}"
            )

        catalog.append(
            {
                "id": embedding_id,
                "name": submission["display_name"],
                "contributor_name": submission["contributor"]["name"],
                "contributor_affiliation": submission[
                    "contributor"
                ]["affiliation"],
                "category": submission[
                    "scientific"
                ]["broad_modality"],
                "category_source": "community_submission",
                "modality": submission[
                    "scientific"
                ]["detailed_modality"],
                "algorithm": submission[
                    "scientific"
                ]["original_method"],
                "description": submission[
                    "scientific"
                ]["description"],
                "n_genes": result.summary["n_genes"],
                "n_dims": result.summary["n_dimensions"],
                "coverage_pct": round(
                    100
                    * result.summary[
                        "master_coverage_fraction"
                    ],
                    1,
                ),
                "trace": result.summary["trace"],
                "trace_gene": result.summary["trace_gene"],
                "qc_status": "AUTO_PASS",
                "license": submission[
                    "licensing"
                ]["source_license"],
                "dataset_path": candidate_path,
                "package_url": package_url,
                "metadata_url": metadata_url,
                "source_dataset": candidate_repo,
                "source_revision": candidate_revision,
                "source_repo_type": candidate_repo_type,
                "storage_mode": storage_mode,
                "availability_status": (
                    "available_at_acceptance"
                ),
                "validation_path": (
                    f"{validation_root_relative}/{embedding_id}"
                ),
                "community_contribution": True,
            }
        )

        catalog.sort(
            key=lambda item: item["name"].casefold()
        )

        shutil.copytree(
            args.space_source,
            output / "space",
            dirs_exist_ok=True,
        )

        write_json(
            output
            / "space"
            / project["space_catalog_file"],
            catalog,
        )

        community_count = sum(
            item.get("community_contribution") is True
            for item in catalog
        )

        write_json(
            output / "space" / "release_summary.json",
            {
                "catalog_count": len(catalog),
                "community_registry_count": len(registry),
                "community_catalog_count": community_count,
                "latest_embedding_id": embedding_id,
            },
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
