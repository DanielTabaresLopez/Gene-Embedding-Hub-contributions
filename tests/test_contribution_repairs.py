from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import yaml
from gene_registry.categories import resolve_catalog_category
from gene_registry.processing_state import marker, retry_decision
from gene_registry.service import run_validation
from scripts.inspect_portal_pr import inspect
from scripts.smoke_test_portal import make_mock_package, release_args, smoke
from scripts.prepare_portal_release import prepare


def validate(package, output, policy="config/policy.yaml"):
    return run_validation(package / "submission.yaml", policy, "reference/master_gene_ids.txt",
                          "schemas", output, package, "portal_submission.schema.json", False)


def rewrite_matrix(package, mutate):
    with np.load(package / "embeddings.npz", allow_pickle=False) as z:
        matrix = mutate(z["embeddings"].copy())
    np.savez_compressed(package / "embeddings.npz", embeddings=matrix)


def test_current_categories_and_legacy_aliases():
    config = yaml.safe_load(Path("config/modalities.yaml").read_text())
    catalog = json.loads(Path("space/catalog.json").read_text())
    assert set(config["categories"]) == {e["category"] for e in catalog}
    for category in config["categories"]:
        assert resolve_catalog_category(category.lower(), config) == (category, True)
    for alias, target in config["aliases"].items():
        assert resolve_catalog_category(alias, config) == (target, True)


@pytest.mark.parametrize("category, modality, expected_category, expected_modality", [
    ("Expression", "Expression", "Bulk expression", "Bulk expression"),
    ("Single-cell", "Single-cell", "Single-cell expression", "Single-cell expression"),
    ("Bulk expression", "Bulk expression", "Bulk expression", "Bulk expression"),
    ("Single-cell expression", "Single-cell expression", "Single-cell expression", "Single-cell expression"),
    ("Single-cell", "Single-cell transcriptomic gene-token vectors", "Single-cell expression", "Single-cell transcriptomic gene-token vectors"),
])
def test_expression_labels_in_published_package(tmp_path, category, modality, expected_category, expected_modality):
    package = make_mock_package(tmp_path / "inputs")
    submission_file = package / "submission.yaml"
    submission = yaml.safe_load(submission_file.read_text())
    submission["scientific"].update(category=category, modality=modality)
    submission_file.write_text(yaml.safe_dump(submission, sort_keys=False))
    registry = tmp_path / "registry.json"
    registry.write_text("[]\n")
    output = tmp_path / "release"
    assert prepare(release_args(package, registry, Path("space/catalog.json"), output)) == 0
    catalog = json.loads((output / "space/catalog.json").read_text())
    row = next(entry for entry in catalog if entry["id"] == package.name)
    assert (row["category"], row["modality"]) == (expected_category, expected_modality)
    dataset = output / "dataset/data/community_contributions"
    metadata = json.loads((dataset / package.name / "metadata.json").read_text())
    assert (metadata["category"], metadata["modality"]) == (expected_category, expected_modality)
    published_registry = json.loads((dataset / "community_registry.json").read_text())[0]
    assert published_registry["modality"] == expected_modality
    assert published_registry["submitted_modality"] == modality
    assert published_registry["submitted_category"] == category
    assert (dataset / package.name / "submission.yaml").read_bytes() == submission_file.read_bytes()


def test_legitimate_duplicate_vectors_and_constant_columns(tmp_path):
    package = make_mock_package(tmp_path)
    result = validate(package, tmp_path / "report")
    assert result.outcome == "PASS"
    assert result.summary["duplicate_vectors"] == 1
    assert result.summary["constant_columns"] == 1


def test_explicit_strict_flags_still_reject(tmp_path):
    package = make_mock_package(tmp_path)
    policy = yaml.safe_load(Path("config/policy.yaml").read_text())
    policy["matrix"].update(fail_on_duplicate_vectors=True, fail_on_constant_columns=True)
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(yaml.safe_dump(policy))
    result = validate(package, tmp_path / "report", policy_path)
    assert result.outcome == "FAIL"
    assert {c.check_id for c in result.checks if c.status == "FAIL"} >= {"matrix.duplicate_vectors", "matrix.constant_columns"}


def test_tiny_finite_nonzero_vectors_are_not_zero(tmp_path):
    package = make_mock_package(tmp_path, advisory=False)
    rewrite_matrix(package, lambda matrix: matrix * np.float32(1e-30))
    result = validate(package, tmp_path / "report")
    assert result.outcome == "PASS"
    assert result.summary["zero_vectors"] == 0 and result.summary["norm_min"] > 0


@pytest.mark.parametrize("problem", ["zero", "nan", "infinity", "float64", "rows", "empty", "string", "object", "broken_npz", "broken_yaml", "duplicate_gene"])
def test_invalid_packages_fail_with_report(tmp_path, problem):
    package = make_mock_package(tmp_path)
    if problem in {"zero", "nan", "infinity"}:
        def mutate(matrix):
            matrix[0] = {"zero": 0, "nan": np.nan, "infinity": np.inf}[problem]
            return matrix
        rewrite_matrix(package, mutate)
    elif problem in {"float64", "string", "object"}:
        rewrite_matrix(package, lambda matrix: matrix.astype({"float64": "float64", "string": "U20", "object": object}[problem]))
    elif problem == "rows": rewrite_matrix(package, lambda matrix: matrix[:-1])
    elif problem == "empty": rewrite_matrix(package, lambda matrix: matrix[:0])
    elif problem == "broken_npz": (package / "embeddings.npz").write_bytes(b"not an npz file")
    elif problem == "broken_yaml": (package / "submission.yaml").write_text("scientific: [broken")
    elif problem == "duplicate_gene":
        p = package / "genes.tsv"
        rows = p.read_text().splitlines(); rows[2] = rows[1]
        p.write_text("\n".join(rows) + "\n")
    result = validate(package, tmp_path / "report")
    assert result.outcome == "FAIL"
    report = json.loads((tmp_path / "report/validation_report.json").read_text())
    assert any(c["status"] == "FAIL" for c in report["checks"])


def test_complete_local_mock_and_partial_publication_recovery(tmp_path):
    assert smoke(tmp_path / "mock")["passed"]


def test_registry_conflict_is_reported_as_failure(tmp_path):
    package = make_mock_package(tmp_path)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps([{"embedding_id": package.name}]))
    output = tmp_path / "release"
    assert prepare(release_args(package, registry, Path("space/catalog.json"), output)) == 2
    result = json.loads((output / "reports/validation_report.json").read_text())
    assert result["outcome"] == "FAIL" and any(c["check_id"] == "release.conflict" for c in result["checks"])


def test_retry_states_and_validator_updates():
    now = datetime(2026, 10, 21, tzinfo=timezone.utc)
    head, version = "a" * 40, "current"
    def event(content, hours=0):
        return {"content": content, "created_at": now - timedelta(hours=hours)}
    old = [event(f"<!-- gene-embeddings-auto-dispatched:{head} -->", 100)]
    assert retry_decision(old, head, version, now)[0]
    queued = [event(marker("dispatched", head, version), 1)]
    assert not retry_decision(queued, head, version, now)[0]
    queued = [event(marker("dispatched", head, version), 7)]
    assert retry_decision(queued, head, version, now)[0]
    assert not retry_decision(queued * 3, head, version, now)[0]
    for result in ["REJECTED", "PUBLISHED"]:
        events = queued + [event(marker("processed", head, version, result))]
        assert not retry_decision(events, head, version, now)[0]
        assert retry_decision(events, head, "new-validator", now)[0]
    assert retry_decision(queued + [event(marker("processed", head, version, "ERROR"))], head, version, now)[0]


class FakePR:
    base, first, head = "0" * 40, "1" * 40, "2" * 40
    def __init__(self): self.revisions = []
    def get_discussion_details(self, **kwargs):
        return {"isPullRequest": True, "status": "open", "author": {"name": "test-author"},
                "changes": {"base": "refs/heads/main"}, "events": [
                    {"type": "commit", "data": {"oid": self.first, "parents": [self.base]}},
                    {"type": "commit", "data": {"oid": self.head, "parents": [self.first]}},
                ]}
    def list_repo_tree(self, revision, **kwargs):
        self.revisions.append(revision)
        if revision == self.base: return []
        assert revision == self.head
        return [SimpleNamespace(path=f"test_embedding/{name}", blob_id=name, size=100,
                                lfs=None, xet_hash=None)
                for name in ["embeddings.npz", "genes.tsv", "README.md", "submission.yaml"]]


def test_pr_correction_uses_original_base_and_immutable_head():
    api = FakePR()
    result = inspect(api, "owner/repo", 11, yaml.safe_load(Path("config/policy.yaml").read_text()), api.head)
    assert result["embedding_id"] == "test_embedding"
    assert result["pr_author"] == "test-author"
    assert api.revisions == [api.base, api.head]


def test_changed_pr_revision_is_not_silently_substituted():
    with pytest.raises(ValueError, match="changed since"):
        inspect(FakePR(), "owner/repo", 11, {}, "3" * 40)
