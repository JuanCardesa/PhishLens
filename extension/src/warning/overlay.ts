chrome.runtime.onMessage.addListener((message) => {
  if (message?.type !== "PHISHLENS_SHOW_WARNING") {
    return false;
  }

  const existing = document.getElementById("phishlens-warning-overlay");
  if (existing) {
    existing.remove();
  }

  const overlay = document.createElement("div");
  overlay.id = "phishlens-warning-overlay";
  overlay.style.cssText = [
    "position:fixed",
    "inset:0",
    "z-index:2147483647",
    "display:grid",
    "place-items:center",
    "background:rgba(16,24,40,0.72)",
    "font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif",
  ].join(";");

  const panel = document.createElement("div");
  panel.style.cssText = [
    "width:min(420px,calc(100vw - 32px))",
    "padding:20px",
    "border-radius:8px",
    "background:#fff",
    "color:#172033",
    "box-shadow:0 18px 48px rgba(0,0,0,0.28)",
  ].join(";");
  panel.textContent = "PhishLens detected high-risk signals on this page.";

  overlay.addEventListener("click", () => overlay.remove());
  overlay.append(panel);
  document.documentElement.append(overlay);

  return false;
});
