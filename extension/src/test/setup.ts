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

// Stub chrome at top-level so modules that register listeners at import time
// (e.g. dom-analyzer.ts) can safely access chrome.runtime.
vi.stubGlobal("chrome", {
  permissions: { request: vi.fn((_permissions, callback: (granted: boolean) => void) => callback(true)) },
  runtime: {
    lastError: null,
    openOptionsPage: vi.fn(),
    sendMessage: vi.fn().mockResolvedValue(undefined),
    onMessage: { addListener: vi.fn() },
  },
  storage: { sync: createStorageArea(), local: createStorageArea() },
  tabs: { query: vi.fn(), sendMessage: vi.fn() },
  scripting: { executeScript: vi.fn() },
});

beforeEach(() => {
  const sync = createStorageArea();
  const local = createStorageArea();

  vi.stubGlobal("chrome", {
    permissions: {
      request: vi.fn((_permissions, callback) => callback(true)),
    },
    runtime: {
      lastError: null,
      openOptionsPage: vi.fn(),
      sendMessage: vi.fn().mockResolvedValue(undefined),
      onMessage: { addListener: vi.fn() },
    },
    storage: {
      sync,
      local,
    },
    tabs: {
      query: vi.fn(),
      sendMessage: vi.fn(),
    },
    scripting: {
      executeScript: vi.fn(),
    },
  });
});

afterEach(() => {
  cleanup();
});
