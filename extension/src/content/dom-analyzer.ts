import browser from "webextension-polyfill";

import type { DOMFeatures } from "../types/analysis";
import { KNOWN_BRAND_DOMAINS, MIN_BRAND_NAME_LENGTH, getRegistrableDomain } from "../utils/url-features";

export function collectDomFeatures(): DOMFeatures {
  const forms = Array.from(document.forms);
  const links = Array.from(document.links);
  const currentOrigin = globalThis.location.origin;
  const externalLinks = links.filter((link) => {
    try {
      return new URL(link.href, globalThis.location.href).origin !== currentOrigin;
    } catch {
      return false;
    }
  });

  return {
    has_password_field: Boolean(document.querySelector('input[type="password"]')),
    num_forms: forms.length,
    external_form_action: forms.some((form) => hasExternalAction(form, currentOrigin)),
    num_iframes: document.querySelectorAll("iframe").length,
    external_links_ratio: links.length === 0 ? 0 : Number((externalLinks.length / links.length).toFixed(3)),
    has_hidden_inputs: Boolean(document.querySelector('input[type="hidden"]')),
    ...detectBrandImpersonation(globalThis.location.hostname),
  };
}

/**
 * Detects two brand-impersonation patterns, both purely from already-loaded
 * DOM state (no network fetch, no new permission):
 *  - brand_text_mismatch: visible page text names a known brand whose real
 *    domain differs from this page's domain (catches cloned login pages on
 *    unrelated/throwaway domains that typosquat detection wouldn't flag,
 *    since the domain string itself bears no lexical resemblance).
 *  - favicon_hotlinked_brand: the favicon <link> points at a different
 *    origin that is itself a known brand domain (a common phishing-kit
 *    laziness pattern — hotlinking the real brand's icon instead of copying
 *    it). This intentionally avoids fetching/hashing favicon bytes, which
 *    would require cross-origin CORS access and a maintained hash database.
 */
function detectBrandImpersonation(currentHostname: string): {
  brand_text_mismatch: boolean;
  favicon_hotlinked_brand: boolean;
} {
  const currentDomain = getRegistrableDomain(currentHostname);
  const visibleText = [
    document.title,
    document.querySelector('meta[property="og:site_name"]')?.getAttribute("content"),
    document.querySelector("h1")?.textContent,
  ]
    .filter((value): value is string => Boolean(value))
    .join(" ")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");

  const brandTextMismatch = KNOWN_BRAND_DOMAINS.some((brandDomain) => {
    const brandLabel = brandDomain.split(".")[0];
    return (
      brandLabel.length >= MIN_BRAND_NAME_LENGTH &&
      visibleText.includes(brandLabel) &&
      !isSameBrandDomain(currentDomain, brandDomain)
    );
  });

  const faviconHref = document.querySelector('link[rel~="icon"]')?.getAttribute("href");
  let faviconHotlinkedBrand = false;
  if (faviconHref) {
    try {
      const faviconDomain = getRegistrableDomain(new URL(faviconHref, globalThis.location.href).hostname);
      faviconHotlinkedBrand =
        !isSameBrandDomain(currentDomain, faviconDomain) && KNOWN_BRAND_DOMAINS.includes(faviconDomain);
    } catch {
      faviconHotlinkedBrand = false;
    }
  }

  return { brand_text_mismatch: brandTextMismatch, favicon_hotlinked_brand: faviconHotlinkedBrand };
}

function isSameBrandDomain(currentDomain: string, brandDomain: string): boolean {
  if (currentDomain === brandDomain) {
    return true;
  }

  return domainLabel(currentDomain) === domainLabel(brandDomain);
}

function domainLabel(domain: string): string {
  return domain.split(".")[0] ?? "";
}

export function hasExternalAction(form: HTMLFormElement, currentOrigin: string): boolean {
  const rawAction = form.getAttribute("action");
  if (!rawAction) {
    return false;
  }

  try {
    const actionUrl = new URL(rawAction, globalThis.location.href);
    return actionUrl.protocol.startsWith("http") && actionUrl.origin !== currentOrigin;
  } catch {
    return false;
  }
}

browser.runtime.onMessage.addListener((rawMessage: unknown) => {
  if ((rawMessage as { type?: string })?.type === "PHISHLENS_COLLECT_DOM") {
    return Promise.resolve({ ok: true, dom_features: collectDomFeatures() });
  }
  return undefined;
});

// Notify the service worker so the badge updates without the popup.
// MV3 content scripts are declared without "type": "module" in manifest.json and
// therefore run as classic scripts. Top-level await is a syntax error in classic
// scripts, so an async IIFE is the correct pattern here.
// NOSONAR S7785 — intentional: top-level await would break MV3 classic script loading.
function notifyPageReady(): void {
  void (async () => {
    try {
      await browser.runtime.sendMessage({
        type: "PHISHLENS_PAGE_READY",
        url: globalThis.location.href,
        dom_features: collectDomFeatures(),
      });
    } catch {
      // Service worker may not be active yet (e.g. fresh install). Ignored.
    }
  })();
}

notifyPageReady();

// SPA routers change the URL via history.pushState/replaceState without a full
// page (re)load, so the document_idle injection above only ever fires once per
// real navigation and the badge goes stale. Patching the History API and
// listening for popstate re-notifies on every URL change without requesting
// the "webNavigation" permission this would otherwise need from the background
// service worker.
function watchSpaNavigation(): void {
  let lastUrl = globalThis.location.href;

  function reportIfUrlChanged(): void {
    if (globalThis.location.href === lastUrl) {
      return;
    }
    lastUrl = globalThis.location.href;
    notifyPageReady();
  }

  for (const method of ["pushState", "replaceState"] as const) {
    const original = history[method];
    history[method] = function (...args: Parameters<History[typeof method]>) {
      const result = (original as (...a: typeof args) => unknown).apply(this, args);
      reportIfUrlChanged();
      return result;
    };
  }

  globalThis.addEventListener("popstate", reportIfUrlChanged);
}

watchSpaNavigation();
