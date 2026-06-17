import type { DOMFeatures } from "../types/analysis";

export function collectDomFeatures(): DOMFeatures {
  const forms = Array.from(document.forms);
  const links = Array.from(document.links);
  const currentHost = globalThis.location.hostname;
  const externalLinks = links.filter((link) => {
    try {
      return new URL(link.href, globalThis.location.href).hostname !== currentHost;
    } catch {
      return false;
    }
  });

  return {
    has_password_field: Boolean(document.querySelector('input[type="password"]')),
    num_forms: forms.length,
    external_form_action: forms.some((form) => hasExternalAction(form, currentHost)),
    num_iframes: document.querySelectorAll("iframe").length,
    external_links_ratio: links.length === 0 ? 0 : Number((externalLinks.length / links.length).toFixed(3)),
    has_hidden_inputs: Boolean(document.querySelector('input[type="hidden"]')),
  };
}

export function hasExternalAction(form: HTMLFormElement, currentHost: string): boolean {
  const rawAction = form.getAttribute("action");
  if (!rawAction) {
    return false;
  }

  try {
    const actionUrl = new URL(rawAction, globalThis.location.href);
    return actionUrl.protocol.startsWith("http") && actionUrl.hostname !== currentHost;
  } catch {
    return false;
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "PHISHLENS_COLLECT_DOM") {
    sendResponse({ ok: true, dom_features: collectDomFeatures() });
  }
  return false;
});

// Notify the service worker so it can update the action badge immediately on
// page load, without requiring the user to open the popup first.
try {
  await chrome.runtime.sendMessage({
    type: "PHISHLENS_PAGE_READY",
    url: globalThis.location.href,
    dom_features: collectDomFeatures(),
  });
} catch {
  // Service worker may not be active yet (e.g. fresh install). Ignored.
}
