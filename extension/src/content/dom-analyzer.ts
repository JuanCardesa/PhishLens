import type { DOMFeatures } from "../types/analysis";

function collectDomFeatures(): DOMFeatures {
  const forms = Array.from(document.forms);
  const links = Array.from(document.links);
  const currentHost = window.location.hostname;
  const externalLinks = links.filter((link) => {
    try {
      return new URL(link.href, window.location.href).hostname !== currentHost;
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

function hasExternalAction(form: HTMLFormElement, currentHost: string): boolean {
  const rawAction = form.getAttribute("action");
  if (!rawAction) {
    return false;
  }

  try {
    const actionUrl = new URL(rawAction, window.location.href);
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
