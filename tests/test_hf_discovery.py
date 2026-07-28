from scripts.discover_hf_submission import (
    already_dispatched,
    discover_next_submission,
    dispatched_marker,
    latest_head_sha,
)


class FakeApi:
    def __init__(
        self,
        discussions,
        details,
    ):
        self.discussions = discussions
        self.details = details

    def get_repo_discussions(
        self,
        repo_id,
        repo_type,
    ):
        return iter(self.discussions)

    def get_discussion_details(
        self,
        repo_id,
        repo_type,
        discussion_num,
    ):
        return self.details[discussion_num]


def make_details(
    head_sha: str,
    *,
    comments: list[str] | None = None,
    status: str = "open",
):
    events = [
        {
            "type": "commit",
            "oid": head_sha,
        }
    ]

    for comment in comments or []:
        events.append(
            {
                "type": "comment",
                "content": comment,
            }
        )

    return {
        "num": 4,
        "author": "test-user",
        "status": status,
        "is_pull_request": True,
        "target_branch": "refs/heads/main",
        "events": events,
    }


def test_latest_head_sha() -> None:
    details = {
        "events": [
            {
                "type": "commit",
                "oid": "a" * 40,
            },
            {
                "type": "commit",
                "oid": "b" * 40,
            },
        ]
    }

    assert latest_head_sha(details) == "b" * 40


def test_marker_detects_same_revision() -> None:
    head = "c" * 40

    details = make_details(
        head,
        comments=[
            dispatched_marker(head),
        ],
    )

    assert already_dispatched(
        details,
        head,
    )


def test_selects_oldest_open_undispatched_pr() -> None:
    first_head = "d" * 40
    second_head = "e" * 40

    discussions = [
        {
            "num": 2,
            "title": "First",
            "status": "open",
            "author": "first-user",
            "is_pull_request": True,
        },
        {
            "num": 3,
            "title": "Second",
            "status": "open",
            "author": "second-user",
            "is_pull_request": True,
        },
    ]

    details = {
        2: make_details(first_head),
        3: make_details(second_head),
    }

    result = discover_next_submission(
        api=FakeApi(
            discussions,
            details,
        ),
        repo_id="org/dataset",
        repo_type="dataset",
    )

    assert result["found"] is True
    assert result["pr_number"] == 2
    assert result["head_sha"] == first_head


def test_skips_already_dispatched_revision() -> None:
    first_head = "f" * 40
    second_head = "1" * 40

    discussions = [
        {
            "num": 2,
            "title": "Already queued",
            "status": "open",
            "author": "first-user",
            "is_pull_request": True,
        },
        {
            "num": 3,
            "title": "New submission",
            "status": "open",
            "author": "second-user",
            "is_pull_request": True,
        },
    ]

    details = {
        2: make_details(
            first_head,
            comments=[
                dispatched_marker(
                    first_head
                ),
            ],
        ),
        3: make_details(second_head),
    }

    result = discover_next_submission(
        api=FakeApi(
            discussions,
            details,
        ),
        repo_id="org/dataset",
        repo_type="dataset",
    )

    assert result["found"] is True
    assert result["pr_number"] == 3


def test_new_commit_is_eligible_again() -> None:
    old_head = "2" * 40
    new_head = "3" * 40

    details = make_details(
        new_head,
        comments=[
            dispatched_marker(old_head),
        ],
    )

    assert not already_dispatched(
        details,
        new_head,
    )
