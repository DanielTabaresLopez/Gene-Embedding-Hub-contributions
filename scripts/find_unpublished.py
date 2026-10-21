from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--registry-file", required=True)
    parser.add_argument("--submissions", required=True)
    parser.add_argument("--github-output", required=True)
    parser.add_argument("--project", default="config/project.yaml")

    args = parser.parse_args()

    registry_path = Path(args.registry_file)

    registry = json.loads(
        registry_path.read_text(encoding="utf-8")
    )

    if not isinstance(registry, list):
        raise ValueError(
            f"Expected a JSON list in {registry_path}"
        )

    published = {
        entry["embedding_id"]
        for entry in registry
    }

    missing: list[str] = []
    project = yaml.safe_load(Path(args.project).read_text(encoding="utf-8"))
    retired = set(project.get("retired_legacy_submission_ids", []))

    for path in sorted(
        Path(args.submissions).glob("*.y*ml")
    ):
        if path.name.startswith("_"):
            continue

        document = yaml.safe_load(
            path.read_text(encoding="utf-8")
        )

        if document.get("embedding_id") not in published | retired:
            missing.append(str(path))

    selected = missing[0] if missing else ""

    with Path(args.github_output).open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            f"submission_file={selected}\n"
        )
        handle.write(
            f"missing_count={len(missing)}\n"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
