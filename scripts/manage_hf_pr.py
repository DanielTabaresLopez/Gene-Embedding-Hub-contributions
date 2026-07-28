from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi


def read_comment(
    comment: str | None,
    comment_file: str | None,
) -> str | None:
    if comment and comment_file:
        raise ValueError(
            "Use either --comment or --comment-file, not both."
        )

    if comment_file:
        return Path(comment_file).read_text(
            encoding="utf-8"
        ).strip()

    if comment:
        return comment.strip()

    return None


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-id",
        required=True,
    )

    parser.add_argument(
        "--repo-type",
        default="dataset",
    )

    parser.add_argument(
        "--pr-number",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--comment",
    )

    parser.add_argument(
        "--comment-file",
    )

    parser.add_argument(
        "--close",
        action="store_true",
    )

    parser.add_argument(
        "--close-comment",
        default=(
            "Accepted and centrally archived. "
            "Thank you for the contribution."
        ),
    )

    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN")

    if not token:
        raise RuntimeError(
            "HF_TOKEN is required."
        )

    comment = read_comment(
        args.comment,
        args.comment_file,
    )

    api = HfApi(token=token)

    before = api.get_discussion_details(
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        discussion_num=args.pr_number,
    )

    if not before.is_pull_request:
        raise ValueError(
            f"Discussion #{args.pr_number} is not a Pull Request."
        )

    print("Status before:", before.status)
    print("PR URL:", before.url)

    if comment:
        api.comment_discussion(
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            discussion_num=args.pr_number,
            comment=comment,
        )

        print("PR comment posted.")

    if args.close and before.status != "closed":
        api.change_discussion_status(
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            discussion_num=args.pr_number,
            new_status="closed",
            comment=args.close_comment,
        )

        print("PR closed.")

    after = api.get_discussion_details(
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        discussion_num=args.pr_number,
    )

    print("Status after:", after.status)

    if args.close and after.status != "closed":
        raise RuntimeError(
            "The Pull Request was not closed successfully."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
