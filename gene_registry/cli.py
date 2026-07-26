from __future__ import annotations

import argparse
import sys

from .service import run_validation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a gene embedding submission")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--submission", required=True)
    validate.add_argument("--policy", required=True)
    validate.add_argument("--master-genes", required=True)
    validate.add_argument("--schema-dir", required=True)
    validate.add_argument("--output-dir", required=True)
    validate.add_argument("--package-dir", default=None, help="Optional local package directory for contributor pre-checks")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_validation(
        submission_path=args.submission,
        policy_path=args.policy,
        master_genes_path=args.master_genes,
        schema_dir=args.schema_dir,
        output_dir=args.output_dir,
        package_dir=args.package_dir,
    )
    print(result.outcome)
    return 0 if result.outcome == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
