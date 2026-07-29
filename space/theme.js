(() => {
  "use strict";

  const storageKey = "gene-embeddings-theme";
  const root = document.documentElement;
  const button = document.getElementById("theme-toggle");

  if (!button) {
    return;
  }

  function readSavedTheme() {
    try {
      return window.localStorage.getItem(storageKey);
    } catch {
      return null;
    }
  }

  function saveTheme(theme) {
    try {
      window.localStorage.setItem(storageKey, theme);
    } catch {
      // The toggle still works when browser storage is unavailable.
    }
  }

  function applyTheme(theme) {
    const night = theme === "night";

    root.dataset.theme = night ? "night" : "day";

    button.textContent = night
      ? "🌙"
      : "☀️";

    button.setAttribute(
      "aria-pressed",
      String(night),
    );

    button.setAttribute(
      "aria-label",
      night
        ? "Current theme: dark. Switch to light theme"
        : "Current theme: light. Switch to dark theme",
    );

    button.setAttribute(
      "title",
      night
        ? "Switch to light theme"
        : "Switch to dark theme",
    );
  }

  const savedTheme = readSavedTheme();

  applyTheme(
    savedTheme === "night"
      ? "night"
      : "day",
  );

  button.addEventListener("click", () => {
    const nextTheme =
      root.dataset.theme === "night"
        ? "day"
        : "night";

    applyTheme(nextTheme);
    saveTheme(nextTheme);
  });
})();
