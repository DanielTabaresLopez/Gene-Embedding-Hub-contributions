from pathlib import Path

import json
import yaml


REQUIRED_FILES = {
    "embeddings.npz",
    "genes.tsv",
    "README.md",
    "submission.yaml",
}

CATEGORIES = {
    "dna",
    "expression",
    "functional-genomics",
    "knowledge",
    "literature",
    "multimodal",
    "network",
    "protein",
    "rna",
    "regulatory",
    "single-cell",
    "other",
}


def read(path: str) -> str:
    return Path(path).read_text(
        encoding="utf-8"
    )


def test_all_submission_instructions_are_on_main_page() -> None:
    index = read("space/index.html")

    assert 'href="#contribute"' in index
    assert "Open Hugging Face uploader" in index
    assert "Open as a pull request" in index
    assert "Automatic validation and publication" in index

    for filename in REQUIRED_FILES:
        assert filename in index

    assert (
        "metadata.json"
        in index
    )

    assert (
        "A <code>metadata.json</code> file is automatically"
        in index
    )

    assert "generated after acceptance." in index

    assert (
        "Dimensions, dtype, gene count and coverage"
        not in index
    )

    step_1_position = index.index(
        '<span class="step-number">1</span>'
    )

    metadata_position = index.index(
        "A <code>metadata.json</code> file is automatically"
    )

    step_2_position = index.index(
        '<span class="step-number">2</span>'
    )

    assert (
        step_1_position
        < metadata_position
        < step_2_position
    )

    assert not Path(
        "space/contribute.html"
    ).exists()


def test_unwanted_space_sections_are_absent() -> None:
    index = read("space/index.html")

    removed_phrases = [
        (
            "A GitHub account, GitHub fork, separate "
            "Dataset, and commit SHA are not required."
        ),
        "Privacy and publication",
        "Staging access",
        "Staging note:",
    ]

    for phrase in removed_phrases:
        assert phrase not in index


def test_template_uses_category_and_modality() -> None:
    source = yaml.safe_load(
        read("portal_template/submission.yaml")
    )

    deployed = yaml.safe_load(
        read("space/submission.yaml")
    )

    assert source == deployed

    scientific = source["scientific"]

    assert (
        scientific["category"]
        == "Replace with the category"
    )

    assert (
        scientific["modality"]
        == "Replace with the modality"
    )

    assert "broad_modality" not in scientific
    assert "detailed_modality" not in scientific


def test_portal_schema_requires_category_and_modality() -> None:
    schema = json.loads(
        read(
            "schemas/portal_submission.schema.json"
        )
    )

    scientific = schema[
        "properties"
    ]["scientific"]

    assert "category" in scientific["required"]
    assert "modality" in scientific["required"]

    assert (
        "broad_modality"
        not in scientific["properties"]
    )

    assert (
        "detailed_modality"
        not in scientific["properties"]
    )


def test_category_card_palettes_are_present() -> None:
    app = read("space/app.js")
    style = read("space/style.css")

    assert "categoryClass(item.category)" in app

    for category in CATEGORIES:
        assert f".category-{category}" in style

def test_portal_optional_and_required_fields() -> None:
    schema = json.loads(
        read(
            "schemas/portal_submission.schema.json"
        )
    )

    assert "contributor" not in schema["required"]

    scientific = schema[
        "properties"
    ]["scientific"]

    assert scientific["required"] == [
        "category",
        "modality",
        "description",
    ]

    provenance = schema[
        "properties"
    ]["provenance"]

    assert provenance["required"] == [
        "species",
        "identifier_before_mapping",
        "mapping_method",
    ]

    licensing = schema[
        "properties"
    ]["licensing"]

    assert licensing["required"] == [
        "redistribution_allowed",
    ]

    source = yaml.safe_load(
        read("portal_template/submission.yaml")
    )

    deployed = yaml.safe_load(
        read("space/submission.yaml")
    )

    assert source == deployed
    assert "contributor" not in source

    assert set(source["scientific"]) == {
        "category",
        "modality",
        "description",
    }

    assert set(source["provenance"]) == {
        "species",
        "identifier_before_mapping",
        "mapping_method",
    }

    assert source["licensing"] == {
        "redistribution_allowed": True,
    }
