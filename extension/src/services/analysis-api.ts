import type { AnalysisResponse, DOMFeatures } from "../types/analysis";

const API_BASE_URL = "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 2500;

export async function requestBackendAnalysis(
  url: string,
  domFeatures: DOMFeatures,
): Promise<AnalysisResponse | null> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/analyze`, {
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
    window.clearTimeout(timeout);
  }
}
