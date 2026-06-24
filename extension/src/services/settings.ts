import browser from "webextension-polyfill";

import type { ExtensionSettings } from "../types/analysis";

const SETTINGS_KEY = "phishlens:settings";

export const DEFAULT_SETTINGS: ExtensionSettings = {
  backendBaseUrl: "http://localhost:8000",
  requestTimeoutMs: 2500,
  dangerOverlayEnabled: true,
};

export async function getExtensionSettings(): Promise<ExtensionSettings> {
  const items = await browser.storage.sync.get([SETTINGS_KEY]);
  return normalizeSettings(items[SETTINGS_KEY]);
}

export async function saveExtensionSettings(settings: ExtensionSettings): Promise<ExtensionSettings> {
  const normalized = normalizeSettings(settings);
  const permissionGranted = await requestBackendOriginPermission(normalized.backendBaseUrl);
  const settingsToStore = permissionGranted
    ? normalized
    : { ...normalized, backendBaseUrl: DEFAULT_SETTINGS.backendBaseUrl };

  await browser.storage.sync.set({ [SETTINGS_KEY]: settingsToStore });
  return settingsToStore;
}

export function normalizeSettings(value: unknown): ExtensionSettings {
  const candidate = typeof value === "object" && value !== null ? (value as Partial<ExtensionSettings>) : {};
  return {
    backendBaseUrl: normalizeBackendBaseUrl(candidate.backendBaseUrl ?? DEFAULT_SETTINGS.backendBaseUrl),
    requestTimeoutMs: clampTimeout(candidate.requestTimeoutMs ?? DEFAULT_SETTINGS.requestTimeoutMs),
    dangerOverlayEnabled: candidate.dangerOverlayEnabled ?? DEFAULT_SETTINGS.dangerOverlayEnabled,
  };
}

export function normalizeBackendBaseUrl(value: string): string {
  try {
    const parsed = new URL(value.trim());
    if (!["http:", "https:"].includes(parsed.protocol)) {
      return DEFAULT_SETTINGS.backendBaseUrl;
    }

    parsed.username = "";
    parsed.password = "";
    parsed.pathname = parsed.pathname.replace(/\/+$/, "");
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return DEFAULT_SETTINGS.backendBaseUrl;
  }
}

export async function requestBackendOriginPermission(baseUrl: string): Promise<boolean> {
  const origin = backendOriginPattern(baseUrl);
  if (!origin || isDefaultLocalBackend(baseUrl) || !browser.permissions?.request) {
    return true;
  }

  return Boolean(await browser.permissions.request({ origins: [origin] }));
}

function backendOriginPattern(baseUrl: string): string | null {
  try {
    const parsed = new URL(baseUrl);
    return `${parsed.origin}/*`;
  } catch {
    return null;
  }
}

function isDefaultLocalBackend(baseUrl: string): boolean {
  return baseUrl.startsWith("http://localhost:8000") || baseUrl.startsWith("http://127.0.0.1:8000");
}

function clampTimeout(value: number): number {
  if (!Number.isFinite(value)) {
    return DEFAULT_SETTINGS.requestTimeoutMs;
  }
  return Math.max(1000, Math.min(10000, Math.round(value)));
}
