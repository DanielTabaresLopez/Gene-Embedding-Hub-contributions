from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download
from huggingface_hub.errors import EntryNotFoundError


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--repo-id", required=True)
    parser.add_argument(
        "--repo-type",
        required=True,
        choices=("dataset", "space", "model"),
    )
    parser.add_argument("--filename", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        downloaded = Path(
            hf_hub_download(
                repo_id=args.repo_id,
                repo_type=args.repo_type,
                filename=args.filename,
            )
        )
    except EntryNotFoundError:
        output.write_text("[]\n", encoding="utf-8")
        print(
            f"{args.filename} does not exist yet; "
            f"created an empty JSON list at {output}"
        )
        return 0

    shutil.copy2(downloaded, output)

    print("Downloaded:", args.filename)
    print("Output:", output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
