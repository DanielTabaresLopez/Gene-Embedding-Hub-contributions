"""Exercise remote-state failure paths without making remote writes."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import fetch_current_state, finalize_portal_run, find_unpublished, publish_payload
from scripts.prepare_portal_release import prepare
from scripts.smoke_test_portal import make_mock_package, release_args


PROJECT = {
    "hf_space_id": "test/space", "hf_dataset_id": "test/data",
    "space_catalog_file": "catalog.json", "dataset_registry_file": "registry.json",
}


def fake_state(monkeypatch, tmp_path, catalog, registry=None, error=None):
    calls = []
    class API:
        def repo_info(self, repo_id, repo_type):
            return SimpleNamespace(sha={"space": "a" * 40, "dataset": "b" * 40}[repo_type])
        def list_repo_files(self, repo_id, **kwargs):
            assert kwargs == {"repo_type": "dataset", "revision": "b" * 40}
            if error:
                raise error
            return [] if registry is None else ["registry.json"]
    def download(repo_id, filename, **kwargs):
        calls.append((repo_id, filename, kwargs))
        path = tmp_path / filename
        path.write_text(json.dumps(catalog if filename == "catalog.json" else registry))
        return str(path)
    monkeypatch.setattr(fetch_current_state, "HfApi", lambda **kwargs: API())
    monkeypatch.setattr(fetch_current_state, "hf_hub_download", download)
    return calls


def test_missing_registry_bootstraps_only_when_catalog_has_no_community(monkeypatch, tmp_path):
    calls = fake_state(monkeypatch, tmp_path, [{"id": "core", "community_contribution": False}])
    output = tmp_path / "state"
    fetch_current_state.fetch_state(PROJECT, output)
    assert json.loads((output / "community_registry.json").read_text()) == []
    state = json.loads((output / "state.json").read_text())
    assert state["registry_missing"] is True
    assert state["space_revision"] == "a" * 40 and state["dataset_revision"] == "b" * 40
    assert calls[0][2] == {"repo_type": "space", "revision": "a" * 40, "token": False}
    fake_state(monkeypatch, tmp_path, [{"id": "community", "community_contribution": True}])
    with pytest.raises(ValueError, match="restore the registry"):
        fetch_current_state.fetch_state(PROJECT, tmp_path / "unsafe")
    assert not (tmp_path / "unsafe/community_registry.json").exists()


def test_existing_registry_download_is_pinned(monkeypatch, tmp_path):
    registry = [{"embedding_id": "accepted"}]
    calls = fake_state(monkeypatch, tmp_path, [{"community_contribution": True}], registry)
    fetch_current_state.fetch_state(PROJECT, tmp_path / "state")
    assert json.loads((tmp_path / "state/community_registry.json").read_text()) == registry
    assert calls[1][2] == {"repo_type": "dataset", "revision": "b" * 40, "token": False}


def test_remote_failure_is_not_treated_as_an_empty_registry(monkeypatch, tmp_path):
    fake_state(monkeypatch, tmp_path, [], error=RuntimeError("HTTP 401"))
    with pytest.raises(RuntimeError, match="401"):
        fetch_current_state.fetch_state(PROJECT, tmp_path / "state")
    assert not (tmp_path / "state/community_registry.json").exists()


@pytest.mark.parametrize("target", ["dataset", "space"])
def test_publisher_requires_unchanged_remote_parent(monkeypatch, tmp_path, target):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({f"{target}_id": "test/repo", f"{target}_revision": "c" * 40}))
    calls = []
    monkeypatch.setattr(publish_payload, "HfApi", lambda: SimpleNamespace(upload_folder=lambda **kwargs: calls.append(kwargs)))
    monkeypatch.setattr(sys, "argv", ["publish", "--target", target, "--state", str(state), "--folder", str(tmp_path), "--message", "Test"])
    publish_payload.main()
    assert calls[0]["parent_commit"] == "c" * 40
    assert calls[0]["repo_type"] == target and calls[0]["revision"] == "main"


@pytest.mark.parametrize("changed_head,close_fails", [(False, False), (True, False), (False, True)])
def test_finalizer_closes_only_published_revision_before_terminal_marker(monkeypatch, tmp_path, changed_head, close_fails):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "hf-pr-state").mkdir()
    (tmp_path / "hf-pr-state/inspection.json").write_text(json.dumps({"head_sha": "a" * 40}))
    events = []
    class API:
        def get_discussion_details(self, **kwargs):
            return SimpleNamespace(status="open")
        def change_discussion_status(self, **kwargs):
            events.append("close")
            if close_fails:
                raise RuntimeError("Temporary close failure")
        def comment_discussion(self, **kwargs):
            events.append("comment")
            assert ":" + "a" * 40 + ":PUBLISHED -->" in kwargs["comment"]
    monkeypatch.setenv("HF_TOKEN", "unit-test-token")
    monkeypatch.setattr(finalize_portal_run, "HfApi", lambda **kwargs: API())
    monkeypatch.setattr(finalize_portal_run, "latest_head_sha", lambda _: ("b" if changed_head else "a") * 40)
    monkeypatch.setattr(finalize_portal_run, "validator_fingerprint", lambda: "test-version")
    monkeypatch.setattr(sys, "argv", ["finalize", "--repo-id", "test/repo", "--pr-number", "11", "--published", "true", "--run-url", "https://example.org/test"])
    if close_fails:
        with pytest.raises(RuntimeError, match="close failure"):
            finalize_portal_run.main()
        assert events == ["close"]
    else:
        assert finalize_portal_run.main() == 0
        assert events == (["comment"] if changed_head else ["close", "comment"])


def test_retired_demo_is_not_reintroduced_by_reconciliation(monkeypatch, tmp_path):
    submissions = tmp_path / "submissions"
    submissions.mkdir()
    for embedding_id in ["retired_demo", "new_real_embedding"]:
        (submissions / f"{embedding_id}.yaml").write_text(yaml.safe_dump({"embedding_id": embedding_id}))
    registry = tmp_path / "registry.json"
    registry.write_text("[]")
    project = tmp_path / "project.yaml"
    project.write_text(yaml.safe_dump({"retired_legacy_submission_ids": ["retired_demo"]}))
    output = tmp_path / "output.txt"
    monkeypatch.setattr(sys, "argv", ["reconcile", "--registry-file", str(registry), "--submissions", str(submissions), "--project", str(project), "--github-output", str(output)])
    assert find_unpublished.main() == 0
    assert "new_real_embedding.yaml" in output.read_text()
    assert "missing_count=1" in output.read_text()


def test_folder_id_mismatch_has_actionable_report(monkeypatch, tmp_path):
    package = make_mock_package(tmp_path)
    doc = yaml.safe_load((package / "submission.yaml").read_text())
    doc["embedding_id"] = "a_different_id"
    (package / "submission.yaml").write_text(yaml.safe_dump(doc))
    registry = tmp_path / "registry.json"
    registry.write_text("[]")
    output = tmp_path / "release"
    assert prepare(release_args(package, registry, Path("space/catalog.json"), output)) == 2
    report = json.loads((output / "reports/validation_report.json").read_text())
    assert report["outcome"] == "FAIL"
    assert any(c["check_id"] == "package.folder" and c["status"] == "FAIL" for c in report["checks"])
    assert not (output / "dataset").exists()
