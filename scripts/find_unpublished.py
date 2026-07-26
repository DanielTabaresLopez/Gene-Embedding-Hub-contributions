from __future__ import annotations

import argparse
import json
from pathlib import Path

from huggingface_hub import hf_hub_download

from gene_registry.util import load_yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--submissions", required=True)
    parser.add_argument("--github-output", required=True)
    args = parser.parse_args()

    project = load_yaml(args.project)
    try:
        registry_file = hf_hub_download(
            repo_id=project["hf_dataset_id"],
            repo_type="dataset",
            filename=project["dataset_registry_file"],
        )
        registry = json.loads(Path(registry_file).read_text(encoding="utf-8"))
    except Exception:
        registry = []
    published = {entry["embedding_id"] for entry in registry}

    import yaml
    missing = []
    for path in sorted(Path(args.submissions).glob("*.y*ml")):
        if path.name.startswith("_"):
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if doc.get("embedding_id") not in published:
            missing.append(str(path))
    selected = missing[0] if missing else ""
    with Path(args.github_output).open("a", encoding="utf-8") as handle:
        handle.write(f"submission_file={selected}\n")
        handle.write(f"missing_count={len(missing)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
