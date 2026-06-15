import { describe, expect, it } from "vitest";

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
});
