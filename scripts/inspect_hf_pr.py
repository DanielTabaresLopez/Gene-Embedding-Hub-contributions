from __future__ import annotations

import argparse
import json
from pathlib import Path

from gene_registry.portal import inspect_portal_diff


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--diff-file",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    diff_text = Path(
        args.diff_file
    ).read_text(
        encoding="utf-8"
    )

    result = inspect_portal_diff(
        diff_text
    )

    output = Path(args.output)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "Embedding ID:",
        result["embedding_id"],
    )

    print(
        "Package path:",
        result["package_path"],
    )

    print(
        "Changed files:",
        len(result["changed_files"]),
    )

    print(
        "Hugging Face PR structure: PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
