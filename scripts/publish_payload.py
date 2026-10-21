"""Publish only against the exact remote state used to build a release."""
import argparse
import json
from pathlib import Path
from huggingface_hub import HfApi


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["dataset", "space"], required=True)
    parser.add_argument("--state", default="current-state/state.json")
    parser.add_argument("--folder", required=True)
    parser.add_argument("--message", required=True)
    args = parser.parse_args()
    state = json.loads(Path(args.state).read_text())
    HfApi().upload_folder(
        repo_id=state[f"{args.target}_id"], repo_type=args.target,
        folder_path=args.folder, path_in_repo=".", revision="main",
        parent_commit=state[f"{args.target}_revision"],
        commit_message=args.message, ignore_patterns=[".cache/**"],
    )


if __name__ == "__main__":
    main()
