from __future__ import annotations

from pathlib import Path

from .models import ValidationResult
from .util import write_json


def write_report(
    result: ValidationResult,
    output_dir: str | Path,
) -> None:
    output = Path(output_dir)

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_json(
        output / "validation_report.json",
        result.to_dict(),
    )

    lines = [
        f"# Candidate validation: {result.outcome}",
        "",
    ]

    if result.summary:
        lines.extend(
            [
                "## Summary",
                "",
                (
                    "- Embedding: "
                    f"`{result.summary.get('embedding_id', 'unknown')}`"
                ),
                (
                    "- Category: "
                    f"`{result.summary.get('catalog_category', result.summary.get('submitted_category', '—'))}`"
                ),
                (
                    "- Modality: "
                    f"`{result.summary.get('submitted_modality', '—')}`"
                ),
                (
                    "- Genes: "
                    f"{result.summary.get('n_genes', '—')}"
                ),
                (
                    "- Dimensions: "
                    f"{result.summary.get('n_dimensions', '—')}"
                ),
                (
                    "- Dtype: "
                    f"{result.summary.get('dtype', '—')}"
                ),
                (
                    "- Master coverage: "
                    f"{100 * result.summary.get('master_coverage_fraction', 0):.2f}%"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Checks",
            "",
            "| Check | Status | Message |",
            "|---|---:|---|",
        ]
    )

    for check in result.checks:
        message = (
            check.message
            .replace("|", "\\|")
            .replace("\n", " ")
        )

        lines.append(
            f"| `{check.check_id}` | "
            f"**{check.status}** | {message} |"
        )

    lines.extend(
        [
            "",
            (
                "> Automatic inclusion confirms compliance "
                "with the configured technical policy. It is "
                "not independent scientific or legal verification."
            ),
            "",
        ]
    )

    (
        output / "validation_summary.md"
    ).write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
