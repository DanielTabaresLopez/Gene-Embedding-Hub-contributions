from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_detail_view_hides_internal_core_fields() -> None:
    app = (ROOT / "space" / "app.js").read_text(encoding="utf-8")

    assert "<b>QC:</b>" not in app
    assert "<b>Source Dataset:</b>" not in app
    # The current live detail view intentionally contains only the card
    # content, measured dimensions/coverage, contributor and package link.
    assert "<b>License:</b>" not in app
    assert "Open package files" in app


def test_core_builder_does_not_generate_old_placeholders() -> None:
    builder = (
        ROOT / "scripts" / "build_core_catalog.py"
    ).read_text(encoding="utf-8")

    assert 'or "see package metadata"' not in builder
    assert 'or "not recorded in package metadata"' not in builder
    assert "f\"{name}. Core embedding package from \"" not in builder


def test_enrichment_script_is_present() -> None:
    script = ROOT / "scripts" / "enrich_core_catalog_metadata.py"
    text = script.read_text(encoding="utf-8")

    assert "method_from_sources" in text
    assert "license_from_sources" in text
    assert "clean_description" in text
