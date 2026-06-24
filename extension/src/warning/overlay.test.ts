// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from "vitest";

// Imported once, same reasoning as dom-analyzer.listener.test.ts: the
// webextension-polyfill wrapped `browser` object is built once per process
// against whichever `chrome` stub existed at first import, so re-importing
// per test after vi.resetModules() silently binds to a stale mock.
import { PHISHLENS_WARNING_OVERLAY_ID } from "./overlay";

type MessageListener = (message: { type?: string; riskScore?: number; reasons?: string[] }) => boolean;

function getListener(): MessageListener {
  const addListenerMock = vi.mocked(chrome.runtime.onMessage.addListener);
  return addListenerMock.mock.calls[0][0] as unknown as MessageListener;
}

describe("warning overlay", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    document.getElementById(PHISHLENS_WARNING_OVERLAY_ID)?.remove();
  });

  it("shows an actionable instruction not to enter sensitive data, alongside the technical reasons", () => {
    const listener = getListener();

    listener({ type: "PHISHLENS_SHOW_WARNING", riskScore: 92, reasons: ["Domain registered 2 days ago"] });

    const panelText = document.getElementById(PHISHLENS_WARNING_OVERLAY_ID)?.textContent ?? "";
    expect(panelText).toContain("Do not enter your password, card details, or any personal information");
    expect(panelText).toContain("Risk score: 92/100");
    expect(panelText).toContain("Domain registered 2 days ago");
  });

  it("ignores unrelated messages", () => {
    const listener = getListener();

    listener({ type: "SOMETHING_ELSE" });

    expect(document.getElementById(PHISHLENS_WARNING_OVERLAY_ID)).toBeNull();
  });
});
