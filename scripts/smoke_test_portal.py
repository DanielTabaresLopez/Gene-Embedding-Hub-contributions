"""Local mock submission. This script has no upload or discussion-writing calls."""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import yaml
from gene_registry.submission import validate_document
from gene_registry.util import write_json
from scripts.prepare_portal_release import prepare


def make_mock_package(root, embedding_id="geh_mock_submission", advisory=True):
    package = Path(root) / embedding_id
    package.mkdir(parents=True)
    genes = Path("reference/master_gene_ids.txt").read_text().splitlines()[:1500]
    matrix = np.random.default_rng(20261021).normal(size=(len(genes), 16)).astype("float32")
    if advisory:
        matrix[:, 0] = 1
        matrix[1] = matrix[0]
    np.savez_compressed(package / "embeddings.npz", embeddings=matrix)
    (package / "genes.tsv").write_text("ensembl_gene_id\n" + "\n".join(genes) + "\n")
    (package / "README.md").write_text(
        "# Local synthetic contribution test\n\n"
        "This package contains deterministic synthetic vectors for testing the "
        "Gene Embedding Hub contribution pipeline. It has no biological meaning "
        "and must not be published in the production catalogue. "
        "Its repeated vectors and constant feature test the advisory numerical checks.\n"
    )
    doc = yaml.safe_load(Path("portal_template/submission.yaml").read_text())
    doc.update(embedding_id=embedding_id, display_name="Synthetic local test")
    doc["scientific"].update(category="Functional", modality="Synthetic test features",
                              description="Synthetic vectors used only to verify local contribution validation and release preparation.")
    doc["provenance"].update(identifier_before_mapping="Ensembl gene ID",
                             mapping_method="Direct selection from the provided master Ensembl gene list for a synthetic test.")
    (package / "submission.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    return package


def release_args(package, registry, catalog, output):
    return SimpleNamespace(
        package_dir=str(package), submission=str(package / "submission.yaml"),
        project="config/project.yaml", policy="config/policy.yaml",
        modalities="config/modalities.yaml", master_genes="reference/master_gene_ids.txt",
        schema_dir="schemas", space_source="space", existing_registry=str(registry),
        existing_catalog=str(catalog), hf_pr_number=999999, hf_pr_author="local-mock",
        hf_pr_revision="a" * 40, output_dir=str(output),
    )


def smoke(output):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    package = make_mock_package(root / "inputs")
    registry = root / "registry.json"
    write_json(registry, [])
    baseline = json.loads(Path("space/catalog.json").read_text())
    release = root / "release"
    args = release_args(package, registry, Path("space/catalog.json"), release)
    assert prepare(args) == 0
    catalog = json.loads((release / "space/catalog.json").read_text())
    published = {row["id"]: row for row in catalog}
    assert all(published[row["id"]] == row for row in baseline)
    assert len(catalog) == len(baseline) + 1
    assert published[package.name]["category"] == "Functional"
    assert {p.name for p in (release / "space").iterdir()} == {"catalog.json", "release_summary.json"}
    target = release / "dataset/data/community_contributions" / package.name
    metadata = json.loads((target / "metadata.json").read_text())
    validate_document(metadata, "schemas/metadata.schema.json")
    assert metadata["n_genes"] == 1500 and metadata["n_dimensions"] == 16
    report = json.loads((release / "reports/validation_report.json").read_text())
    advisory = {c["check_id"]: c for c in report["checks"]}
    assert advisory["matrix.duplicate_vectors"]["status"] == "INFO"
    assert advisory["matrix.constant_columns"]["status"] == "INFO"
    # Simulate Dataset publication succeeding and Space publication failing.
    current_registry = release / "dataset/data/community_contributions/community_registry.json"
    resume = root / "resumed-release"
    assert prepare(release_args(package, current_registry, Path("space/catalog.json"), resume)) == 0
    resumed = json.loads((resume / "space/catalog.json").read_text())
    assert resumed == catalog
    resumed_registry = json.loads((resume / "dataset/data/community_contributions/community_registry.json").read_text())
    assert len(resumed_registry) == 1
    # A retry after both uploads succeeded (for example, feedback failed) is also safe.
    completed_retry = root / "completed-retry"
    assert prepare(release_args(package, current_registry, release / "space/catalog.json", completed_retry)) == 0
    assert json.loads((completed_retry / "space/catalog.json").read_text()) == catalog
    # Invalid data must still be rejected and produce an actionable report.
    invalid_package = root / "invalid-inputs" / package.name
    shutil.copytree(package, invalid_package)
    with np.load(invalid_package / "embeddings.npz", allow_pickle=False) as loaded:
        matrix = loaded["embeddings"].copy()
    matrix[0, 0] = np.nan
    np.savez_compressed(invalid_package / "embeddings.npz", embeddings=matrix)
    rejected = root / "rejected-release"
    assert prepare(release_args(invalid_package, registry, Path("space/catalog.json"), rejected)) == 2
    assert not (rejected / "dataset").exists() and not (rejected / "space").exists()
    rejection = json.loads((rejected / "reports/validation_report.json").read_text())
    assert any(c["check_id"] == "matrix.finite" and c["status"] == "FAIL" for c in rejection["checks"])
    summary = {
        "scope": "offline_mock_no_remote_writes", "passed": True,
        "existing_catalog_entries_preserved": len(baseline),
        "mock_catalog_entries": len(catalog), "generated_metadata_valid": True,
        "duplicate_vectors_and_constant_columns": "accepted_with_INFO",
        "partial_publication_retry": "resumed_without_duplicate_registry_entry",
        "completed_publication_retry": "preserved_the_existing_catalogue_entry",
        "invalid_NaN_package": "rejected_with_diagnostic_report",
        "interface_payload": "catalogue data only",
    }
    write_json(root / "mock_test_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="A new directory for local test results")
    smoke(parser.parse_args().output)
