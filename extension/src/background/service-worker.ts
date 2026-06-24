import browser from "webextension-polyfill";

import type { DOMFeatures, RiskLabel } from "../types/analysis";
import { analyzeLocally } from "../utils/risk-score";

const EMPTY_DOM_FEATURES: DOMFeatures = {
  has_password_field: false,
  num_forms: 0,
  external_form_action: false,
  num_iframes: 0,
  external_links_ratio: 0,
  has_hidden_inputs: false,
  brand_text_mismatch: false,
  favicon_hotlinked_brand: false,
};

function updateActionBadge(tabId: number, label: RiskLabel): void {
  const config: Record<RiskLabel, { text: string; color: string }> = {
    safe: { text: "", color: "#22c55e" },
    suspicious: { text: "?", color: "#f59e0b" },
    dangerous: { text: "!", color: "#ef4444" },
  };
  const { text, color } = config[label];
  // webextension-polyfill predates the MV3-only `action` namespace, so it
  // passes `browser.action` through to the underlying engine's own API
  // unwrapped. Both Chrome (native Promise support since MV96) and Firefox
  // (native `browser.action`) already return promises here without a callback.
  void browser.action.setBadgeText({ tabId, text });
  void browser.action.setBadgeBackgroundColor({ tabId, color });
}

browser.runtime.onInstalled.addListener(() => {
  void browser.storage.local.set({
    phishlensInstalledAt: new Date().toISOString(),
  });
});

browser.runtime.onMessage.addListener((rawMessage: unknown, sender: { tab?: { id?: number } }) => {
  const message = rawMessage as { type?: string; url?: unknown; dom_features?: unknown };

  if (message?.type === "PHISHLENS_PING") {
    return Promise.resolve({ ok: true });
  }

  if (message?.type === "PHISHLENS_PAGE_READY" && sender.tab?.id !== undefined) {
    const tabId = sender.tab.id;
    const url = typeof message.url === "string" ? message.url : "";
    const domFeatures =
      message.dom_features != null ? (message.dom_features as DOMFeatures) : EMPTY_DOM_FEATURES;
    const result = analyzeLocally(url, domFeatures);
    updateActionBadge(tabId, result.label);
    return Promise.resolve({ ok: true });
  }

  return undefined;
});
