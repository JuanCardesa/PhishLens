import type { AnalysisResponse, DOMFeatures, ExtensionSettings, FeedbackReport } from "../types/analysis";

const MAX_ATTEMPTS = 2;
const RETRY_DELAY_MS = 200;

export async function requestBackendAnalysis(
  url: string,
  domFeatures: DOMFeatures,
  settings: ExtensionSettings,
): Promise<AnalysisResponse | null> {
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    const controller = new AbortController();
    const timeout = globalThis.setTimeout(() => controller.abort(), settings.requestTimeoutMs);

    try {
      const response = await fetch(`${settings.backendBaseUrl}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, dom_features: domFeatures }),
        signal: controller.signal,
      });

      if (!response.ok) {
        return null;
      }

      return (await response.json()) as AnalysisResponse;
    } catch (error) {
      // Timeouts are user-visible waits — do not add another full window on top.
      if (error instanceof DOMException && error.name === "AbortError") {
        return null;
      }
      if (attempt < MAX_ATTEMPTS) {
        await new Promise<void>((resolve) => globalThis.setTimeout(resolve, RETRY_DELAY_MS));
      }
    } finally {
      globalThis.clearTimeout(timeout);
    }
  }

  return null;
}

export async function submitFeedbackReport(
  report: FeedbackReport,
  settings: ExtensionSettings,
): Promise<boolean> {
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), settings.requestTimeoutMs);

  try {
    const response = await fetch(`${settings.backendBaseUrl}/report`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(report),
      signal: controller.signal,
    });

    return response.ok;
  } catch {
    return false;
  } finally {
    globalThis.clearTimeout(timeout);
  }
}
