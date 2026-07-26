from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from huggingface_hub import HfApi, hf_hub_download


PACKAGE_ROOT = "data/embeddings/"
MASTER_GENE_COUNT_DEFAULT = 20097


def first_value(metadata: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = metadata.get(key)

        if value is None:
            continue

        if isinstance(value, str) and not value.strip():
            continue

        return value

    return None


def text_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None

    if isinstance(value, (int, float, bool)):
        return str(value)

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
    )


def integer_value(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return None

    if isinstance(value, str):
        match = re.search(r"-?\d+", value.replace(",", ""))

        if match:
            return int(match.group())

    return None


def matrix_shape(metadata: dict[str, Any]) -> tuple[int | None, int | None]:
    value = metadata.get("matrix_shape")

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return integer_value(value[0]), integer_value(value[1])

    if isinstance(value, str):
        numbers = [
            int(item)
            for item in re.findall(r"\d+", value)
        ]

        if len(numbers) >= 2:
            return numbers[0], numbers[1]

    return None, None


def normalize_percentage(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, str):
        cleaned = value.strip().replace("%", "")

        try:
            number = float(cleaned)
        except ValueError:
            return None
    else:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None

    if number < 0:
        return None

    if number <= 1:
        number *= 100

    return round(number, 2)



def zero_vector_count(metadata: dict[str, Any]) -> int | None:
    """Extract a zero-vector count from legacy and current metadata formats."""
    direct = integer_value(
        first_value(
            metadata,
            "zero_vectors",
            "n_zero_vectors",
        )
    )

    if direct is not None:
        return direct

    all_zero_rows = metadata.get("all_zero_rows")

    if isinstance(all_zero_rows, dict):
        count = integer_value(all_zero_rows.get("count"))

        if count is not None:
            return count

    qc = metadata.get("qc")

    if isinstance(qc, dict):
        count = integer_value(qc.get("zero_vectors"))

        if count is not None:
            return count

    return None

def derive_category(
    embedding_id: str,
    modality: str,
    name: str,
) -> tuple[str, str]:
    combined = " ".join(
        [embedding_id, modality, name]
    ).lower()

    rules: list[tuple[str, tuple[str, ...]]] = [
        (
            "Single-cell",
            (
                "single-cell",
                "single_cell",
                "geneformer",
                "scgpt",
                "scbert",
                "uce",
            ),
        ),
        (
            "Regulatory",
            (
                "alphagenome",
                "basenji",
                "deepsea",
                "enformer",
                "spliceai",
                "regulatory",
                "epigen",
                "chromatin",
            ),
        ),
        (
            "Protein",
            (
                "protein",
                "esm",
                "protbert",
                "prott5",
                "ankh",
                "gearnet",
                "msa transformer",
                "amino acid",
            ),
        ),
        (
            "Literature",
            (
                "literature",
                "text",
                "biobert",
                "bioconceptvec",
                "pubmed",
                "biomedical_literature",
            ),
        ),
        (
            "Expression",
            (
                "expression",
                "transcriptom",
                "cmap",
                "perturbation",
            ),
        ),
        (
            "Network",
            (
                "network",
                "string",
                "ppi",
                "deepnf",
                "node2vec",
                "interaction graph",
            ),
        ),
        (
            "Knowledge",
            (
                "knowledge graph",
                "ontology",
                "pathway",
                "gene ontology",
                "kge",
            ),
        ),
        (
            "DNA",
            (
                "dna sequence",
                "nucleotide",
                "genomic sequence",
                "genome language",
            ),
        ),
    ]

    for category, keywords in rules:
        if any(keyword in combined for keyword in keywords):
            return category, "heuristic"

    return "Other", "fallback"


def load_overrides(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    value = yaml.safe_load(
        path.read_text(encoding="utf-8")
    )

    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ValueError(
            "core_catalog_overrides.yaml must contain a mapping"
        )

    normalized: dict[str, dict[str, Any]] = {}

    for embedding_id, fields in value.items():
        if not isinstance(fields, dict):
            raise ValueError(
                f"Override for {embedding_id} must be a mapping"
            )

        normalized[str(embedding_id)] = fields

    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-id",
        default="embeddingsSSRF/gene_embeddings",
    )
    parser.add_argument(
        "--revision",
        default=None,
        help="Immutable Dataset revision used for the core catalog.",
    )
    parser.add_argument(
        "--master-gene-count",
        type=int,
        default=MASTER_GENE_COUNT_DEFAULT,
    )
    parser.add_argument(
        "--overrides",
        default="config/core_catalog_overrides.yaml",
    )
    parser.add_argument(
        "--output",
        default="space/catalog.json",
    )
    parser.add_argument(
        "--report",
        default="reports/core_catalog_build.json",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=68,
    )

    args = parser.parse_args()

    api = HfApi()

    repo_info = api.repo_info(
        repo_id=args.dataset_id,
        repo_type="dataset",
        revision=args.revision,
    )

    revision = args.revision or repo_info.sha

    files = sorted(
        api.list_repo_files(
            repo_id=args.dataset_id,
            repo_type="dataset",
            revision=revision,
        )
    )

    metadata_paths = [
        path
        for path in files
        if path.startswith(PACKAGE_ROOT)
        and path.endswith("/metadata.json")
    ]

    overrides = load_overrides(
        Path(args.overrides)
    )

    catalog: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    duplicate_ids: list[str] = []
    seen_ids: set[str] = set()

    for metadata_path in metadata_paths:
        relative = metadata_path[len(PACKAGE_ROOT):]
        folder_id = relative.split("/", maxsplit=1)[0]

        local_metadata = Path(
            hf_hub_download(
                repo_id=args.dataset_id,
                repo_type="dataset",
                revision=revision,
                filename=metadata_path,
            )
        )

        metadata = json.loads(
            local_metadata.read_text(encoding="utf-8")
        )

        if not isinstance(metadata, dict):
            raise ValueError(
                f"{metadata_path} does not contain a JSON object"
            )

        embedding_id = text_value(
            first_value(
                metadata,
                "embedding_id",
                "id",
            )
        ) or folder_id

        if embedding_id in seen_ids:
            duplicate_ids.append(embedding_id)

        seen_ids.add(embedding_id)

        name = text_value(
            first_value(
                metadata,
                "embedding_name",
                "display_name",
                "name",
            )
        ) or embedding_id

        modality = text_value(
            first_value(
                metadata,
                "modality",
                "detailed_modality",
                "input_sequence_type",
            )
        ) or "not specified"

        shape_rows, shape_dims = matrix_shape(metadata)

        n_genes = integer_value(
            first_value(
                metadata,
                "num_genes",
                "n_covered_genes",
                "n_mapped_genes",
                "mapped_genes",
                "n_valid_tss_windows",
                "n_master_rows",
                "master_rows",
            )
        )

        if n_genes is None:
            n_genes = shape_rows

        n_dims = integer_value(
            first_value(
                metadata,
                "embedding_dimension",
                "embedding_dim",
                "dimension",
                "n_pca_components",
            )
        )

        if n_dims is None:
            n_dims = shape_dims

        coverage_pct = normalize_percentage(
            first_value(
                metadata,
                "coverage_pct",
                "master_coverage",
                "coverage_of_master_rows",
                "coverage",
            )
        )

        if (
            coverage_pct is None
            and n_genes is not None
            and args.master_gene_count > 0
        ):
            coverage_pct = round(
                100 * n_genes / args.master_gene_count,
                2,
            )

        category, category_source = derive_category(
            embedding_id=embedding_id,
            modality=modality,
            name=name,
        )

        algorithm = text_value(
            first_value(
                metadata,
                "original_method",
                "model_checkpoint",
                "model",
                "transform",
                "transformation",
                "pooled_representation",
                "pooling_strategy",
            )
        ) or "see package metadata"

        description = text_value(
            first_value(
                metadata,
                "description",
                "summary",
                "original_text_source",
            )
        )

        if description is None:
            description = (
                f"{name}. Core embedding package from "
                f"{args.dataset_id}."
            )

        qc_status = text_value(
            first_value(
                metadata,
                "status",
                "qc_status",
            )
        ) or "legacy_core_package"

        source_license = text_value(
            first_value(
                metadata,
                "source_license",
                "license",
            )
        ) or "not recorded in package metadata"

        zero_vectors = zero_vector_count(metadata)

        package_path = (
            f"{PACKAGE_ROOT}{folder_id}"
        )

        entry: dict[str, Any] = {
            "id": embedding_id,
            "name": name,
            "category": category,
            "category_source": category_source,
            "modality": modality,
            "algorithm": algorithm,
            "description": description,
            "n_genes": n_genes,
            "n_dims": n_dims,
            "coverage_pct": coverage_pct,
            "qc_status": qc_status,
            "license": source_license,
            "zero_vectors": zero_vectors,
            "dataset_path": package_path,
            "package_url": (
                "https://huggingface.co/datasets/"
                f"{args.dataset_id}/tree/{revision}/"
                f"{package_path}"
            ),
            "metadata_url": (
                "https://huggingface.co/datasets/"
                f"{args.dataset_id}/blob/{revision}/"
                f"{metadata_path}"
            ),
            "source_dataset": args.dataset_id,
            "source_revision": revision,
            "community_contribution": False,
        }

        entry.update(
            overrides.get(embedding_id, {})
        )

        missing_fields = [
            field
            for field in (
                "id",
                "name",
                "n_genes",
                "n_dims",
                "coverage_pct",
            )
            if entry.get(field) is None
        ]

        if missing_fields:
            unresolved.append(
                {
                    "embedding_id": embedding_id,
                    "metadata_path": metadata_path,
                    "missing_fields": missing_fields,
                }
            )

        catalog.append(entry)

    catalog.sort(
        key=lambda item: (
            str(item["name"]).casefold(),
            str(item["id"]).casefold(),
        )
    )

    report = {
        "dataset_id": args.dataset_id,
        "dataset_revision": revision,
        "metadata_file_count": len(metadata_paths),
        "catalog_entry_count": len(catalog),
        "duplicate_ids": duplicate_ids,
        "unresolved_entries": unresolved,
        "category_counts": dict(
            sorted(
                Counter(
                    item["category"]
                    for item in catalog
                ).items()
            )
        ),
        "heuristic_category_count": sum(
            item.get("category_source") == "heuristic"
            for item in catalog
        ),
        "fallback_category_count": sum(
            item.get("category_source") == "fallback"
            for item in catalog
        ),
    }

    output_path = Path(args.output)
    report_path = Path(args.report)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            catalog,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print("Dataset:", args.dataset_id)
    print("Revision:", revision)
    print("Metadata files:", len(metadata_paths))
    print("Catalog entries:", len(catalog))
    print("Duplicate IDs:", len(duplicate_ids))
    print("Unresolved entries:", len(unresolved))
    print("Fallback categories:", report["fallback_category_count"])

    print("\nCategory counts:")

    for category, count in report["category_counts"].items():
        print(f" - {category}: {count}")

    print("\nCatalog written to:", output_path)
    print("Report written to:", report_path)

    if len(catalog) != args.expected_count:
        print(
            f"\nERROR: expected {args.expected_count} entries, "
            f"found {len(catalog)}"
        )
        return 2

    if duplicate_ids:
        print("\nERROR: duplicate embedding IDs detected")
        return 2

    if unresolved:
        print("\nERROR: unresolved required fields detected")

        for item in unresolved:
            print(
                f" - {item['embedding_id']}: "
                f"{', '.join(item['missing_fields'])}"
            )

        return 2

    print("\nCore catalog build: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
