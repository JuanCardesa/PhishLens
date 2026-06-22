// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from "vitest";

type MessageListener = (
  message: { type?: string },
  sender: unknown,
  sendResponse: (response: unknown) => void,
) => boolean;

describe("dom-analyzer chrome.runtime.onMessage listener", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  async function importAndGetListener(): Promise<MessageListener> {
    await import("./dom-analyzer");
    const addListenerMock = vi.mocked(chrome.runtime.onMessage.addListener);
    return addListenerMock.mock.calls[0][0] as unknown as MessageListener;
  }

  it("responds to PHISHLENS_COLLECT_DOM with dom features and returns false", async () => {
    const listener = await importAndGetListener();
    const sendResponse = vi.fn();

    const handled = listener({ type: "PHISHLENS_COLLECT_DOM" }, {}, sendResponse);

    expect(sendResponse).toHaveBeenCalledWith({
      ok: true,
      dom_features: expect.objectContaining({ num_forms: 0, has_password_field: false }),
    });
    expect(handled).toBe(false);
  });

  it("ignores messages that are not PHISHLENS_COLLECT_DOM", async () => {
    const listener = await importAndGetListener();
    const sendResponse = vi.fn();

    listener({ type: "SOMETHING_ELSE" }, {}, sendResponse);

    expect(sendResponse).not.toHaveBeenCalled();
  });

  it("ignores messages with no type", async () => {
    const listener = await importAndGetListener();
    const sendResponse = vi.fn();

    listener({}, {}, sendResponse);

    expect(sendResponse).not.toHaveBeenCalled();
  });
});
