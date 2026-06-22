chrome.runtime.onMessage.addListener((message) => {
  if (message?.type !== "PHISHLENS_SHOW_WARNING") {
    return false;
  }

  const existing = document.getElementById("phishlens-warning-overlay");
  if (existing) {
    existing.remove();
  }

  const dark = globalThis.matchMedia("(prefers-color-scheme: dark)").matches;
  const panelBg = dark ? "#1f2937" : "#ffffff";
  const panelText = dark ? "#f1f5f9" : "#172033";
  const bodyText = dark ? "#cbd5e1" : "#344054";
  const buttonBg = dark ? "#991b1b" : "#b42318";

  const overlay = document.createElement("div");
  overlay.id = "phishlens-warning-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-labelledby", "phishlens-warning-title");
  overlay.tabIndex = -1;
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
    `background:${panelBg}`,
    `color:${panelText}`,
    "box-shadow:0 18px 48px rgba(0,0,0,0.28)",
  ].join(";");

  const title = document.createElement("h2");
  title.id = "phishlens-warning-title";
  title.textContent = "High-risk phishing signals detected";
  title.style.cssText = "margin:0 0 8px;font-size:20px;line-height:1.2";

  const score = document.createElement("p");
  score.textContent = `Risk score: ${Number(message.riskScore ?? 0)}/100`;
  score.style.cssText = `margin:0 0 12px;color:${bodyText};font-size:14px`;

  const list = document.createElement("ul");
  list.style.cssText = `display:grid;gap:6px;margin:0 0 16px;padding-left:18px;color:${bodyText};font-size:13px`;
  for (const reason of Array.isArray(message.reasons) ? message.reasons : []) {
    const item = document.createElement("li");
    item.textContent = String(reason);
    list.append(item);
  }

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.textContent = "Continue";
  closeButton.style.cssText = [
    "min-height:38px",
    "width:100%",
    "border:0",
    "border-radius:8px",
    "color:#fff",
    `background:${buttonBg}`,
    "font:inherit",
    "font-weight:700",
    "cursor:pointer",
  ].join(";");
  closeButton.addEventListener("click", () => overlay.remove());

  overlay.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      overlay.remove();
    }
  });
  overlay.addEventListener("click", () => overlay.remove());
  panel.addEventListener("click", (event) => event.stopPropagation());
  panel.append(title, score, list, closeButton);
  overlay.append(panel);
  document.documentElement.append(overlay);
  closeButton.focus();

  return false;
});
