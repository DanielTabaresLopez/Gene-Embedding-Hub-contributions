from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from gene_registry.categories import (
    resolve_catalog_category,
)
from gene_registry.embedding_fields import (
    submission_category,
    submission_modality,
)
from gene_registry.report import write_report
from gene_registry.service import run_validation
from gene_registry.submission import (
    load_and_validate_submission,
    validate_document,
)
from gene_registry.util import load_yaml, write_json


def load_list(
    path: Path,
) -> list[dict[str, Any]]:
    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(value, list):
        raise ValueError(
            f"Expected a JSON list in {path}"
        )

    if not all(
        isinstance(entry, dict)
        for entry in value
    ):
        raise ValueError(
            f"Expected only objects in {path}"
        )

    return value


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


def central_urls(
    repo_id: str,
    package_path: str,
) -> tuple[str, str]:
    encoded = quote(
        package_path,
        safe="/",
    )

    base = (
        "https://huggingface.co/datasets/"
        f"{repo_id}"
    )

    return (
        f"{base}/tree/main/{encoded}",
        f"{base}/blob/main/{encoded}/metadata.json",
    )



def build_generated_metadata(
    submission: dict[str, Any],
    result_summary: dict[str, Any],
    hf_pr_author: str,
    accepted_at: str,
) -> dict[str, Any]:
    scientific = submission["scientific"]
    provenance = submission["provenance"]
    licensing = submission["licensing"]

    metadata: dict[str, Any] = {
        "embedding_id": submission["embedding_id"],
        "display_name": submission["display_name"],
        "category": submission_category(
            submission
        ),
        "modality": submission_modality(
            submission
        ),
        "description": scientific["description"],
        "species": provenance["species"],
        "original_identifier_type": provenance[
            "identifier_before_mapping"
        ],
        "mapping_method": provenance[
            "mapping_method"
        ],
        "redistribution_allowed": licensing[
            "redistribution_allowed"
        ],
        "n_genes": result_summary["n_genes"],
        "n_dimensions": result_summary[
            "n_dimensions"
        ],
        "dtype": result_summary["dtype"],
        "npz_key": result_summary["npz_key"],
        "master_coverage_fraction": (
            result_summary[
                "master_coverage_fraction"
            ]
        ),
        "validation_outcome": "PASS",
        "accepted_at_utc": accepted_at,
        "metadata_generated_automatically": True,
    }

    optional_values = {
        "original_method": scientific.get(
            "original_method"
        ),
        "model_checkpoint": scientific.get(
            "model_checkpoint"
        ),
        "publication": scientific.get(
            "source_publication"
        ),
        "embedding_generated_by": provenance.get(
            "embedding_generated_by"
        ),
        "input_data_source": provenance.get(
            "input_data_source"
        ),
        "input_data_release": provenance.get(
            "input_data_release"
        ),
        "pooling_strategy": provenance.get(
            "pooling_strategy"
        ),
        "source_license": licensing.get(
            "source_license"
        ),
        "terms_url": licensing.get(
            "terms_url"
        ),
    }

    for key, value in optional_values.items():
        if (
            isinstance(value, str)
            and value.strip()
        ):
            metadata[key] = value.strip()

    contributor_metadata: dict[str, str] = {
        "huggingface_username": hf_pr_author,
    }

    contributor = submission.get(
        "contributor"
    )

    if isinstance(contributor, dict):
        for key in (
            "name",
            "affiliation",
        ):
            value = contributor.get(key)

            if (
                isinstance(value, str)
                and value.strip()
            ):
                contributor_metadata[key] = (
                    value.strip()
                )

    metadata["contributor"] = (
        contributor_metadata
    )

    return metadata

def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--package-dir",
        required=True,
    )
    parser.add_argument(
        "--submission",
        required=True,
    )
    parser.add_argument(
        "--project",
        required=True,
    )
    parser.add_argument(
        "--policy",
        required=True,
    )
    parser.add_argument(
        "--modalities",
        required=True,
    )
    parser.add_argument(
        "--master-genes",
        required=True,
    )
    parser.add_argument(
        "--schema-dir",
        required=True,
    )
    parser.add_argument(
        "--space-source",
        required=True,
    )
    parser.add_argument(
        "--existing-registry",
        required=True,
    )
    parser.add_argument(
        "--existing-catalog",
        required=True,
    )
    parser.add_argument(
        "--hf-pr-number",
        required=True,
        type=int,
    )
    parser.add_argument(
        "--hf-pr-author",
        required=True,
    )
    parser.add_argument(
        "--output-dir",
        required=True,
    )

    args = parser.parse_args()

    project = load_yaml(args.project)
    modalities = load_yaml(args.modalities)

    storage_mode = project.get(
        "portal_storage_mode"
    )

    if storage_mode != "central_hf_dataset":
        raise ValueError(
            "Portal storage mode must be "
            "'central_hf_dataset'."
        )

    package_dir = Path(args.package_dir)
    submission_path = Path(args.submission)
    schema_dir = Path(args.schema_dir)
    output = Path(args.output_dir)

    submission = load_and_validate_submission(
        submission_path,
        schema_dir / "portal_submission.schema.json",
    )

    embedding_id = submission["embedding_id"]

    if package_dir.name != embedding_id:
        raise ValueError(
            "The package folder name must equal embedding_id: "
            f"{package_dir.name!r} != {embedding_id!r}"
        )

    if output.exists():
        shutil.rmtree(output)

    reports_dir = output / "reports"
    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = run_validation(
        submission_path=submission_path,
        policy_path=args.policy,
        master_genes_path=args.master_genes,
        schema_dir=schema_dir,
        output_dir=reports_dir,
        package_dir=package_dir,
        submission_schema_name=(
            "portal_submission.schema.json"
        ),
        submitted_metadata_required=False,
    )

    submitted_category = submission_category(
        submission
    )

    submitted_modality = submission_modality(
        submission
    )

    catalog_category, recognized = (
        resolve_catalog_category(
            submitted_category,
            modalities,
        )
    )

    if recognized:
        result.add(
            "catalog.category",
            "PASS",
            (
                "Submitted category matched the catalog "
                f"category {catalog_category!r}."
            ),
            {
                "submitted": submitted_category,
                "published_as": catalog_category,
            },
        )
    else:
        result.add(
            "catalog.category",
            "INFO",
            (
                f"Submitted category {submitted_category!r} "
                "is not in the official category list. "
                "The embedding will be displayed under "
                f"{catalog_category!r}."
            ),
            {
                "submitted": submitted_category,
                "published_as": catalog_category,
            },
        )

    result.summary.update(
        {
            "submitted_category": (
                submitted_category
            ),
            "submitted_modality": (
                submitted_modality
            ),
            "catalog_category": catalog_category,
            "category_fallback_applied": (
                not recognized
            ),
        }
    )

    result.provenance.update(
        {
            "submission_channel": (
                "huggingface_pull_request"
            ),
            "source_hf_pr_number": args.hf_pr_number,
            "source_hf_pr_author": args.hf_pr_author,
        }
    )

    # Rewrite the report so the category decision appears.
    write_report(
        result,
        reports_dir,
    )

    if result.outcome != "PASS":
        print(
            "Portal validation outcome:",
            result.outcome,
        )
        return 2

    registry = load_list(
        Path(args.existing_registry)
    )

    catalog = load_list(
        Path(args.existing_catalog)
    )

    checksum = result.summary[
        "checksums_sha256"
    ]["embeddings.npz"]

    if any(
        entry.get("embedding_id") == embedding_id
        for entry in registry
    ):
        raise ValueError(
            "Embedding ID already exists in registry: "
            f"{embedding_id}"
        )

    if any(
        entry.get("embeddings_sha256") == checksum
        for entry in registry
    ):
        raise ValueError(
            "The exact embeddings.npz checksum "
            "is already registered."
        )

    if any(
        entry.get("id") == embedding_id
        for entry in catalog
    ):
        raise ValueError(
            "Embedding ID already exists in catalog: "
            f"{embedding_id}"
        )

    package_path = (
        f"{project['dataset_package_root'].strip('/')}/"
        f"{embedding_id}"
    )

    dataset_payload = output / "dataset"
    space_payload = output / "space"

    package_target = (
        dataset_payload / package_path
    )

    package_target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # The downloaded PR package is no longer needed separately
    # after validation, so moving it avoids a second local copy.
    shutil.move(
        str(package_dir),
        str(package_target),
    )

    shutil.copy2(
        reports_dir / "validation_report.json",
        package_target / "validation_report.json",
    )

    shutil.copy2(
        reports_dir / "validation_summary.md",
        package_target / "validation_summary.md",
    )

    package_url, metadata_url = central_urls(
        project["hf_dataset_id"],
        package_path,
    )

    accepted_at = datetime.now(
        timezone.utc
    ).isoformat()

    generated_metadata = build_generated_metadata(
        submission=submission,
        result_summary=result.summary,
        hf_pr_author=args.hf_pr_author,
        accepted_at=accepted_at,
    )

    validate_document(
        generated_metadata,
        schema_dir / "metadata.schema.json",
    )

    write_json(
        package_target / "metadata.json",
        generated_metadata,
    )

    contributor = submission.get(
        "contributor"
    )

    if not isinstance(contributor, dict):
        contributor = {}

    contributor_name = (
        contributor.get("name")
        or args.hf_pr_author
    )

    contributor_affiliation = (
        contributor.get("affiliation")
        or "Not provided"
    )

    source_license = (
        submission["licensing"].get(
            "source_license"
        )
        or ""
    )

    catalog_license = (
        source_license
        or "Not provided"
    )

    catalog_algorithm = (
        submission["scientific"].get(
            "original_method"
        )
        or "Not provided"
    )

    pr_url = (
        "https://huggingface.co/datasets/"
        f"{project['hf_submission_dataset_id']}"
        f"/discussions/{args.hf_pr_number}"
    )

    source_reference = {
        "embedding_id": embedding_id,
        "submission_channel": (
            "huggingface_pull_request"
        ),
        "source_dataset": project["hf_submission_dataset_id"],
        "source_revision": (
            f"refs/pr/{args.hf_pr_number}"
        ),
        "source_pr_number": args.hf_pr_number,
        "source_pr_author": args.hf_pr_author,
        "source_pr_url": pr_url,
        "central_dataset": project["hf_dataset_id"],
        "central_package_path": package_path,
        "central_package_url": package_url,
        "embeddings_sha256": checksum,
        "storage_mode": storage_mode,
        "validation_outcome": result.outcome,
        "accepted_at_utc": accepted_at,
    }

    write_json(
        package_target / "source_reference.json",
        source_reference,
    )

    registry_entry = {
        "embedding_id": embedding_id,
        "display_name": submission["display_name"],
        "contributor_name": contributor_name,
        "contributor_affiliation": (
            contributor_affiliation
        ),
        "contributor_hf_username": (
            args.hf_pr_author
        ),
        "submission_channel": (
            "huggingface_pull_request"
        ),
        "source_pr_number": args.hf_pr_number,
        "submitted_category": (
            submitted_category
        ),
        "submitted_modality": (
            submitted_modality
        ),
        "catalog_category": catalog_category,
        "category_fallback_applied": (
            not recognized
        ),
        "modality": submitted_modality,
        "n_genes": result.summary["n_genes"],
        "n_dimensions": result.summary[
            "n_dimensions"
        ],
        "master_coverage_fraction": result.summary[
            "master_coverage_fraction"
        ],
        "source_license": source_license,
        "embeddings_sha256": checksum,
        "storage_mode": storage_mode,
        "package_path": package_path,
        "package_url": package_url,
        "metadata_url": metadata_url,
        "validation_path": package_path,
        "availability_status": "centrally_archived",
        "validation_outcome": result.outcome,
        "accepted_at_utc": accepted_at,
    }

    registry.append(registry_entry)

    registry.sort(
        key=lambda entry: entry["embedding_id"]
    )

    registry_target = (
        dataset_payload
        / project["dataset_registry_file"]
    )

    write_json(
        registry_target,
        registry,
    )

    manifest_target = (
        dataset_payload
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

        for entry in registry:
            writer.writerow(
                {
                    column: entry.get(column, "")
                    for column in columns
                }
            )

    catalog.append(
        {
            "id": embedding_id,
            "name": submission["display_name"],
            "contributor_name": contributor_name,
            "contributor_affiliation": (
                contributor_affiliation
            ),
            "contributor_hf_username": (
                args.hf_pr_author
            ),
            "category": catalog_category,
            "category_source": (
                "community_submission"
                if recognized
                else "fallback_other"
            ),
            "submitted_category": (
                submitted_category
            ),
            "modality": submitted_modality,
            "algorithm": catalog_algorithm,
            "description": submission[
                "scientific"
            ]["description"],
            "n_genes": result.summary["n_genes"],
            "n_dims": result.summary[
                "n_dimensions"
            ],
            "coverage_pct": round(
                100
                * result.summary[
                    "master_coverage_fraction"
                ],
                1,
            ),
            "trace": result.summary["trace"],
            "trace_gene": result.summary[
                "trace_gene"
            ],
            "qc_status": "AUTO_PASS",
            "license": catalog_license,
            "dataset_path": package_path,
            "package_url": package_url,
            "metadata_url": metadata_url,
            "source_dataset": project[
                "hf_dataset_id"
            ],
            "source_revision": "main",
            "source_repo_type": "dataset",
            "storage_mode": storage_mode,
            "availability_status": (
                "centrally_archived"
            ),
            "validation_path": package_path,
            "community_contribution": True,
        }
    )

    catalog.sort(
        key=lambda entry: entry["name"].casefold()
    )

    shutil.copytree(
        args.space_source,
        space_payload,
        dirs_exist_ok=True,
    )

    write_json(
        space_payload
        / project["space_catalog_file"],
        catalog,
    )

    community_count = sum(
        entry.get("community_contribution") is True
        for entry in catalog
    )

    write_json(
        space_payload / "release_summary.json",
        {
            "catalog_count": len(catalog),
            "community_registry_count": len(registry),
            "community_catalog_count": community_count,
            "latest_embedding_id": embedding_id,
            "latest_hf_pr_number": args.hf_pr_number,
        },
    )

    write_json(
        reports_dir / "portal_release.json",
        {
            "embedding_id": embedding_id,
            "catalog_category": catalog_category,
            "category_fallback_applied": (
                not recognized
            ),
            "package_path": package_path,
            "package_url": package_url,
            "validation_outcome": result.outcome,
        },
    )

    print("Portal release preparation: PASS")
    print("Embedding ID:", embedding_id)
    print("Catalog category:", catalog_category)
    print("Central package path:", package_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
