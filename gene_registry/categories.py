from __future__ import annotations

from typing import Any


def resolve_catalog_category(
    submitted_value: str,
    modality_config: dict[str, Any],
) -> tuple[str, bool]:
    submitted = submitted_value.strip()

    if not submitted:
        raise ValueError(
            "The submitted modality cannot be empty."
        )

    categories = modality_config["categories"]
    fallback = modality_config["fallback_category"]

    canonical_by_casefold = {
        str(category).casefold(): str(category)
        for category in categories
    }

    for alias, canonical in modality_config.get("aliases", {}).items():
        if canonical in categories:
            canonical_by_casefold[str(alias).casefold()] = str(canonical)

    resolved = canonical_by_casefold.get(
        submitted.casefold()
    )

    if resolved is None:
        return str(fallback), False

    return resolved, True
