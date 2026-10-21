from __future__ import annotations

import platform
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from .checks import validate_package
from .hf_package import download_candidate, inspect_candidate
from .models import ValidationResult
from .report import write_report
from .submission import load_and_validate_submission
from .util import load_yaml


def run_validation(
    submission_path: str | Path,
    policy_path: str | Path,
    master_genes_path: str | Path,
    schema_dir: str | Path,
    output_dir: str | Path,
    package_dir: str | Path | None = None,
    submission_schema_name: str = "submission.schema.json",
    submitted_metadata_required: bool = True,
) -> ValidationResult:
    policy = load_yaml(policy_path)
    schema_dir = Path(schema_dir)

    try:
        if Path(submission_path).stat().st_size > int(policy["limits"]["max_submission_yaml_bytes"]):
            raise ValueError("submission.yaml exceeds the configured size limit")
        submission = load_and_validate_submission(
            submission_path,
            schema_dir / submission_schema_name,
        )
    except Exception as exc:
        result = ValidationResult(outcome="FAIL")
        result.add("submission.schema", "FAIL", str(exc))
        write_report(result, output_dir)
        return result

    master_genes = {
        line.strip()
        for line in Path(master_genes_path)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }

    candidate_info = None
    temporary: Path | None = None

    try:
        if package_dir is None:
            candidate_info = inspect_candidate(
                submission,
                policy,
            )

            temporary = Path(
                tempfile.mkdtemp(
                    prefix="gene-embedding-candidate-"
                )
            )

            package_dir = download_candidate(
                submission,
                temporary,
            )

        try:
            result = validate_package(
                package_dir=package_dir,
                submission=submission,
                policy=policy,
                master_genes=master_genes,
                metadata_schema=schema_dir / "metadata.schema.json",
                metadata_required=submitted_metadata_required,
                candidate_info=candidate_info,
            )
        except Exception as exc:
            result = ValidationResult(outcome="FAIL")
            result.add("package.read", "FAIL", f"Could not validate the package: {exc}")

        result.provenance["validator_environment"] = {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        }

        write_report(
            result,
            output_dir,
        )

        return result

    finally:
        if temporary is not None:
            shutil.rmtree(
                temporary,
                ignore_errors=True,
            )
