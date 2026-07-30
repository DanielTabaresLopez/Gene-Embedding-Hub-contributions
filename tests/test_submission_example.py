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

    assert document["embedding_id"] == "esm2_v1_1"
    assert document["display_name"] == "ESM2-v1.1"

    assert document["contributor"] == {
        "name": "Daniel Tabares Lopez",
        "affiliation": "ETH Zurich",
    }

    scientific = document["scientific"]

    assert scientific["category"] == "Protein"
    assert scientific["modality"] == "Protein sequence"
    assert scientific["model_checkpoint"] == (
        "esm2_t33_650M_UR50D"
    )

    assert scientific["source_publication"] == (
        "https://doi.org/10.1101/"
        "2025.01.29.635607"
    )

    provenance = document["provenance"]

    assert provenance[
        "identifier_before_mapping"
    ] == "Entrez Gene ID"

    assert provenance["species"] == "Homo sapiens"

    # Unknown optional values must not be fabricated.
    assert "input_data_release" not in provenance
    assert "source_license" not in document["licensing"]
    assert "terms_url" not in document["licensing"]

    assert all(
        document["attestations"].values()
    )

    for placeholder in (
        "Example Contributor",
        "Example Research Institute",
        "Replace with",
    ):
        assert placeholder not in source_text

    index = Path(
        "space/index.html"
    ).read_text(
        encoding="utf-8"
    )

    assert 'href="submission.example.yaml"' in index

    assert (
        "Download completed example"
        in index
    )
