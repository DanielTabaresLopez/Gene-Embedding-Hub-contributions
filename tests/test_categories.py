from gene_registry.categories import (
    resolve_catalog_category,
)


MODALITIES = {
    "categories": [
        "DNA",
        "Expression",
        "Functional Genomics",
        "Knowledge",
        "Literature",
        "Multimodal",
        "Network",
        "Protein",
        "RNA",
        "Regulatory",
        "Single-cell",
    ],
    "fallback_category": "Other",
}


def test_known_category_is_canonicalized() -> None:
    category, recognized = (
        resolve_catalog_category(
            "protein",
            MODALITIES,
        )
    )

    assert category == "Protein"
    assert recognized is True


def test_unknown_category_becomes_other() -> None:
    category, recognized = (
        resolve_catalog_category(
            "Spatial Omics",
            MODALITIES,
        )
    )

    assert category == "Other"
    assert recognized is False
