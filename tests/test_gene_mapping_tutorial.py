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
        "master_gene_table.parquet"
        in tutorial
    )

    assert (
        "Do not blindly use"
        in tutorial
    )

    assert (
        "Average those source vectors"
        in tutorial
    )
