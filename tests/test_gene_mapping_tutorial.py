import re

from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(
        encoding="utf-8"
    )


def test_gene_mapping_tutorial_is_published() -> None:
    index = read("space/index.html")
    tutorial = read(
        "space/gene-mapping-tutorial.html"
    )
    documentation = read(
        "docs/GENE_MAPPING_TUTORIAL.md"
    )

    assert (
        'href="gene-mapping-tutorial.html"'
        in index
    )

    assert (
        "Open gene mapping tutorial"
        in index
    )

    required_terms = (
        "map_ensembl_gene_ids_all",
        "map_entrez_ids_all",
        "map_uniprot_ids_all",
        "map_symbols_all",
        "unique",
        "unmapped",
        "ambiguous",
        "genes.tsv",
        "embeddings.npz",
    )

    for term in required_terms:
        assert term in tutorial
        assert term in documentation

    assert (
        "master_gene_table.csv"
        in tutorial
    )

    assert (
        "Do not blindly use"
        in tutorial
    )


    assert "Need help converting source identifiers?" not in index

    assert "master_gene_table.parquet" not in tutorial
    assert "Download master table Parquet" not in tutorial

    assert "Exclude and report" not in tutorial
    assert "Recommended mapping report" not in tutorial

    overview_position = tutorial.index("<h2>Overview</h2>")
    important_position = tutorial.index(
        "<strong>Important:</strong>"
    )
    step_1_position = tutorial.index(
        "<h2>1. Identify the source identifier type</h2>"
    )

    assert (
        overview_position
        < important_position
        < step_1_position
    )

    assert (
        "Average those source vectors"
        in tutorial
    )

def test_mapping_tutorial_heading_and_theme_toggle() -> None:
    index = read("space/index.html")
    tutorial = read(
        "space/gene-mapping-tutorial.html"
    )

    assert (
        "<h2>7. Document the procedure in "
        "submission.yaml</h2>"
        in tutorial
    )

    assert (
        "<h2>7. Document the procedure</h2>"
        not in tutorial
    )

    button_pattern = re.compile(
        r"<button\b[^>]*>.*?</button>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    main_theme_buttons = [
        button.strip()
        for button in button_pattern.findall(index)
        if "theme" in button.lower()
    ]

    tutorial_theme_buttons = [
        button.strip()
        for button in button_pattern.findall(tutorial)
        if "theme" in button.lower()
    ]

    assert len(main_theme_buttons) == 1
    assert tutorial_theme_buttons == main_theme_buttons

    assert '<script src="theme.js"></script>' in tutorial

    assert (
        "Tutorial theme-toggle support"
        in tutorial
    )
