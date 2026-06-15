import { describe, expect, it, vi } from "vitest";

import {
  DEFAULT_SETTINGS,
  getExtensionSettings,
  normalizeBackendBaseUrl,
  normalizeSettings,
  saveExtensionSettings,
} from "./settings";

describe("settings", () => {
  it("normalizes backend URLs", () => {
    expect(normalizeBackendBaseUrl(" HTTPS://API.EXAMPLE.TEST/// ")).toBe("https://api.example.test");
    expect(normalizeBackendBaseUrl("https://user:pass@api.example.test/v1")).toBe("https://api.example.test/v1");
    expect(normalizeBackendBaseUrl("ftp://example.test")).toBe(DEFAULT_SETTINGS.backendBaseUrl);
  });

  it("clamps timeout and preserves overlay preference", () => {
    const settings = normalizeSettings({
      backendBaseUrl: "http://localhost:8000/",
      requestTimeoutMs: 50000,
      dangerOverlayEnabled: false,
    });

    expect(settings.requestTimeoutMs).toBe(10000);
    expect(settings.dangerOverlayEnabled).toBe(false);
  });

  it("stores and reads settings from chrome.storage.sync", async () => {
    await saveExtensionSettings({
      backendBaseUrl: "https://api.example.test",
      requestTimeoutMs: 3000,
      dangerOverlayEnabled: false,
    });

    await expect(getExtensionSettings()).resolves.toEqual({
      backendBaseUrl: "https://api.example.test",
      requestTimeoutMs: 3000,
      dangerOverlayEnabled: false,
    });
  });

  it("falls back to the default backend when optional host permission is denied", async () => {
    chrome.permissions.request = vi.fn(
      (_permissions: chrome.permissions.Permissions, callback?: (granted: boolean) => void) => {
        callback?.(false);
      },
    ) as unknown as typeof chrome.permissions.request;

    await expect(
      saveExtensionSettings({
        backendBaseUrl: "https://api.example.test",
        requestTimeoutMs: 3000,
        dangerOverlayEnabled: false,
      }),
    ).resolves.toEqual({
      backendBaseUrl: DEFAULT_SETTINGS.backendBaseUrl,
      requestTimeoutMs: 3000,
      dangerOverlayEnabled: false,
    });
  });
});
