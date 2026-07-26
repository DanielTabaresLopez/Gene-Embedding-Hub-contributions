from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master-genes", default="reference/master_gene_ids.txt")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--embedding-id", default="smoke_test_embedding")
    args = parser.parse_args()

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    genes = Path(args.master_genes).read_text(encoding="utf-8").splitlines()[:1500]
    rng = np.random.default_rng(12345)
    matrix = rng.normal(size=(len(genes), 16)).astype(np.float32)
    np.savez_compressed(output / "embeddings.npz", embeddings=matrix)
    pd.DataFrame({"ensembl_gene_id": genes}).to_csv(output / "genes.tsv", sep="\t", index=False)
    metadata = {
        "embedding_id": args.embedding_id,
        "display_name": "Smoke Test Embedding",
        "species": "Homo sapiens",
        "broad_modality": "other",
        "detailed_modality": "synthetic CI smoke test",
        "original_method": "deterministic Gaussian fixture",
        "model_checkpoint": "not-applicable",
        "embedding_generated_by": "project CI test",
        "input_data_source": "synthetic",
        "input_data_release": "v1",
        "pooling_strategy": "not-applicable",
        "original_identifier_type": "Ensembl gene ID",
        "mapping_method": "direct use of the project master gene universe",
        "source_license": "cc0-1.0",
        "redistribution_allowed": True,
        "source_url": "",
        "publication": ""
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        "# Smoke Test Embedding\n\nA deterministic synthetic package used only to test the automatic contribution pipeline. "
        "It contains no biological claims and must be removed from staging after the end-to-end test.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
