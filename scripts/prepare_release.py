from __future__ import annotations

import argparse
import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from huggingface_hub import hf_hub_download

from gene_registry.hf_package import download_candidate
from gene_registry.service import run_validation
from gene_registry.submission import load_and_validate_submission
from gene_registry.util import load_yaml, write_json


def download_optional(repo_id: str, repo_type: str, filename: str, destination: Path) -> Path | None:
    try:
        return Path(hf_hub_download(repo_id=repo_id, repo_type=repo_type, filename=filename, local_dir=destination))
    except Exception:
        return None


def load_list(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--master-genes", required=True)
    parser.add_argument("--schema-dir", required=True)
    parser.add_argument("--space-source", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    project = load_yaml(args.project)
    submission = load_and_validate_submission(args.submission, Path(args.schema_dir) / "submission.schema.json")
    embedding_id = submission["embedding_id"]
    output = Path(args.output_dir)
    if output.exists():
        shutil.rmtree(output)
    (output / "dataset").mkdir(parents=True)
    (output / "space").mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="candidate-release-") as temp:
        temp_path = Path(temp)
        package_dir = download_candidate(submission, temp_path / "candidate")
        validation_dir = temp_path / "validation"
        result = run_validation(
            submission_path=args.submission,
            policy_path=args.policy,
            master_genes_path=args.master_genes,
            schema_dir=args.schema_dir,
            output_dir=validation_dir,
            package_dir=package_dir,
        )
        if result.outcome != "PASS":
            raise SystemExit("Refusing to publish a candidate that does not have a strict PASS")

        package_root = output / "dataset" / project["dataset_package_root"] / embedding_id
        shutil.copytree(package_dir, package_root)
        shutil.copy2(validation_dir / "validation_report.json", package_root / "validation_report.json")
        shutil.copy2(validation_dir / "validation_summary.md", package_root / "validation_summary.md")

        remote = temp_path / "remote"
        registry_path = download_optional(
            project["hf_dataset_id"], "dataset", project["dataset_registry_file"], remote
        )
        registry = load_list(registry_path)
        if any(entry.get("embedding_id") == embedding_id for entry in registry):
            raise SystemExit(f"Embedding ID already exists in community registry: {embedding_id}")
        checksum = result.summary["checksums_sha256"]["embeddings.npz"]
        if any(entry.get("embeddings_sha256") == checksum for entry in registry):
            raise SystemExit("An exact embeddings.npz checksum is already registered")

        registry_entry = {
            "embedding_id": embedding_id,
            "display_name": submission["display_name"],
            "candidate_repo": submission["candidate"]["repo_id"],
            "candidate_revision": submission["candidate"]["revision"],
            "candidate_path": submission["candidate"]["path"],
            "broad_modality": submission["scientific"]["broad_modality"],
            "detailed_modality": submission["scientific"]["detailed_modality"],
            "n_genes": result.summary["n_genes"],
            "n_dimensions": result.summary["n_dimensions"],
            "master_coverage_fraction": result.summary["master_coverage_fraction"],
            "source_license": submission["licensing"]["source_license"],
            "embeddings_sha256": checksum,
            "package_path": f"{project['dataset_package_root']}/{embedding_id}",
            "validation_outcome": result.outcome,
        }
        registry.append(registry_entry)
        registry.sort(key=lambda item: item["embedding_id"])
        registry_target = output / "dataset" / project["dataset_registry_file"]
        write_json(registry_target, registry)

        manifest_target = output / "dataset" / project["dataset_community_manifest_file"]
        manifest_target.parent.mkdir(parents=True, exist_ok=True)
        columns = list(registry_entry)
        with manifest_target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in registry:
                writer.writerow({column: row.get(column, "") for column in columns})

        catalog_path = download_optional(
            project["hf_space_id"], "space", project["space_catalog_file"], remote
        )
        catalog = load_list(catalog_path)
        if any(item.get("id") == embedding_id for item in catalog):
            raise SystemExit(f"Embedding ID already exists in Space catalog: {embedding_id}")
        catalog.append({
            "id": embedding_id,
            "name": submission["display_name"],
            "category": submission["scientific"]["broad_modality"],
            "modality": submission["scientific"]["detailed_modality"],
            "algorithm": submission["scientific"]["original_method"],
            "description": submission["scientific"]["description"],
            "n_genes": result.summary["n_genes"],
            "n_dims": result.summary["n_dimensions"],
            "coverage_pct": round(100 * result.summary["master_coverage_fraction"], 1),
            "trace": result.summary["trace"],
            "trace_gene": result.summary["trace_gene"],
            "qc_status": "AUTO_PASS",
            "license": submission["licensing"]["source_license"],
            "dataset_path": f"{project['dataset_package_root']}/{embedding_id}",
            "community_contribution": True,
        })
        catalog.sort(key=lambda item: item["name"].casefold())

        shutil.copytree(args.space_source, output / "space", dirs_exist_ok=True)
        write_json(output / "space" / project["space_catalog_file"], catalog)
        write_json(output / "space" / "release_summary.json", {
            "catalog_count": len(catalog),
            "community_registry_count": len(registry),
            "latest_embedding_id": embedding_id,
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
