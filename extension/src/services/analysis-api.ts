import type { AnalysisResponse, DOMFeatures, ExtensionSettings, FeedbackReport } from "../types/analysis";

export async function requestBackendAnalysis(
  url: string,
  domFeatures: DOMFeatures,
  settings: ExtensionSettings,
): Promise<AnalysisResponse | null> {
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), settings.requestTimeoutMs);

  try {
    const response = await fetch(`${settings.backendBaseUrl}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url,
        dom_features: domFeatures,
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as AnalysisResponse;
  } catch {
    return null;
  } finally {
    globalThis.clearTimeout(timeout);
  }
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
