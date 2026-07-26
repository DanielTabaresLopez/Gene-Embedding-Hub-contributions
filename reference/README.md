# Reference files

`master_gene_ids.txt` contains the 20,097 unique `ensembl_gene_id` values from `master_gene_table_v1_1_enriched.csv` used by the project.

Do not replace this file without creating a documented library release and updating the policy version.

Biological family validation is intentionally disabled in `config/policy.yaml` until the exact seven-family labels, test statistic, permutations, and acceptance thresholds are added and regression-tested. Technical validation remains fully automatic.
