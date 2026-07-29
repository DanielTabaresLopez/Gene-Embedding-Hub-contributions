from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .embedding_fields import (
    package_category,
    package_modality,
    submission_category,
    submission_modality,
)
from .models import ValidationResult
from .submission import validate_document
from .util import sha256_file


def _status(condition: bool, failure: str = "FAIL") -> str:
    return "PASS" if condition else failure


def _duplicate_row_count(matrix: np.ndarray) -> int:
    seen: set[bytes] = set()
    duplicates = 0
    contiguous = np.ascontiguousarray(matrix)
    for row in contiguous:
        digest = hashlib.blake2b(memoryview(row).cast("B"), digest_size=16).digest()
        if digest in seen:
            duplicates += 1
        else:
            seen.add(digest)
    return duplicates


def validate_package(
    package_dir: str | Path,
    submission: dict[str, Any],
    policy: dict[str, Any],
    master_genes: set[str],
    metadata_schema: str | Path,
    metadata_required: bool = True,
    candidate_info: dict[str, Any] | None = None,
) -> ValidationResult:
    package_dir = Path(package_dir)
    result = ValidationResult(outcome="FAIL")

    required = [
        "embeddings.npz",
        "genes.tsv",
        "README.md",
    ]

    if metadata_required:
        required.append("metadata.json")

    for filename in required:
        exists = (package_dir / filename).is_file()
        result.add(f"file.{filename}", _status(exists), f"{filename} {'exists' if exists else 'is missing'}")
    if any(c.status == "FAIL" for c in result.checks):
        return _finish(result, policy)

    submitted_category = submission_category(
        submission
    )

    submitted_modality = submission_modality(
        submission
    )

    submitted_species = submission[
        "provenance"
    ]["species"]

    submitted_license = submission[
        "licensing"
    ]["source_license"]

    if metadata_required:
        try:
            metadata = json.loads(
                (
                    package_dir / "metadata.json"
                ).read_text(
                    encoding="utf-8"
                )
            )

            validate_document(
                metadata,
                metadata_schema,
            )

            result.add(
                "metadata.schema",
                "PASS",
                "metadata.json matches the schema",
            )

        except Exception as exc:
            result.add(
                "metadata.schema",
                "FAIL",
                str(exc),
            )

            return _finish(
                result,
                policy,
            )

        stored_category = package_category(
            metadata
        )

        stored_modality = package_modality(
            metadata
        )

        expected_pairs = {
            "embedding_id": submission[
                "embedding_id"
            ],
            "display_name": submission[
                "display_name"
            ],
            "species": submitted_species,
            "original_method": submission[
                "scientific"
            ]["original_method"],
            "model_checkpoint": submission[
                "scientific"
            ]["model_checkpoint"],
            "embedding_generated_by": submission[
                "provenance"
            ]["embedding_generated_by"],
            "input_data_source": submission[
                "provenance"
            ]["input_data_source"],
            "input_data_release": submission[
                "provenance"
            ]["input_data_release"],
            "pooling_strategy": submission[
                "provenance"
            ]["pooling_strategy"],
            "original_identifier_type": submission[
                "provenance"
            ]["identifier_before_mapping"],
            "mapping_method": submission[
                "provenance"
            ]["mapping_method"],
            "source_license": submitted_license,
            "redistribution_allowed": True,
        }

        for key, expected in expected_pairs.items():
            actual = metadata.get(key)

            result.add(
                f"metadata.consistency.{key}",
                _status(actual == expected),
                (
                    f"metadata {key} matches submission"
                    if actual == expected
                    else (
                        f"metadata {key} does not "
                        "match submission"
                    )
                ),
                {
                    "expected": expected,
                    "actual": actual,
                },
            )

        result.add(
            "metadata.consistency.category",
            _status(
                stored_category
                == submitted_category
            ),
            (
                "metadata category matches submission"
                if (
                    stored_category
                    == submitted_category
                )
                else (
                    "metadata category does not "
                    "match submission"
                )
            ),
            {
                "expected": submitted_category,
                "actual": stored_category,
            },
        )

        result.add(
            "metadata.consistency.modality",
            _status(
                stored_modality
                == submitted_modality
            ),
            (
                "metadata modality matches submission"
                if (
                    stored_modality
                    == submitted_modality
                )
                else (
                    "metadata modality does not "
                    "match submission"
                )
            ),
            {
                "expected": submitted_modality,
                "actual": stored_modality,
            },
        )

    else:
        result.add(
            "metadata.generation",
            "INFO",
            (
                "metadata.json was not supplied by the "
                "contributor and will be generated "
                "automatically after validation."
            ),
        )

    allowed_species = set(
        policy["metadata"]["allowed_species"]
    )

    allowed_licenses = {
        value.lower()
        for value in policy[
            "metadata"
        ]["allowed_licenses"]
    }

    result.add(
        "policy.species",
        _status(
            submitted_species
            in allowed_species
        ),
        "Species is allowed",
        submitted_species,
    )

    normalized_category = (
        submitted_category.strip()
    )

    valid_category = (
        submitted_category
        == normalized_category
        and 2 <= len(normalized_category) <= 80
        and all(
            character.isprintable()
            for character in submitted_category
        )
    )

    result.add(
        "policy.category",
        _status(valid_category),
        (
            "Category is a valid catalog "
            "category value"
        ),
        submitted_category,
    )

    normalized_modality = (
        submitted_modality.strip()
    )

    valid_modality = (
        submitted_modality
        == normalized_modality
        and len(normalized_modality) >= 2
        and all(
            character.isprintable()
            for character in submitted_modality
        )
    )

    result.add(
        "policy.modality",
        _status(valid_modality),
        (
            "Modality is a valid free-text "
            "description"
        ),
        submitted_modality,
    )

    result.add(
        "policy.license",
        _status(
            submitted_license.lower()
            in allowed_licenses
        ),
        "License is on the automatic allowlist",
        submitted_license,
    )

    genes = pd.read_csv(package_dir / "genes.tsv", sep="\t", dtype=str, keep_default_na=False)
    gene_column = policy["identifiers"]["required_column"]
    if gene_column not in genes.columns:
        result.add("genes.column", "FAIL", f"genes.tsv lacks required column {gene_column}")
        return _finish(result, policy)
    ids = genes[gene_column].astype(str).str.strip()
    result.add("genes.nonempty", _status(bool((ids != "").all())), "All gene identifiers are non-empty")
    result.add("genes.unique", _status(not ids.duplicated().any()), "Gene identifiers are unique", int(ids.duplicated().sum()))
    pattern = re.compile(policy["identifiers"]["ensembl_pattern"])
    valid_format = ids.map(lambda value: bool(pattern.fullmatch(value)))
    result.add("genes.format", _status(bool(valid_format.all())), "All identifiers are unversioned Ensembl gene IDs", int((~valid_format).sum()))

    in_master = ids.isin(master_genes)
    unknown_fraction = float((~in_master).mean()) if len(ids) else 1.0
    master_coverage_fraction = float(in_master.sum() / len(master_genes))
    result.add(
        "genes.unknown_fraction",
        _status(unknown_fraction <= float(policy["identifiers"]["maximum_unknown_fraction"])),
        "Unknown identifier fraction is within policy",
        unknown_fraction,
    )
    result.add(
        "genes.master_coverage",
        _status(master_coverage_fraction >= float(policy["identifiers"]["minimum_master_coverage_fraction"])),
        "Master-universe coverage is within policy",
        master_coverage_fraction,
    )
    result.add(
        "genes.count",
        _status(int(policy["limits"]["min_genes"]) <= len(ids) <= int(policy["limits"]["max_genes"])),
        "Gene count is within policy",
        len(ids),
    )

    npz_path = package_dir / "embeddings.npz"
    with zipfile.ZipFile(npz_path) as archive:
        total_uncompressed = sum(item.file_size for item in archive.infolist())
        encrypted = any(item.flag_bits & 0x1 for item in archive.infolist())
    result.add(
        "npz.uncompressed_size",
        _status(total_uncompressed <= int(policy["limits"]["max_npz_uncompressed_bytes"])),
        "NPZ uncompressed size is within policy",
        total_uncompressed,
    )
    result.add("npz.not_encrypted", _status(not encrypted), "NPZ archive is not encrypted")
    if any(c.status == "FAIL" for c in result.checks):
        return _finish(result, policy)

    with np.load(npz_path, allow_pickle=False) as archive:
        keys = list(archive.files)
        required_key = policy["matrix"]["required_key"]
        result.add("matrix.single_key", _status(keys == [required_key]), f"NPZ contains exactly the {required_key!r} array", keys)
        if required_key not in archive.files:
            return _finish(result, policy)
        matrix = np.asarray(archive[required_key])

    result.add("matrix.ndim", _status(matrix.ndim == 2), "Embedding matrix is two-dimensional", matrix.ndim)
    if matrix.ndim != 2:
        return _finish(result, policy)
    rows, dims = matrix.shape
    result.add("matrix.rows", _status(rows == len(ids)), "Matrix row count equals genes.tsv row count", {"matrix_rows": rows, "gene_rows": len(ids)})
    result.add(
        "matrix.dimensions",
        _status(int(policy["limits"]["min_dimensions"]) <= dims <= int(policy["limits"]["max_dimensions"])),
        "Embedding dimensionality is within policy",
        dims,
    )
    required_dtype = np.dtype(policy["matrix"]["required_dtype"])
    result.add("matrix.dtype", _status(matrix.dtype == required_dtype), f"Matrix dtype is {required_dtype}", str(matrix.dtype))
    result.add("matrix.numeric", _status(np.issubdtype(matrix.dtype, np.floating)), "Matrix has a floating numeric dtype", str(matrix.dtype))

    finite = np.isfinite(matrix)
    nonfinite_count = int(matrix.size - finite.sum())
    result.add("matrix.finite", _status(nonfinite_count == 0), "Matrix contains no NaN or infinite values", nonfinite_count)
    zero_rows = int(np.count_nonzero(np.linalg.norm(matrix, axis=1) == 0))
    zero_status = "FAIL" if policy["matrix"]["fail_on_zero_vectors"] else "WARNING"
    result.add("matrix.zero_vectors", _status(zero_rows == 0, zero_status), "Matrix contains no zero vectors", zero_rows)

    column_min = np.min(matrix, axis=0)
    column_max = np.max(matrix, axis=0)
    constant_columns = int(np.count_nonzero(column_min == column_max))
    constant_status = "FAIL" if policy["matrix"]["fail_on_constant_columns"] else "WARNING"
    result.add("matrix.constant_columns", _status(constant_columns == 0, constant_status), "Matrix contains no constant columns", constant_columns)

    duplicate_rows = _duplicate_row_count(matrix)
    duplicate_status = "FAIL" if policy["matrix"]["fail_on_duplicate_vectors"] else "WARNING"
    result.add("matrix.duplicate_vectors", _status(duplicate_rows == 0, duplicate_status), "Matrix contains no exact duplicate vectors", duplicate_rows)

    readme_size = (package_dir / "README.md").stat().st_size
    result.add("readme.nonempty", _status(readme_size >= 200), "README.md contains substantive documentation", readme_size)

    checksums = {name: sha256_file(package_dir / name) for name in required}
    norms = np.linalg.norm(matrix, axis=1)
    result.summary.update({
        "embedding_id": submission["embedding_id"],
        "display_name": submission["display_name"],
        "submitted_category": submitted_category,
        "submitted_modality": submitted_modality,
        "n_genes": int(rows),
        "n_dimensions": int(dims),
        "dtype": str(matrix.dtype),
        "npz_key": required_key,
        "master_genes_matched": int(in_master.sum()),
        "master_coverage_fraction": master_coverage_fraction,
        "unknown_identifier_fraction": unknown_fraction,
        "zero_vectors": zero_rows,
        "duplicate_vectors": duplicate_rows,
        "constant_columns": constant_columns,
        "value_min": float(np.min(matrix)),
        "value_max": float(np.max(matrix)),
        "norm_min": float(np.min(norms)),
        "norm_median": float(np.median(norms)),
        "norm_max": float(np.max(norms)),
        "checksums_sha256": checksums,
        "trace": make_trace(matrix),
        "trace_gene": str(ids.iloc[0]) if len(ids) else "",
    })
    if candidate_info:
        result.provenance["candidate"] = candidate_info
    result.provenance["source_license"] = submission["licensing"]["source_license"]
    return _finish(result, policy)


def make_trace(matrix: np.ndarray, bins: int = 32) -> list[float]:
    row = np.asarray(matrix[0], dtype=np.float64)
    chunks = np.array_split(row, bins)
    pooled = np.array([float(chunk.mean()) if len(chunk) else 0.0 for chunk in chunks])
    low, high = float(pooled.min()), float(pooled.max())
    if high == low:
        return [0.5] * bins
    return [round(float((value - low) / (high - low)), 6) for value in pooled]


def _finish(result: ValidationResult, policy: dict[str, Any]) -> ValidationResult:
    has_fail = any(check.status == "FAIL" for check in result.checks)
    has_warning = any(check.status == "WARNING" for check in result.checks)
    if has_fail:
        result.outcome = "FAIL"
    elif has_warning and policy["acceptance"]["warnings_are_failures"]:
        result.outcome = "FAIL"
    elif has_warning:
        result.outcome = "PASS_WITH_WARNINGS"
    else:
        result.outcome = "PASS"
    return result
