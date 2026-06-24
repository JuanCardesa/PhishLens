import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

type StorageArea = {
  data: Record<string, unknown>;
  get: (keys: string[] | string, callback: (items: Record<string, unknown>) => void) => void;
  set: (items: Record<string, unknown>, callback?: () => void) => void;
  remove: (keys: string[] | string, callback?: () => void) => void;
};

function createStorageArea(): StorageArea {
  return {
    data: {},
    get(keys, callback) {
      const keyList = Array.isArray(keys) ? keys : [keys];
      callback(Object.fromEntries(keyList.map((key) => [key, this.data[key]])));
    },
    set(items, callback) {
      this.data = { ...this.data, ...items };
      callback?.();
    },
    remove(keys, callback) {
      const keyList = Array.isArray(keys) ? keys : [keys];
      for (const key of keyList) {
        delete this.data[key];
      }
      callback?.();
    },
  };
}

// webextension-polyfill is a singleton CJS module: it builds its wrapped
// `browser` object exactly once per worker process, the first time any test
// file imports it, by capturing a reference to `globalThis.chrome` and its
// sub-objects (chrome.runtime, chrome.runtime.onMessage, chrome.tabs, ...) at
// that moment. If `beforeEach` replaced the whole `chrome` object with a
// brand-new one every test (as this file used to), the polyfill would keep
// calling methods on the stale, orphaned first-test object forever, and the
// freshly stubbed object the current test inspects would silently see zero
// calls. So `chrome` and all its nested namespace objects are created ONCE
// here at module scope with stable identity; only their leaf vi.fn()
// properties get reset per test, which the polyfill reads dynamically on
// every call (see wrapEvent/wrapObject internals — target.addListener(...)
// resolves the method fresh on each invocation, not at wrap time).
const chromeStub = {
  permissions: {
    request: vi.fn((_permissions: unknown, callback?: (granted: boolean) => void) => callback?.(true)),
  },
  runtime: {
    id: "phishlens-test-extension-id",
    lastError: null as unknown,
    openOptionsPage: vi.fn(),
    sendMessage: vi.fn().mockResolvedValue(undefined),
    onMessage: { addListener: vi.fn() },
    onInstalled: { addListener: vi.fn() },
  },
  storage: {
    sync: createStorageArea(),
    local: createStorageArea(),
  },
  tabs: {
    query: vi.fn(),
    sendMessage: vi.fn(),
  },
  scripting: {
    executeScript: vi.fn(),
  },
};

vi.stubGlobal("chrome", chromeStub);

beforeEach(() => {
  chromeStub.permissions.request = vi.fn((_permissions: unknown, callback?: (granted: boolean) => void) =>
    callback?.(true),
  );
  chromeStub.runtime.lastError = null;
  chromeStub.runtime.openOptionsPage = vi.fn();
  chromeStub.runtime.sendMessage = vi.fn().mockResolvedValue(undefined);
  // onMessage/onInstalled addListener are deliberately NOT reset here: source
  // modules (dom-analyzer.ts, overlay.ts, service-worker.ts) register exactly
  // one listener at module-load time, same as in a real browser, and several
  // tests retrieve that registered listener via .mock.calls[0][0]. Resetting
  // the mock per test would erase that recorded call before any test ran.
  chromeStub.storage.sync = createStorageArea();
  chromeStub.storage.local = createStorageArea();
  chromeStub.tabs.query = vi.fn();
  chromeStub.tabs.sendMessage = vi.fn();
  chromeStub.scripting.executeScript = vi.fn();
});

afterEach(() => {
  cleanup();
});
