"""Read public state at immutable revisions; authentication errors are never empty registries."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download
from gene_registry.util import load_yaml, write_json


def fetch_state(project, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    api = HfApi(token=False)
    space_id, dataset_id = project["hf_space_id"], project["hf_dataset_id"]
    space_sha = api.repo_info(space_id, repo_type="space").sha
    dataset_sha = api.repo_info(dataset_id, repo_type="dataset").sha
    def read(repo_id, repo_type, revision, filename):
        path = hf_hub_download(repo_id, filename, repo_type=repo_type,
                               revision=revision, token=False)
        value = json.loads(Path(path).read_text())
        if not isinstance(value, list) or not all(isinstance(x, dict) for x in value):
            raise ValueError(f"{filename} must contain a list of objects")
        return value
    catalog = read(space_id, "space", space_sha, project["space_catalog_file"])
    files = api.list_repo_files(dataset_id, repo_type="dataset", revision=dataset_sha)
    registry_path = project["dataset_registry_file"]
    if registry_path in files:
        registry = read(dataset_id, "dataset", dataset_sha, registry_path)
    else:
        if any(e.get("community_contribution") is True for e in catalog):
            raise ValueError("Registry is missing while the live catalog contains community entries; restore the registry before publishing")
        registry = []
    write_json(output / "catalog.json", catalog)
    write_json(output / "community_registry.json", registry)
    write_json(output / "state.json", {
        "space_id": space_id, "space_revision": space_sha,
        "dataset_id": dataset_id, "dataset_revision": dataset_sha,
        "registry_missing": registry_path not in files,
    })
    print(f"Pinned live catalog: {len(catalog)} entries; registry: {len(registry)} entries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="config/project.yaml")
    parser.add_argument("--output", default="current-state")
    args = parser.parse_args()
    fetch_state(load_yaml(args.project), args.output)
