from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_catalog(path: Path, required: bool) -> list[dict[str, Any]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return []

    value = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(value, list):
        raise ValueError(f"{path} must contain a JSON list")

    if not all(isinstance(entry, dict) for entry in value):
        raise ValueError(f"{path} contains a non-object catalog entry")

    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", required=True)
    parser.add_argument("--existing", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    core = load_catalog(Path(args.core), required=True)
    existing = load_catalog(Path(args.existing), required=False)

    community = [
        entry
        for entry in existing
        if entry.get("community_contribution") is True
    ]

    core_ids = {str(entry.get("id")) for entry in core}
    community_ids = {str(entry.get("id")) for entry in community}

    duplicate_ids = sorted(core_ids & community_ids)

    if duplicate_ids:
        raise SystemExit(
            "Community entries conflict with core IDs: "
            + ", ".join(duplicate_ids)
        )

    merged = core + community
    merged.sort(
        key=lambda entry: (
            str(entry.get("name", "")).casefold(),
            str(entry.get("id", "")).casefold(),
        )
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary = {
        "catalog_count": len(merged),
        "core_count": len(core),
        "community_count": len(community),
        "latest_embedding_id": None,
    }

    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("Core entries:", len(core))
    print("Preserved community entries:", len(community))
    print("Merged catalog entries:", len(merged))
    print("Output:", output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
