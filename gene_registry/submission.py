from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .util import load_yaml, safe_relative_package_path


def validate_document(
    document: dict[str, Any],
    schema_path: str | Path,
) -> None:
    schema = json.loads(
        Path(schema_path).read_text(encoding="utf-8")
    )

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )

    if errors:
        formatted = []

        for error in errors:
            location = (
                ".".join(
                    str(part)
                    for part in error.absolute_path
                )
                or "<root>"
            )

            formatted.append(
                f"{location}: {error.message}"
            )

        raise ValueError(
            "Schema validation failed:\n"
            + "\n".join(formatted)
        )


def load_and_validate_submission(
    path: str | Path,
    schema_path: str | Path,
) -> dict[str, Any]:
    submission = load_yaml(path)

    validate_document(
        submission,
        schema_path,
    )

    # The legacy GitHub submission schema contains a candidate
    # section. Direct Hugging Face submissions do not.
    candidate = submission.get("candidate")

    if isinstance(candidate, dict):
        candidate["path"] = safe_relative_package_path(
            candidate["path"]
        )

    return submission
