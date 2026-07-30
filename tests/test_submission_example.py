from __future__ import annotations

from pathlib import Path

import yaml

from gene_registry.submission import validate_document


def test_completed_submission_example() -> None:
    source_path = Path(
        "portal_template/submission.example.yaml"
    )
    deployed_path = Path(
        "space/submission.example.yaml"
    )

    source_text = source_path.read_text(
        encoding="utf-8"
    )
    deployed_text = deployed_path.read_text(
        encoding="utf-8"
    )

    assert source_text == deployed_text

    document = yaml.safe_load(source_text)

    validate_document(
        document,
        "schemas/portal_submission.schema.json",
    )

    assert document["embedding_id"].startswith(
        "example_"
    )

    assert all(
        document["attestations"].values()
    )

    index = Path(
        "space/index.html"
    ).read_text(
        encoding="utf-8"
    )

    assert 'href="submission.example.yaml"' in index
    assert "Download completed example" in index
