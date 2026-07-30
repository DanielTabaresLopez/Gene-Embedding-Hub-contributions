# Gene identifier mapping tutorial

All submitted embeddings must use unversioned human Ensembl gene IDs
in `genes.tsv`. The order of those IDs must exactly match the row order
of the matrix stored in `embeddings.npz`.

The project master table is the single reference used to convert source
identifiers into the accepted Ensembl gene universe.

## Download the master table

- CSV:
  https://huggingface.co/datasets/embeddingsSSRF/gene_embeddings/resolve/main/data/master_gene_table.csv?download=true
- Parquet:
  https://huggingface.co/datasets/embeddingsSSRF/gene_embeddings/resolve/main/data/master_gene_table.parquet?download=true

The Parquet file is normally faster and preserves column types better.
The CSV file is easier to inspect manually.

## Mapping workflow

```text
source identifiers + source embedding matrix
                    |
                    v
       map identifiers to the master table
                    |
                    v
       classify each source identifier as:
       unique / unmapped / ambiguous
                    |
                    v
       exclude unmapped and ambiguous rows
                    |
                    v
       average rows that map to the same final gene
                    |
                    v
       mapped matrix + row-aligned genes.tsv
```

## 1. Identify the source identifier type

First determine what identifies each row in the original embedding.

Common possibilities include:

| Source identifier | Master-table mapping column |
|---|---|
| Ensembl gene ID | `map_ensembl_gene_ids_all` |
| Entrez Gene ID | `map_entrez_ids_all` |
| UniProt accession | `map_uniprot_ids_all` |
| RefSeq accession | `map_refseq_ids_all` |
| CCDS ID | `map_ccds_ids_all` |
| Ensembl transcript ID | `map_ensembl_transcript_ids_all` |
| Versioned Ensembl transcript ID | `map_ensembl_transcript_ids_all_versioned` |
| Ensembl protein ID | `map_ensembl_protein_ids_all` |
| Versioned Ensembl protein ID | `map_ensembl_protein_ids_all_versioned` |
| STRING protein ID | `map_string_protein_ids_all` |

Values containing several identifiers use `|` as the separator.

For versioned Ensembl identifiers such as `ENSG00000123456.7`, retain
the original value for reporting but normally compare the unversioned
form `ENSG00000123456` when using an unversioned mapping column.

## 2. Treat symbols with explicit priority

Do not blindly map gene symbols through `map_symbols_all`, because that
column combines current symbols, previous symbols, aliases, and names.

Use this order:

1. Current `gene_symbol` or `hgnc_approved_symbol`.
2. `hgnc_previous_symbols`.
3. `hgnc_alias_symbols`.

Only move to a lower-priority level when the identifier was not matched
at a higher-priority level.

## 3. Accept only unique mappings

For every source identifier, collect the Ensembl gene IDs to which it
maps.

- **Unique:** exactly one Ensembl gene ID; retain the row.
- **Unmapped:** no Ensembl gene ID; exclude the row and report it.
- **Ambiguous:** more than one Ensembl gene ID; exclude the row and
  report all candidates.

Do not select one candidate arbitrarily from an ambiguous mapping.

## 4. Build a lookup from a mapping column

The following example creates a lookup for Entrez IDs. The same pattern
can be used with another mapping column.

```python
from collections import defaultdict

import pandas as pd


master = pd.read_csv(
    "master_gene_table.csv",
    dtype=str,
)

lookup: dict[str, set[str]] = defaultdict(set)

for row in master[
    ["ensembl_gene_id", "map_entrez_ids_all"]
].dropna().itertuples(index=False):
    ensembl_gene_id = row.ensembl_gene_id

    for identifier in row.map_entrez_ids_all.split("|"):
        identifier = identifier.strip()

        if identifier:
            lookup[identifier].add(
                ensembl_gene_id
            )


def map_identifier(
    source_identifier: str,
) -> tuple[str, str | None]:
    candidates = lookup.get(
        str(source_identifier).strip(),
        set(),
    )

    if len(candidates) == 1:
        return "unique", next(iter(candidates))

    if len(candidates) == 0:
        return "unmapped", None

    return "ambiguous", None
```

## 5. Keep the matrix and identifiers aligned

Suppose:

```python
source_ids.shape[0] == source_matrix.shape[0]
```

Mapping decisions must be applied to both objects using the same source
row indices. Never sort or filter `genes.tsv` independently from the
matrix.

A mapping report should retain at least:

```text
source_row
source_identifier
mapping_status
ensembl_gene_id
mapping_method
```

## 6. Collapse duplicate final mappings

Several different source rows can sometimes map uniquely to the same
final Ensembl gene. The final package must still contain only one row
per Ensembl gene.

Average those source vectors after identifier mapping:

```python
import numpy as np


final_gene_ids = []
final_vectors = []

for ensembl_gene_id, source_indices in grouped_indices.items():
    final_gene_ids.append(ensembl_gene_id)

    final_vectors.append(
        source_matrix[source_indices].mean(
            axis=0,
        )
    )

final_matrix = np.asarray(
    final_vectors,
    dtype=np.float32,
)
```

Record how many source rows were combined for every final gene.

## 7. Create the final package files

Write the mapped matrix:

```python
np.savez_compressed(
    "embeddings.npz",
    embeddings=final_matrix.astype(
        np.float32
    ),
)
```

Write `genes.tsv` in exactly the same order:

```python
pd.DataFrame(
    {
        "ensembl_gene_id": final_gene_ids,
    }
).to_csv(
    "genes.tsv",
    sep="\t",
    index=False,
)
```

The following conditions must hold:

```python
assert final_matrix.shape[0] == len(final_gene_ids)
assert len(final_gene_ids) == len(set(final_gene_ids))
assert all(
    gene_id.startswith("ENSG")
    for gene_id in final_gene_ids
)
```

## 8. Describe the mapping in submission.yaml

Record the original identifier type and the actual decisions made:

```yaml
provenance:
  species: Homo sapiens
  identifier_before_mapping: Entrez Gene ID
  mapping_method: Source Entrez IDs were mapped through map_entrez_ids_all in the project master gene table. Only unique mappings were retained, unmapped and ambiguous identifiers were excluded, and duplicate source rows mapping to the same final Ensembl gene were averaged.
```

Change this text to accurately describe the submitted embedding.

## Recommended mapping report

Keep a separate report during processing with:

```text
total source rows
unique mapped rows
unmapped rows
ambiguous rows
final unique Ensembl genes
duplicate source rows collapsed
final master-table coverage
```

The mapping report is useful for reproducibility even though it is not
one of the four required submission files.
