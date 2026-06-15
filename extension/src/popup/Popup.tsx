import { useEffect, useMemo, useState } from "react";

import { requestBackendAnalysis } from "../services/analysis-api";
import type { AnalysisResponse, DOMFeatures, PopupAnalysis } from "../types/analysis";
import { analyzeLocally } from "../utils/risk-score";
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void runAnalysis();
  }, []);

  const statusText = useMemo(() => {
    if (!analysis) {
      return "Checking";
    }
    if (analysis.label === "dangerous") {
      return "Dangerous";
    }
    if (analysis.label === "suspicious") {
      return "Suspicious";
    }
    return "Safe";
  }, [analysis]);

  async function runAnalysis() {
    setLoading(true);
    setError(null);

    try {
      const tab = await getActiveTab();
      const url = tab?.url;

      if (!tab?.id || !url || !url.startsWith("http")) {
        setError("This page cannot be analyzed by the extension.");
        setLoading(false);
        return;
      }

      const cached = await readCachedAnalysis(url);
      if (cached) {
        setAnalysis(cached);
      }

      const domFeatures = await collectDomFeatures(tab.id);
      const localAnalysis = toPopupAnalysis(url, analyzeLocally(url, domFeatures), false);
      setAnalysis(localAnalysis);

      const backendAnalysis = await requestBackendAnalysis(url, domFeatures);
      if (backendAnalysis) {
        const nextAnalysis = toPopupAnalysis(url, backendAnalysis, true);
        setAnalysis(nextAnalysis);
        await writeCachedAnalysis(url, nextAnalysis);
      } else {
        await writeCachedAnalysis(url, localAnalysis);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="popup-shell">
      <header className="header">
        <div>
          <p className="eyebrow">PhishLens</p>
          <h1>Page risk</h1>
        </div>
        <button className="icon-button" type="button" aria-label="Refresh analysis" onClick={() => void runAnalysis()}>
          <span aria-hidden="true">R</span>
        </button>
      </header>

      {error ? <div className="notice">{error}</div> : null}

      <section className={`risk-panel ${analysis?.label ?? "safe"}`}>
        <div>
          <span className="status">{statusText}</span>
          <strong className="score">{analysis?.risk_score ?? "--"}</strong>
        </div>
        <span className="score-label">risk score</span>
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
            <strong>{analysis?.backendAvailable ? "Online" : "Local"}</strong>
          </div>
        </div>
      </section>

      <section className="reasons">
        <h2>Signals</h2>
        {loading && !analysis ? <p className="muted">Analyzing current page...</p> : null}
        <ul>
          {(analysis?.reasons ?? []).map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
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

function toPopupAnalysis(url: string, response: AnalysisResponse, backendAvailable: boolean): PopupAnalysis {
  return {
    ...response,
    url,
    backendAvailable,
    analyzedAt: new Date().toISOString(),
  };
}

async function readCachedAnalysis(url: string): Promise<PopupAnalysis | null> {
  const key = cacheKey(url);
  return new Promise((resolve) => {
    chrome.storage.local.get([key], (items) => {
      const cached = items[key] as PopupAnalysis | undefined;
      if (!cached) {
        resolve(null);
        return;
      }

      const ageMs = Date.now() - new Date(cached.analyzedAt).getTime();
      resolve(ageMs < 5 * 60 * 1000 ? cached : null);
    });
  });
}

async function writeCachedAnalysis(url: string, value: PopupAnalysis): Promise<void> {
  const key = cacheKey(url);
  return new Promise((resolve) => {
    chrome.storage.local.set({ [key]: value }, () => resolve());
  });
}

function cacheKey(url: string): string {
  let hash = 0;
  for (let index = 0; index < url.length; index += 1) {
    hash = (hash * 31 + url.charCodeAt(index)) >>> 0;
  }
  return `analysis:${hash.toString(16)}`;
}
