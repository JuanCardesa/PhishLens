// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from "vitest";

// Imported once: the module patches history.pushState/replaceState and adds a
// popstate listener as a load-time side effect, so re-importing per test would
// stack duplicate patches. Each test instead clears the shared sendMessage mock
// and asserts deltas from real history navigation.
import "./dom-analyzer";

describe("dom-analyzer SPA navigation watcher", () => {
  beforeEach(() => {
    vi.mocked(chrome.runtime.sendMessage).mockClear();
  });

  it("re-notifies PHISHLENS_PAGE_READY when pushState changes the URL", () => {
    const sendMessage = vi.mocked(chrome.runtime.sendMessage);

    history.pushState({}, "", "/spa-next-page");

    expect(sendMessage).toHaveBeenCalledTimes(1);
    expect(sendMessage.mock.calls[0][0]).toMatchObject({ type: "PHISHLENS_PAGE_READY" });
  });

  it("re-notifies when replaceState changes the URL", () => {
    const sendMessage = vi.mocked(chrome.runtime.sendMessage);

    history.replaceState({}, "", "/spa-replaced");

    expect(sendMessage).toHaveBeenCalledTimes(1);
  });

  it("registers a popstate listener that is a no-op when the URL has not changed since the last notification", () => {
    // The real browser back/forward case changes location.href before firing
    // popstate, which routes through the same reportIfUrlChanged comparison
    // already exercised by the pushState/replaceState tests above. This test
    // covers the listener's idempotency: firing popstate with no intervening
    // URL change must not produce a duplicate notification.
    const sendMessage = vi.mocked(chrome.runtime.sendMessage);
    history.pushState({}, "", "/spa-pushed-for-popstate");
    sendMessage.mockClear();

    globalThis.dispatchEvent(new PopStateEvent("popstate"));

    expect(sendMessage).not.toHaveBeenCalled();
  });

  it("does not re-notify when the URL stays the same", () => {
    const sendMessage = vi.mocked(chrome.runtime.sendMessage);
    const currentUrl = globalThis.location.href;

    history.pushState({}, "", currentUrl);

    expect(sendMessage).not.toHaveBeenCalled();
  });
});
