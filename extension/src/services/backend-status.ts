import type { BackendHealthResponse, BackendStatus, DiagnosticsResponse, ExtensionSettings } from "../types/analysis";

export async function requestBackendStatus(settings: ExtensionSettings): Promise<BackendStatus> {
  const checkedAt = new Date().toISOString();

  try {
    const health = await requestJson<BackendHealthResponse>(`${settings.backendBaseUrl}/health`, settings.requestTimeoutMs);
    if (health.status !== "ok") {
      return offlineStatus(checkedAt, "Backend health check returned an unexpected status.");
    }

    const diagnostics = await requestDiagnostics(settings);
    if (diagnostics === "disabled") {
      return {
        state: "diagnostics-disabled",
        service: health.service,
        diagnosticsAvailable: false,
        diagnostics: null,
        message: "Backend is online. Diagnostics are disabled.",
        checkedAt,
      };
    }

    if (!diagnostics) {
      return {
        state: "online",
        service: health.service,
        diagnosticsAvailable: false,
        diagnostics: null,
        message: "Backend is online. Diagnostics are unavailable.",
        checkedAt,
      };
    }

    return {
      state: "online",
      service: diagnostics.service || health.service,
      diagnosticsAvailable: true,
      diagnostics,
      message: "Backend is online with diagnostics enabled.",
      checkedAt,
    };
  } catch {
    return offlineStatus(checkedAt, "Backend is offline or unreachable.");
  }
}

export function totalCounter(diagnostics: DiagnosticsResponse | null, key: string): number {
  return diagnostics?.counters[key] ?? 0;
}

export function capabilityLabel(value: boolean, enabledLabel = "Enabled", fallbackLabel = "Fallback"): string {
  return value ? enabledLabel : fallbackLabel;
}

async function requestDiagnostics(settings: ExtensionSettings): Promise<DiagnosticsResponse | "disabled" | null> {
  try {
    return await requestJson<DiagnosticsResponse>(`${settings.backendBaseUrl}/diagnostics`, settings.requestTimeoutMs);
  } catch (error) {
    if (error instanceof HttpStatusError && error.status === 404) {
      return "disabled";
    }
    return null;
  }
}

async function requestJson<T>(url: string, timeoutMs: number): Promise<T> {
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: "GET",
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new HttpStatusError(response.status);
    }

    return (await response.json()) as T;
  } finally {
    globalThis.clearTimeout(timeout);
  }
}

function offlineStatus(checkedAt: string, message: string): BackendStatus {
  return {
    state: "offline",
    service: null,
    diagnosticsAvailable: false,
    diagnostics: null,
    message,
    checkedAt,
  };
}

class HttpStatusError extends Error {
  constructor(readonly status: number) {
    super(`HTTP ${status}`);
  }
}
