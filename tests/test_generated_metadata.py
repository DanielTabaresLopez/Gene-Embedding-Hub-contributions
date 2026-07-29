from __future__ import annotations

from gene_registry.submission import (
    validate_document,
)
from scripts.prepare_portal_release import (
    build_generated_metadata,
)


def minimal_submission() -> dict:
    return {
        "schema_version": 1,
        "embedding_id": "minimal_embedding",
        "display_name": "Minimal Embedding",
        "scientific": {
            "category": "Protein",
            "modality": "Protein sequence",
            "description": (
                "A sufficiently detailed description of "
                "a minimal portal embedding submission."
            ),
        },
        "provenance": {
            "species": "Homo sapiens",
            "identifier_before_mapping": (
                "Ensembl gene ID"
            ),
            "mapping_method": (
                "Direct alignment to the project master "
                "gene universe"
            ),
        },
        "licensing": {
            "redistribution_allowed": True,
        },
        "attestations": {
            "information_is_accurate": True,
            "rights_to_redistribute": True,
            "no_sensitive_human_data": True,
            "no_patient_level_data": True,
            "source_terms_reviewed": True,
            "acceptance_of_automatic_checks": True,
        },
    }


def result_summary() -> dict:
    return {
        "n_genes": 1500,
        "n_dimensions": 16,
        "dtype": "float32",
        "npz_key": "embeddings",
        "master_coverage_fraction": 0.0746,
    }


def test_compact_metadata_omits_optional_fields() -> None:
    metadata = build_generated_metadata(
        submission=minimal_submission(),
        result_summary=result_summary(),
        hf_pr_author="example-user",
        accepted_at=(
            "2026-07-29T15:00:00+00:00"
        ),
    )

    validate_document(
        metadata,
        "schemas/metadata.schema.json",
    )

    assert "schema_version" not in metadata

    assert metadata["contributor"] == {
        "huggingface_username": "example-user",
    }

    omitted = {
        "original_method",
        "model_checkpoint",
        "publication",
        "embedding_generated_by",
        "input_data_source",
        "input_data_release",
        "pooling_strategy",
        "source_license",
        "terms_url",
        "zero_vectors",
        "duplicate_vectors",
        "constant_columns",
        "value_min",
        "value_max",
        "norm_min",
        "norm_median",
        "norm_max",
        "embeddings_sha256",
        "checksums_sha256",
        "file_sizes_bytes",
    }

    assert omitted.isdisjoint(metadata)


def test_compact_metadata_includes_optional_fields() -> None:
    submission = minimal_submission()

    submission["contributor"] = {
        "name": "Example Contributor",
        "affiliation": "Example Institute",
    }

    submission["scientific"].update(
        {
            "original_method": "Example method",
            "model_checkpoint": "checkpoint-v1",
            "source_publication": (
                "https://doi.org/10.0000/example"
            ),
        }
    )

    submission["provenance"].update(
        {
            "embedding_generated_by": (
                "Example software"
            ),
            "input_data_source": "Example source",
            "input_data_release": "v1",
            "pooling_strategy": "Mean pooling",
        }
    )

    submission["licensing"].update(
        {
            "source_license": "cc-by-4.0",
            "terms_url": (
                "https://creativecommons.org/"
                "licenses/by/4.0/"
            ),
        }
    )

    metadata = build_generated_metadata(
        submission=submission,
        result_summary=result_summary(),
        hf_pr_author="example-user",
        accepted_at=(
            "2026-07-29T15:00:00+00:00"
        ),
    )

    validate_document(
        metadata,
        "schemas/metadata.schema.json",
    )

    assert metadata["original_method"] == (
        "Example method"
    )

    assert metadata["source_license"] == (
        "cc-by-4.0"
    )

    assert metadata["contributor"] == {
        "huggingface_username": "example-user",
        "name": "Example Contributor",
        "affiliation": "Example Institute",
    }
