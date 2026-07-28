from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _resolve_text(
    document: Mapping[str, Any],
    canonical_name: str,
    legacy_name: str,
) -> str:
    value = document.get(canonical_name)

    if value is None:
        value = document.get(legacy_name)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Missing required field {canonical_name!r}."
        )

    return value


def submission_category(
    submission: Mapping[str, Any],
) -> str:
    scientific = submission["scientific"]

    return _resolve_text(
        scientific,
        "category",
        "broad_modality",
    )


def submission_modality(
    submission: Mapping[str, Any],
) -> str:
    scientific = submission["scientific"]

    return _resolve_text(
        scientific,
        "modality",
        "detailed_modality",
    )


def package_category(
    metadata: Mapping[str, Any],
) -> str:
    return _resolve_text(
        metadata,
        "category",
        "broad_modality",
    )


def package_modality(
    metadata: Mapping[str, Any],
) -> str:
    return _resolve_text(
        metadata,
        "modality",
        "detailed_modality",
    )
