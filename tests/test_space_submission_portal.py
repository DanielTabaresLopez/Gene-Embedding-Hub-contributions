from pathlib import Path


REQUIRED_FILES = {
    "embeddings.npz",
    "genes.tsv",
    "metadata.json",
    "README.md",
    "submission.yaml",
}


def read(path: str) -> str:
    return Path(path).read_text(
        encoding="utf-8"
    )


def test_space_uses_hugging_face_uploader() -> None:
    app = read("space/app.js")

    assert (
        "embeddingsSSRF/"
        "gene_embeddings_staging/upload/main"
        in app
    )

    assert "GITHUB_CONTRIBUTING" not in app


def test_space_explains_pull_request_submission() -> None:
    index = read("space/index.html")
    guide = read("space/contribute.html")

    assert "Open as a pull request" in index
    assert "Open as a pull request" in guide
    assert "Do not commit" in guide

    for filename in REQUIRED_FILES:
        assert filename in index
        assert filename in guide


def test_space_has_downloadable_template() -> None:
    deployed = read(
        "space/submission-template.yaml"
    )

    source = read(
        "portal_template/submission.yaml"
    )

    assert deployed == source


def test_old_contribution_architecture_removed() -> None:
    contributing = read("CONTRIBUTING.md")
    readme = read("README.md")

    assert (
        "Fork this GitHub repository"
        not in contributing
    )

    assert (
        "Contributor Hugging Face Datasets"
        not in readme
    )

    assert (
        "data/embeddings/<embedding_id>"
        in contributing
    )
