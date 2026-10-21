from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from huggingface_hub import HfApi, hf_hub_download


PLACEHOLDERS = {
    "see package metadata",
    "not recorded in package metadata",
    "legacy_core_package",
    "legacy package",
    "unknown",
    "not specified",
    "n/a",
    "none",
}
URL_RE = re.compile(r"https?://[^\s<>()\]\[{}\"']+")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
GENERIC_DESCRIPTION_RE = re.compile(
    r"^\s*[A-Za-z0-9_.-]+(?:_v\d+(?:_\d+)*)?\.\s+"
    r"(Core embedding package from\s+.+)$",
    flags=re.IGNORECASE,
)


def compact(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = re.sub(r"\s+", " ", value).strip()
    elif isinstance(value, (int, float, bool)):
        text = str(value)
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if not text or text.casefold() in PLACEHOLDERS:
        return None
    return text


def normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def walk_metadata(value: Any) -> Iterable[tuple[str, Any]]:
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        yield normalized_key(str(key)), item
        if isinstance(item, dict):
            yield from walk_metadata(item)


def metadata_value(metadata: dict[str, Any], *keys: str) -> str | None:
    wanted = [normalized_key(key) for key in keys]
    values: dict[str, list[Any]] = defaultdict(list)
    for key, value in walk_metadata(metadata):
        values[key].append(value)
    for key in wanted:
        for value in values.get(key, []):
            if isinstance(value, (dict, list, tuple, set)):
                continue
            text = compact(value)
            if text is not None:
                return text
    return None


def markdown_to_text(value: str) -> str:
    text = MARKDOWN_LINK_RE.sub(lambda match: match.group(1), value)
    text = re.sub(r"[`*_~]", "", text)
    text = re.sub(r"^\s*[-+>]\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def readme_key_values(readme: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = defaultdict(list)
    for raw_line in readme.splitlines():
        line = raw_line.strip().strip("|").strip()
        line = re.sub(r"^[-*+]\s+", "", line)
        line = line.strip("`")
        match = re.match(
            r"^([A-Za-z][A-Za-z0-9_ /.-]{1,80})\s*:\s*(.+)$",
            line,
        )
        if not match:
            continue
        key = normalized_key(match.group(1))
        value = match.group(2).strip().strip("`").strip()
        if value:
            values[key].append(value)
    return values


def readme_value(readme: str, *keys: str) -> str | None:
    values = readme_key_values(readme)
    for key in keys:
        for value in values.get(normalized_key(key), []):
            text = compact(markdown_to_text(value))
            if text is not None:
                return text
    return None


def markdown_sections(readme: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []
    in_code = False
    for raw_line in readme.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            current_lines.append(raw_line)
            continue
        heading = None if in_code else re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading:
            if current_title or current_lines:
                sections.append((current_title, current_lines))
            current_title = markdown_to_text(heading.group(1))
            current_lines = []
        else:
            current_lines.append(raw_line)
    if current_title or current_lines:
        sections.append((current_title, current_lines))
    return [(title, "\n".join(lines).strip()) for title, lines in sections]


def first_prose(value: str) -> str | None:
    paragraphs: list[list[str]] = []
    current: list[str] = []
    in_code = False
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code = not in_code
            if current:
                paragraphs.append(current)
                current = []
            continue
        if in_code:
            continue
        if not line:
            if current:
                paragraphs.append(current)
                current = []
            continue
        if line.startswith("#") or line.startswith("|"):
            continue
        if re.match(r"^[-*+]\s+", line) and ":" in line:
            continue
        current.append(line)
    if current:
        paragraphs.append(current)

    for paragraph in paragraphs:
        text = markdown_to_text(" ".join(paragraph))
        lowered = text.casefold()
        if len(text) < 35:
            continue
        if "~/" in text or "sha256" in lowered or "shape:" in lowered:
            continue
        if lowered.startswith("this folder contains"):
            continue
        return text[:700]
    return None


def section_prose(readme: str, keywords: tuple[str, ...]) -> str | None:
    for title, body in markdown_sections(readme):
        lowered = title.casefold()
        if any(keyword in lowered for keyword in keywords):
            text = first_prose(body)
            if text:
                return text
    return None


def sentence(value: str) -> str:
    text = compact(markdown_to_text(value)) or ""
    if not text:
        return text
    if text[-1] not in ".!?":
        text += "."
    return text


def clean_description(
    description: str | None,
    *,
    dataset_id: str,
) -> str:
    text = compact(description)
    if text is None:
        return f"Core embedding package from {dataset_id}."
    match = GENERIC_DESCRIPTION_RE.match(text)
    if match:
        return sentence(match.group(1))
    return text


def method_from_sources(
    metadata: dict[str, Any],
    readme: str,
    *,
    name: str,
    modality: str,
) -> tuple[str, str, bool]:
    direct_keys = (
        "method_description",
        "embedding_method",
        "original_model_or_method",
        "original_method",
        "method",
        "algorithm",
    )
    direct = metadata_value(metadata, *direct_keys) or readme_value(
        readme, *direct_keys
    )
    model = metadata_value(
        metadata,
        "model_checkpoint",
        "checkpoint",
        "model",
        "original_model",
    ) or readme_value(
        readme,
        "model_checkpoint",
        "checkpoint",
        "model",
        "original_model",
    )
    processing = metadata_value(
        metadata,
        "processing_summary",
        "pooling_strategy",
        "pooled_representation",
        "transformation",
        "transform",
        "embedding_generation",
    ) or readme_value(
        readme,
        "processing_summary",
        "pooling_strategy",
        "pooled_representation",
        "transformation",
        "transform",
        "embedding_generation",
    )

    if direct:
        method = sentence(direct)
        if processing and processing.casefold() not in method.casefold():
            method += " " + sentence(processing)
        return method[:900], "metadata_or_readme_field", False

    if model:
        method = f"Generated with {model}."
        if processing:
            method += " " + sentence(processing)
        else:
            method += " The released output is used as a fixed gene-level representation."
        return method[:900], "model_and_processing_fields", False

    section = section_prose(
        readme,
        (
            "method",
            "generation",
            "processing",
            "embedding construction",
            "provenance",
        ),
    )
    if section:
        return sentence(section)[:900], "readme_method_section", False

    fallback = (
        f"Fixed gene-level {modality} representation distributed as {name}. "
        "Full generation details are documented in the package README."
    )
    return fallback, "honest_fallback", True


def first_url(value: str | None) -> str | None:
    if not value:
        return None
    markdown_match = MARKDOWN_LINK_RE.search(value)
    if markdown_match:
        return markdown_match.group(2).rstrip(".,;:")
    match = URL_RE.search(value)
    if match:
        return match.group(0).rstrip(".,;:")
    return None


def source_url_from_readme(readme: str) -> str | None:
    priority = (
        "license",
        "licence",
        "terms",
        "original source",
        "official source",
        "model card",
        "repository",
        "paper",
    )
    lines = readme.splitlines()
    for keyword in priority:
        for raw_line in lines:
            if keyword in raw_line.casefold():
                url = first_url(raw_line)
                if url:
                    return url
    return first_url(readme)


def license_from_sources(
    metadata: dict[str, Any],
    readme: str,
    *,
    package_url: str,
) -> tuple[str, str | None, str, bool]:
    label_keys = (
        "source_license",
        "license",
        "licence",
        "model_license",
        "dataset_license",
        "original_license",
        "upstream_license",
    )
    url_keys = (
        "source_license_url",
        "license_url",
        "licence_url",
        "terms_url",
        "usage_terms_url",
        "original_source_url",
        "official_source_url",
        "source_url",
        "model_card_url",
        "repository_url",
        "paper_url",
    )
    label = metadata_value(metadata, *label_keys) or readme_value(
        readme, *label_keys
    )
    url = metadata_value(metadata, *url_keys) or readme_value(readme, *url_keys)
    url = first_url(url) or (url if url and url.startswith(("http://", "https://")) else None)

    license_section = None
    for title, body in markdown_sections(readme):
        if "license" in title.casefold() or "licence" in title.casefold():
            license_section = body
            break

    if license_section:
        section_url = first_url(license_section)
        section_text = first_prose(license_section)
        if not label and section_text:
            label = section_text
        if not url and section_url:
            url = section_url

    if label:
        embedded_url = first_url(label)
        if embedded_url and not url:
            url = embedded_url
        clean_label = markdown_to_text(label)
        clean_label = URL_RE.sub("", clean_label).strip(" -—:;,.()")
        if not clean_label:
            clean_label = "Original license / usage terms"
        return clean_label[:600], url, "explicit_license", False

    keyword_lines = [
        line.strip()
        for line in readme.splitlines()
        if any(
            keyword in line.casefold()
            for keyword in ("license", "licence", "terms of use", "usage terms")
        )
    ]
    for line in keyword_lines:
        text = markdown_to_text(line)
        line_url = first_url(line)
        text = URL_RE.sub("", text).strip(" -—:;,.()")
        if text and text.casefold() not in {"license", "licence"}:
            return text[:600], line_url, "readme_license_line", False

    source_url = source_url_from_readme(readme) or metadata_value(
        metadata,
        "original_source_url",
        "official_source_url",
        "source_url",
        "download_source",
        "model_card_url",
        "repository_url",
        "paper_url",
    )
    source_url = first_url(source_url) or (
        source_url
        if source_url and source_url.startswith(("http://", "https://"))
        else None
    )
    if source_url:
        return (
            "Original source / license terms",
            source_url,
            "upstream_source_link",
            False,
        )

    return (
        "See package README for upstream license terms",
        package_url,
        "package_readme_fallback",
        True,
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="space/catalog.json")
    parser.add_argument(
        "--report",
        default="reports/core_catalog_metadata_enrichment.json",
    )
    parser.add_argument(
        "--fail-on-fallback",
        action="store_true",
        help="Return a non-zero status if any method/license required a fallback.",
    )
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    report_path = Path(args.report)
    catalog = load_json(catalog_path)
    if not isinstance(catalog, list):
        raise ValueError("Catalog must contain a JSON list.")

    api = HfApi()
    repo_files_cache: dict[tuple[str, str], set[str]] = {}
    report_entries: list[dict[str, Any]] = []
    fallback_count = 0

    for entry in catalog:
        if not isinstance(entry, dict):
            raise ValueError("Every catalog entry must be an object.")
        if entry.get("community_contribution") is True:
            continue

        embedding_id = str(entry.get("id") or "").strip()
        dataset_id = str(entry.get("source_dataset") or "").strip()
        revision = str(entry.get("source_revision") or "main").strip()
        package_path = str(entry.get("dataset_path") or "").strip().rstrip("/")
        package_url = str(entry.get("package_url") or "").strip()
        if not all((embedding_id, dataset_id, package_path, package_url)):
            raise ValueError(f"{embedding_id or '<unknown>'}: incomplete source fields")

        repo_key = (dataset_id, revision)
        if repo_key not in repo_files_cache:
            repo_files_cache[repo_key] = set(
                api.list_repo_files(
                    repo_id=dataset_id,
                    repo_type="dataset",
                    revision=revision,
                )
            )
        repo_files = repo_files_cache[repo_key]

        metadata_path = f"{package_path}/metadata.json"
        if metadata_path not in repo_files:
            raise FileNotFoundError(f"Missing {metadata_path}")
        metadata_local = Path(
            hf_hub_download(
                repo_id=dataset_id,
                repo_type="dataset",
                revision=revision,
                filename=metadata_path,
            )
        )
        metadata = load_json(metadata_local)
        if not isinstance(metadata, dict):
            raise ValueError(f"{metadata_path} is not a JSON object")

        readme_path = next(
            (
                candidate
                for candidate in (
                    f"{package_path}/README.md",
                    f"{package_path}/README.MD",
                    f"{package_path}/readme.md",
                )
                if candidate in repo_files
            ),
            None,
        )
        readme = ""
        if readme_path:
            readme_local = Path(
                hf_hub_download(
                    repo_id=dataset_id,
                    repo_type="dataset",
                    revision=revision,
                    filename=readme_path,
                )
            )
            readme = readme_local.read_text(encoding="utf-8", errors="replace")

        method, method_source, method_fallback = method_from_sources(
            metadata,
            readme,
            name=str(entry.get("name") or embedding_id),
            modality=str(entry.get("modality") or "gene"),
        )
        license_label, license_url, license_source, license_fallback = (
            license_from_sources(
                metadata,
                readme,
                package_url=package_url,
            )
        )

        entry["algorithm"] = method
        entry["license"] = license_label
        if license_url:
            entry["license_url"] = license_url
        else:
            entry.pop("license_url", None)
        entry["description"] = clean_description(
            entry.get("description"),
            dataset_id=dataset_id,
        )

        used_fallback = method_fallback or license_fallback
        fallback_count += int(used_fallback)
        report_entries.append(
            {
                "embedding_id": embedding_id,
                "readme_path": readme_path,
                "method_source": method_source,
                "license_source": license_source,
                "used_fallback": used_fallback,
                "method": method,
                "license": license_label,
                "license_url": license_url,
                "description": entry["description"],
            }
        )

    catalog_path.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "catalog": str(catalog_path),
                "core_entries_enriched": len(report_entries),
                "entries_using_fallback": fallback_count,
                "entries": report_entries,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print("Core entries enriched:", len(report_entries))
    print("Entries using a fallback:", fallback_count)
    print("Catalog written to:", catalog_path)
    print("Review report written to:", report_path)

    if args.fail_on_fallback and fallback_count:
        print("ERROR: review fallback entries before publication.")
        return 2

    print("Catalog metadata enrichment: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
