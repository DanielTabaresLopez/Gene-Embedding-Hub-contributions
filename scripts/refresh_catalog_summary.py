import argparse
import json
from pathlib import Path
from gene_registry.util import write_json


def summary(catalog):
    community = sum(entry.get("community_contribution") is True for entry in catalog)
    return {"catalog_count": len(catalog), "core_count": len(catalog) - community,
            "community_count": community, "community_catalog_count": community}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write_json(args.output, summary(json.loads(Path(args.catalog).read_text())))
