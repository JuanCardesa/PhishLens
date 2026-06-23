import { describe, expect, it, vi } from "vitest";

import {
  DEFAULT_SETTINGS,
  getExtensionSettings,
  normalizeBackendBaseUrl,
  normalizeSettings,
  saveExtensionSettings,
} from "./settings";

// ---------------------------------------------------------------------------
// normalizeBackendBaseUrl
// ---------------------------------------------------------------------------

describe("normalizeBackendBaseUrl", () => {
  it("accepts a valid http URL", () => {
    expect(normalizeBackendBaseUrl("http://localhost:8000")).toBe("http://localhost:8000");
  });

  it("accepts a valid https URL", () => {
    expect(normalizeBackendBaseUrl("https://api.example.test")).toBe("https://api.example.test");
  });

  it("strips trailing slashes", () => {
    expect(normalizeBackendBaseUrl(" HTTPS://API.EXAMPLE.TEST/// ")).toBe("https://api.example.test");
  });

  it("strips credentials from the URL", () => {
    expect(normalizeBackendBaseUrl("https://user:pass@api.example.test/v1")).toBe("https://api.example.test/v1");
  });

  it("strips query string and hash", () => {
    expect(normalizeBackendBaseUrl("http://localhost:8000?debug=true#section")).toBe("http://localhost:8000");
  });

  it("falls back to default for non-http protocol", () => {
    expect(normalizeBackendBaseUrl("ftp://example.test")).toBe(DEFAULT_SETTINGS.backendBaseUrl);
  });

  it("falls back to default for an unparseable value", () => {
    expect(normalizeBackendBaseUrl("not-a-url")).toBe(DEFAULT_SETTINGS.backendBaseUrl);
  });

  it("falls back to default for an empty string", () => {
    expect(normalizeBackendBaseUrl("")).toBe(DEFAULT_SETTINGS.backendBaseUrl);
  });
});

// ---------------------------------------------------------------------------
// normalizeSettings
// ---------------------------------------------------------------------------

describe("normalizeSettings", () => {
  it("returns defaults for null input", () => {
    expect(normalizeSettings(null)).toEqual(DEFAULT_SETTINGS);
  });

  it("returns defaults for a non-object value", () => {
    expect(normalizeSettings(42)).toEqual(DEFAULT_SETTINGS);
  });

  it("returns defaults for an empty object", () => {
    expect(normalizeSettings({})).toEqual(DEFAULT_SETTINGS);
  });

  it("clamps requestTimeoutMs to [1000, 10000]", () => {
    expect(normalizeSettings({ requestTimeoutMs: 50000 }).requestTimeoutMs).toBe(10000);
    expect(normalizeSettings({ requestTimeoutMs: 0 }).requestTimeoutMs).toBe(1000);
    expect(normalizeSettings({ requestTimeoutMs: 3000 }).requestTimeoutMs).toBe(3000);
  });

  it("returns the default timeout for NaN or Infinity", () => {
    expect(normalizeSettings({ requestTimeoutMs: Number.NaN }).requestTimeoutMs).toBe(
      DEFAULT_SETTINGS.requestTimeoutMs,
    );
    expect(normalizeSettings({ requestTimeoutMs: Number.POSITIVE_INFINITY }).requestTimeoutMs).toBe(
      DEFAULT_SETTINGS.requestTimeoutMs,
    );
  });

  it("preserves dangerOverlayEnabled when explicitly set to false", () => {
    expect(normalizeSettings({ dangerOverlayEnabled: false }).dangerOverlayEnabled).toBe(false);
  });

  it("normalizes and preserves a valid backendBaseUrl", () => {
    const settings = normalizeSettings({
      backendBaseUrl: "http://localhost:8000/",
      requestTimeoutMs: 50000,
      dangerOverlayEnabled: false,
    });
    expect(settings.backendBaseUrl).toBe("http://localhost:8000");
    expect(settings.requestTimeoutMs).toBe(10000);
    expect(settings.dangerOverlayEnabled).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// chrome.storage integration
// ---------------------------------------------------------------------------

describe("settings storage", () => {
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
