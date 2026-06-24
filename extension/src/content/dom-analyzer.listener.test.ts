// @vitest-environment happy-dom
import { describe, expect, it, vi } from "vitest";

// Imported once: webextension-polyfill builds its wrapped `browser` object
// once per process (it predates MV3 and isn't designed for being re-imported
// against a freshly stubbed `chrome` global per test), so this file follows
// the same single-static-import pattern as dom-analyzer.spa.test.ts instead
// of vi.resetModules() + re-import.
import "./dom-analyzer";

type MessageListener = (
  message: { type?: string },
  sender: unknown,
  sendResponse: (response: unknown) => void,
) => boolean;

function getListener(): MessageListener {
  const addListenerMock = vi.mocked(chrome.runtime.onMessage.addListener);
  return addListenerMock.mock.calls[0][0] as unknown as MessageListener;
}

describe("dom-analyzer chrome.runtime.onMessage listener", () => {
  it("responds to PHISHLENS_COLLECT_DOM with dom features", async () => {
    const listener = getListener();
    const sendResponse = vi.fn();

    const handled = listener({ type: "PHISHLENS_COLLECT_DOM" }, {}, sendResponse);
    expect(handled).toBe(true);

    await vi.waitFor(() => expect(sendResponse).toHaveBeenCalled());
    expect(sendResponse).toHaveBeenCalledWith({
      ok: true,
      dom_features: expect.objectContaining({ num_forms: 0, has_password_field: false }),
    });
  });

  it("ignores messages that are not PHISHLENS_COLLECT_DOM", () => {
    const listener = getListener();
    const sendResponse = vi.fn();

    const handled = listener({ type: "SOMETHING_ELSE" }, {}, sendResponse);

    expect(handled).toBe(false);
    expect(sendResponse).not.toHaveBeenCalled();
  });

  it("ignores messages with no type", () => {
    const listener = getListener();
    const sendResponse = vi.fn();

    const handled = listener({}, {}, sendResponse);

    expect(handled).toBe(false);
    expect(sendResponse).not.toHaveBeenCalled();
  });
});
