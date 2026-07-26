(() => {
  "use strict";
  const GITHUB_CONTRIBUTING = "https://github.com/DanielTabaresLopez/Gene-Embeddings-Contributions/blob/main/CONTRIBUTING.md";
  const DATASET_BASE = "https://huggingface.co/datasets/embeddingsSSRF/gene_embeddings_staging/tree/main/";

  const grid = document.getElementById("grid");
  const search = document.getElementById("search");
  const category = document.getElementById("category");
  const dialog = document.getElementById("detail-dialog");
  const detail = document.getElementById("detail-content");
  let catalog = [];

  document.getElementById("contribute-link").href = GITHUB_CONTRIBUTING;
  document.getElementById("contribute-link-bottom").href = GITHUB_CONTRIBUTING;
  document.getElementById("close-detail").addEventListener("click", () => dialog.close());

  const escapeHtml = (value) => {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
  };

  function render() {
    const term = search.value.trim().toLowerCase();
    const selected = category.value;
    const items = catalog.filter((item) => {
      if (selected !== "All" && item.category !== selected) return false;
      const haystack = `${item.name} ${item.category} ${item.modality} ${item.algorithm} ${item.description}`.toLowerCase();
      return !term || haystack.includes(term);
    });
    document.getElementById("result-count").textContent = `${items.length} of ${catalog.length} embedding sets`;
    grid.innerHTML = "";
    items.forEach((item) => {
      const card = document.createElement("button");
      card.className = "card";
      card.innerHTML = `
        <span class="badge">${escapeHtml(item.category)}</span>
        <h3>${escapeHtml(item.name)}</h3>
        <p>${escapeHtml(item.description || "No description provided.")}</p>
        <div class="metrics">
          <span><strong>${Number(item.n_genes).toLocaleString()}</strong> genes</span>
          <span><strong>${Number(item.n_dims).toLocaleString()}</strong> dims</span>
          <span><strong>${item.coverage_pct}%</strong> coverage</span>
        </div>`;
      card.addEventListener("click", () => openDetail(item));
      grid.appendChild(card);
    });
  }

  function openDetail(item) {
    const path = item.dataset_path || `data/embeddings/${item.id}`;
    const packageUrl =
      item.package_url || `${DATASET_BASE}${encodeURI(path)}`;
    detail.innerHTML = `
      <p class="badge">${escapeHtml(item.category)}</p>
      <h2>${escapeHtml(item.name)}</h2>
      <p>${escapeHtml(item.description || "")}</p>
      <div class="detail-grid">
        <div><strong>${Number(item.n_genes).toLocaleString()}</strong>genes</div>
        <div><strong>${Number(item.n_dims).toLocaleString()}</strong>dimensions</div>
        <div><strong>${item.coverage_pct}%</strong>coverage</div>
      </div>
      <p><b>Modality:</b> ${escapeHtml(item.modality || "—")}</p>
      <p><b>Method:</b> ${escapeHtml(item.algorithm || "—")}</p>
      <p><b>QC:</b> ${escapeHtml(item.qc_status || "legacy package")}</p>
      <p><b>License:</b> ${escapeHtml(item.license || "see package metadata")}</p>
      <p><b>Source Dataset:</b> ${escapeHtml(item.source_dataset || "—")}</p>
      <a class="button primary" href="${escapeHtml(packageUrl)}" target="_blank" rel="noopener noreferrer">Open package files</a>`;
    dialog.showModal();
  }

  async function init() {
    const response = await fetch("catalog.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Could not load catalog.json (${response.status})`);
    catalog = await response.json();
    const categories = [...new Set(catalog.map((item) => item.category))].sort();
    categories.forEach((value) => category.add(new Option(value, value)));
    document.getElementById("stat-count").textContent = catalog.length.toLocaleString();
    document.getElementById("stat-genes").textContent = Math.max(...catalog.map((item) => Number(item.n_genes) || 0)).toLocaleString();
    const dims = catalog.map((item) => Number(item.n_dims) || 0);
    document.getElementById("stat-dims").textContent = `${Math.min(...dims).toLocaleString()}–${Math.max(...dims).toLocaleString()}`;
    render();
  }

  search.addEventListener("input", render);
  category.addEventListener("change", render);
  init().catch((error) => {
    grid.innerHTML = `<p>Catalog failed to load: ${escapeHtml(error.message)}</p>`;
  });
})();
