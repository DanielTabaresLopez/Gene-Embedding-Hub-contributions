# Automatic acceptance policy

A contribution is automatically accepted when the configured validator returns `PASS`. Exact repeated vectors and constant feature columns are reported as advisory `INFO` checks under the current policy; they can be legitimate representations. Setting their explicit `fail_on_*` flags to `true` makes them blocking again. Zero vectors, non-finite values, identifier and shape errors remain blocking.

The default starter policy checks:

- immutable public Hugging Face Dataset revision;
- exact required package files;
- size limits suitable for a standard GitHub-hosted runner;
- safe NPZ loading with `allow_pickle=False`;
- exactly one two-dimensional `float32` array called `embeddings`;
- row agreement with `genes.tsv`;
- unique, unversioned Ensembl gene identifiers;
- coverage against the 20,097-gene master universe;
- finite values, no zero vectors, and no constant columns or exact duplicate vectors when policy requires them;
- submission schema, contributor-provided provenance, and automatic metadata generation;
- allowlisted source-license identifier when supplied, plus mandatory redistribution and rights attestations;
- exact checksum duplicate rejection against prior automatic contributions.

## Not verified by a computer

The system cannot independently establish that a license claim is legally correct, that provenance is truthful, or that a representation is scientifically valuable. The Space must state that automatic inclusion is not scientific or legal endorsement.

## Biological checks

The default starter leaves `biological_checks_enabled: false`. Enable it only after adding the project's exact seven-family labels, statistic, permutation procedure, multiple-testing rule, and tested thresholds. Do not invent a replacement test merely to make this field green.
