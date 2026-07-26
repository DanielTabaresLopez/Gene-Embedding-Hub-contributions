from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from gene_registry.service import run_validation


def make_package(tmp_path: Path, zero_vector: bool = False) -> tuple[Path, Path, Path]:
    package = tmp_path / "package"
    package.mkdir()
    master = [f"ENSG{i:011d}" for i in range(1, 1501)]
    matrix = np.empty((1500, 4), dtype=np.float32)
    matrix[:, 0] = np.arange(1500, dtype=np.float32) + 1
    matrix[:, 1] = np.arange(1500, dtype=np.float32)
    matrix[:, 2] = np.arange(1500, dtype=np.float32) ** 2
    matrix[:, 3] = np.arange(1500, dtype=np.float32) % 7
    if zero_vector:
        matrix[0] = 0
    np.savez_compressed(package / "embeddings.npz", embeddings=matrix)
    pd.DataFrame({"ensembl_gene_id": master}).to_csv(package / "genes.tsv", sep="\t", index=False)
    metadata = {
        "embedding_id": "test_embedding",
        "display_name": "Test Embedding",
        "species": "Homo sapiens",
        "broad_modality": "other",
        "detailed_modality": "test fixture",
        "original_method": "fixture",
        "model_checkpoint": "not-applicable",
        "embedding_generated_by": "test suite",
        "input_data_source": "synthetic",
        "input_data_release": "v1",
        "pooling_strategy": "not-applicable",
        "original_identifier_type": "Ensembl gene ID",
        "mapping_method": "direct project master mapping",
        "source_license": "cc0-1.0",
        "redistribution_allowed": True,
    }
    (package / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (package / "README.md").write_text("# Test\n\n" + "Documented test package. " * 20, encoding="utf-8")

    submission = {
        "schema_version": 1,
        "embedding_id": "test_embedding",
        "display_name": "Test Embedding",
        "candidate": {"repo_id": "owner/repo", "repo_type": "dataset", "revision": "0" * 40, "path": "."},
        "contributor": {"name": "Test User", "email": "test@example.org", "affiliation": "Test Lab"},
        "scientific": {"broad_modality": "other", "detailed_modality": "test fixture", "original_method": "fixture", "model_checkpoint": "not-applicable", "source_publication": "", "description": "A sufficiently detailed synthetic test description for automated validation."},
        "provenance": {"embedding_generated_by": "test suite", "input_data_source": "synthetic", "input_data_release": "v1", "species": "Homo sapiens", "pooling_strategy": "not-applicable", "identifier_before_mapping": "Ensembl gene ID", "mapping_method": "direct project master mapping"},
        "licensing": {"source_license": "cc0-1.0", "redistribution_allowed": True, "terms_url": "https://creativecommons.org/publicdomain/zero/1.0/"},
        "attestations": {"information_is_accurate": True, "rights_to_redistribute": True, "no_sensitive_human_data": True, "no_patient_level_data": True, "source_terms_reviewed": True, "acceptance_of_automatic_checks": True},
    }
    submission_path = tmp_path / "submission.yaml"
    submission_path.write_text(yaml.safe_dump(submission, sort_keys=False), encoding="utf-8")
    master_path = tmp_path / "master.txt"
    master_path.write_text("\n".join(master) + "\n", encoding="utf-8")
    return package, submission_path, master_path


def test_valid_local_package_passes(tmp_path: Path):
    package, submission, master = make_package(tmp_path)
    result = run_validation(submission, "config/policy.yaml", master, "schemas", tmp_path / "out", package)
    assert result.outcome == "PASS"


def test_zero_vector_fails(tmp_path: Path):
    package, submission, master = make_package(tmp_path, zero_vector=True)
    result = run_validation(submission, "config/policy.yaml", master, "schemas", tmp_path / "out", package)
    assert result.outcome == "FAIL"
    assert any(check.check_id == "matrix.zero_vectors" and check.status == "FAIL" for check in result.checks)
