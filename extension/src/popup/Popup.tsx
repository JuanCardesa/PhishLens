import { useEffect, useState } from "react";

import { requestBackendAnalysis, submitFeedbackReport } from "../services/analysis-api";
import { DEFAULT_SETTINGS, getExtensionSettings } from "../services/settings";
import type { AnalysisMode, AnalysisResponse, DOMFeatures, ExtensionSettings, PopupAnalysis, RiskLabel } from "../types/analysis";
import { buildReportSummary } from "../utils/report-summary";
import { analyzeLocally } from "../utils/risk-score";
import { formatSignalScore, groupReasonsBySignal, primarySignalReason } from "../utils/signal-categories";
import "./popup.css";

const EMPTY_DOM_FEATURES: DOMFeatures = {
  has_password_field: false,
  num_forms: 0,
  external_form_action: false,
  num_iframes: 0,
  external_links_ratio: 0,
  has_hidden_inputs: false,
};

export function Popup() {
  const [analysis, setAnalysis] = useState<PopupAnalysis | null>(null);
  const [settings, setSettings] = useState<ExtensionSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackStatus, setFeedbackStatus] = useState<string | null>(null);
  const [reportStatus, setReportStatus] = useState<string | null>(null);

  useEffect(() => {
    void runAnalysis();
  }, []);

  const statusText = analysis ? labelText(analysis.label) : "Checking";
  const statusSymbol = analysis ? labelSymbol(analysis.label) : null;
  const signalGroups = analysis ? groupReasonsBySignal(analysis.reasons, analysis.sources, analysis.risk_breakdown) : [];

  async function runAnalysis() {
    setLoading(true);
    setError(null);

    try {
      const tab = await getActiveTab();
      const url = tab?.url;
      const currentSettings = await getExtensionSettings();
      setSettings(currentSettings);

      if (!tab?.id || !url || !url.startsWith("http")) {
        setError("This page cannot be analyzed by the extension.");
        setLoading(false);
        return;
      }

      const cached = await readCachedAnalysis(url);
      if (cached) {
        setAnalysis({ ...cached, mode: "cached" });
      }

      const domFeatures = await collectDomFeatures(tab.id);
      const localAnalysis = toPopupAnalysis(url, analyzeLocally(url, domFeatures), false, "local-only");
      setAnalysis(localAnalysis);

      const backendAnalysis = await requestBackendAnalysis(url, domFeatures, currentSettings);
      if (backendAnalysis) {
        const nextAnalysis = toPopupAnalysis(url, backendAnalysis, true, "backend-enriched");
        setAnalysis(nextAnalysis);
        await writeCachedAnalysis(url, nextAnalysis);
        await showDangerOverlay(tab.id, nextAnalysis, currentSettings);
      } else {
        const fallbackAnalysis = { ...localAnalysis, mode: "backend-unavailable" as const };
        setAnalysis(fallbackAnalysis);
        await writeCachedAnalysis(url, fallbackAnalysis);
        await showDangerOverlay(tab.id, fallbackAnalysis, currentSettings);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleFeedback(expectedLabel: RiskLabel) {
    if (!analysis) {
      return;
    }

    setFeedbackStatus("Sending feedback...");
    const ok = await submitFeedbackReport(
      {
        url: analysis.url,
        observed_label: analysis.label,
        expected_label: expectedLabel,
      },
      settings,
    );
    setFeedbackStatus(
      ok
        ? `Feedback sent: observed ${analysis.label}, expected ${expectedLabel}. No page content or form values were sent.`
        : "Backend unavailable. Feedback was not sent.",
    );
  }

  async function copyReport() {
    if (!analysis) {
      return;
    }

    try {
      await navigator.clipboard.writeText(buildReportSummary(analysis));
      setReportStatus("Report copied without full URL or page content.");
    } catch {
      setReportStatus("Clipboard unavailable. Try again from the browser popup.");
    }
  }

  function openOptionsPage() {
    chrome.runtime.openOptionsPage();
  }

  return (
    <main className="popup-shell">
      <header className="header">
        <div>
          <p className="eyebrow">PhishLens</p>
          <h1>Page risk</h1>
        </div>
        <div className="header-actions">
          <button className="tool-button" type="button" aria-label="Open settings" onClick={openOptionsPage}>
            Settings
          </button>
          <button className="tool-button" type="button" aria-label="Refresh analysis" onClick={() => void runAnalysis()}>
            Refresh
          </button>
        </div>
      </header>

      {error ? <div className="notice">{error}</div> : null}
      {analysis ? <div className={`mode-banner ${analysis.mode}`}>{modeBannerText(analysis)}</div> : null}

      <section
        className={`risk-panel ${analysis?.label ?? "safe"}`}
        aria-live="polite"
        aria-atomic="true"
        aria-label={analysis ? `Risk level: ${statusText}, score ${analysis.risk_score} out of 100` : "Awaiting analysis"}
      >
        <div>
          <span className="status">
            {statusSymbol ? <span className="status-symbol" aria-hidden="true">{statusSymbol}</span> : null}
            {statusText}
          </span>
          <strong className="score">{analysis?.risk_score ?? "--"}</strong>
        </div>
        <span className="score-label" aria-hidden="true">risk score</span>
      </section>

      <section className="details">
        <div className="url-block">
          <span>URL</span>
          <p>{analysis?.url ?? "Waiting for active tab..."}</p>
        </div>

        <div className="meta-grid">
          <div>
            <span>Confidence</span>
            <strong>{analysis ? `${Math.round(analysis.confidence * 100)}%` : "--"}</strong>
          </div>
          <div>
            <span>Backend</span>
            <strong>{analysis ? modeLabel(analysis.mode) : "--"}</strong>
          </div>
        </div>
        {analysis ? (
          <div className="source-list" aria-label="Analysis sources">
            {sourceList(analysis).map((source) => (
              <span key={source}>{source}</span>
            ))}
          </div>
        ) : null}
      </section>

      <section className="reasons">
        <h2>Signals</h2>
        {loading && !analysis ? <p className="muted">Analyzing current page...</p> : null}
        {analysis ? <p className="primary-signal">{primarySignalReason(signalGroups)}</p> : null}
        <div className="signal-groups">
          {signalGroups.map((group) => (
            <section className="signal-group" key={group.id}>
              <h3>
                <span>{group.title}</span>
                <strong>{formatSignalScore(group)}</strong>
              </h3>
              <ul>
                {group.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </section>

      <section className="feedback">
        <h2>Feedback</h2>
        <div className="feedback-actions">
          <button type="button" disabled={!analysis} onClick={() => void handleFeedback("safe")}>
            Mark as safe
          </button>
          <button type="button" disabled={!analysis} onClick={() => void handleFeedback("dangerous")}>
            Mark as phishing
          </button>
        </div>
        {feedbackStatus ? <p role="status">{feedbackStatus}</p> : null}
      </section>

      <section className="report-copy">
        <h2>Report</h2>
        <button type="button" disabled={!analysis} onClick={() => void copyReport()}>
          Copy report
        </button>
        {reportStatus ? <p role="status">{reportStatus}</p> : null}
      </section>
    </main>
  );
}

async function getActiveTab(): Promise<chrome.tabs.Tab | undefined> {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      resolve(tabs[0]);
    });
  });
}

async function collectDomFeatures(tabId: number): Promise<DOMFeatures> {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { type: "PHISHLENS_COLLECT_DOM" }, (response) => {
      if (chrome.runtime.lastError || !response?.ok) {
        resolve(EMPTY_DOM_FEATURES);
        return;
      }
      resolve(response.dom_features as DOMFeatures);
    });
  });
}

function toPopupAnalysis(
  url: string,
  response: AnalysisResponse,
  backendAvailable: boolean,
  mode: AnalysisMode,
): PopupAnalysis {
  return {
    ...response,
    url,
    backendAvailable,
    mode,
    analyzedAt: new Date().toISOString(),
  };
}

async function readCachedAnalysis(url: string): Promise<PopupAnalysis | null> {
  const key = await cacheKey(url);
  return new Promise((resolve) => {
    chrome.storage.local.get([key], (items) => {
      const cached = items[key] as PopupAnalysis | undefined;
      if (!cached) {
        resolve(null);
        return;
      }

      const ageMs = Date.now() - new Date(cached.analyzedAt).getTime();
      if (ageMs >= 5 * 60 * 1000) {
        chrome.storage.local.remove([key]);
        resolve(null);
        return;
      }
      resolve(cached);
    });
  });
}

async function writeCachedAnalysis(url: string, value: PopupAnalysis): Promise<void> {
  const key = await cacheKey(url);
  return new Promise((resolve) => {
    chrome.storage.local.set({ [key]: value }, () => resolve());
  });
}

export async function cacheKey(url: string): Promise<string> {
  const data = new TextEncoder().encode(url);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hex = Array.from(new Uint8Array(hashBuffer), (b) => b.toString(16).padStart(2, "0")).join("");
  return `analysis:${hex.slice(0, 16)}`;
}

export function modeLabel(mode: AnalysisMode): string {
  if (mode === "backend-enriched") {
    return "Backend enriched";
  }
  if (mode === "backend-unavailable") {
    return "Backend unavailable";
  }
  if (mode === "cached") {
    return "Cached";
  }
  if (mode === "checking") {
    return "Checking";
  }
  return "Local only";
}

export function modeBannerText(analysis: PopupAnalysis): string {
  if (analysis.mode === "backend-enriched") {
    return "Backend enrichment is active for this result.";
  }
  if (analysis.mode === "backend-unavailable") {
    const skipped: string[] = [];
    if (!analysis.sources.tls) skipped.push("TLS");
    if (!analysis.sources.phishtank) skipped.push("threat intelligence");
    if (!analysis.sources.ml) skipped.push("ML");
    const suffix = skipped.length > 0 ? ` ${skipped.join(", ")} ${skipped.length === 1 ? "was" : "were"} not checked.` : "";
    return `Backend unavailable — showing local heuristic analysis.${suffix}`;
  }
  if (analysis.mode === "cached") {
    return "Showing a recent cached result while refreshing.";
  }
  if (analysis.mode === "checking") {
    return "Checking the current page.";
  }
  return "Local-only analysis. Backend enrichment is not active.";
}

export function sourceList(analysis: PopupAnalysis): string[] {
  const sources = ["heuristics"];
  if (analysis.sources.tls) {
    sources.push("tls");
  }
  if (analysis.sources.phishtank) {
    sources.push("phishtank");
  }
  if (analysis.sources.ml) {
    sources.push("ml");
  }
  if (analysis.sources.demo) {
    sources.push("demo");
  }
  return sources;
}

export function labelText(label: RiskLabel): string {
  if (label === "dangerous") {
    return "Dangerous";
  }
  if (label === "suspicious") {
    return "Suspicious";
  }
  return "Safe";
}

export function labelSymbol(label: RiskLabel): string {
  if (label === "dangerous") {
    return "✕";
  }
  if (label === "suspicious") {
    return "!";
  }
  return "✓";
}

async function showDangerOverlay(
  tabId: number,
  value: PopupAnalysis,
  currentSettings: ExtensionSettings,
): Promise<void> {
  if (!currentSettings.dangerOverlayEnabled || value.label !== "dangerous") {
    return;
  }

  await executeScript(tabId, "warning/overlay.js");
  await sendOverlayMessage(tabId, {
    type: "PHISHLENS_SHOW_WARNING",
    riskScore: value.risk_score,
    reasons: value.reasons.slice(0, 4),
  });
}

async function executeScript(tabId: number, file: string): Promise<void> {
  return new Promise((resolve) => {
    chrome.scripting.executeScript({ target: { tabId }, files: [file] }, () => {
      resolve();
    });
  });
}

async function sendOverlayMessage(tabId: number, message: unknown): Promise<void> {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, message, () => {
      resolve();
    });
  });
}
