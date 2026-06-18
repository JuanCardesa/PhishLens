import { type FormEvent, useEffect, useState } from "react";

import { capabilityLabel, requestBackendStatus, totalCounter } from "../services/backend-status";
import { DEFAULT_SETTINGS, getExtensionSettings, saveExtensionSettings } from "../services/settings";
import type { BackendStatus, DiagnosticsCapabilities, ExtensionSettings } from "../types/analysis";
import "./options.css";

export function diagnosticsLabelFor(backendStatus: BackendStatus | null): string {
  if (backendStatus?.diagnosticsAvailable) return "Enabled";
  if (backendStatus?.state === "diagnostics-disabled") return "Disabled";
  return "Unavailable";
}

export function Options() {
  const [settings, setSettings] = useState<ExtensionSettings>(DEFAULT_SETTINGS);
  const [status, setStatus] = useState<string>("Loading settings...");
  const [backendStatus, setBackendStatus] = useState<BackendStatus | null>(null);
  const [backendStatusLoading, setBackendStatusLoading] = useState(false);
  const diagnosticsLabel = diagnosticsLabelFor(backendStatus);

  useEffect(() => {
    void getExtensionSettings().then((storedSettings) => {
      setSettings(storedSettings);
      setStatus("Settings loaded");
      void refreshBackendStatus(storedSettings);
    });
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const saved = await saveExtensionSettings(settings);
    setSettings(saved);
    setStatus("Settings saved");
    await refreshBackendStatus(saved);
  }

  async function refreshBackendStatus(nextSettings = settings) {
    setBackendStatusLoading(true);
    const nextStatus = await requestBackendStatus(nextSettings);
    setBackendStatus(nextStatus);
    setBackendStatusLoading(false);
  }

  return (
    <main className="options-shell">
      <header>
        <p className="eyebrow">PhishLens</p>
        <h1>Settings</h1>
      </header>

      <form className="settings-form" onSubmit={handleSubmit}>
        <label>
          <span>Backend URL</span>
          <input
            type="url"
            value={settings.backendBaseUrl}
            onChange={(event) => setSettings({ ...settings, backendBaseUrl: event.target.value })}
            placeholder="http://localhost:8000"
            required
          />
        </label>

        <label>
          <span>Timeout</span>
          <input
            type="number"
            min="1000"
            max="10000"
            step="250"
            value={settings.requestTimeoutMs}
            onChange={(event) => setSettings({ ...settings, requestTimeoutMs: Number(event.target.value) })}
          />
        </label>

        <label className="toggle-row">
          <span>Danger overlay</span>
          <input
            type="checkbox"
            checked={settings.dangerOverlayEnabled}
            onChange={(event) => setSettings({ ...settings, dangerOverlayEnabled: event.target.checked })}
          />
        </label>

        <button type="submit">Save settings</button>
      </form>

      <section className={`backend-status ${backendStatus?.state ?? "offline"}`} aria-label="Backend status">
        <div className="section-header">
          <div>
            <p className="section-kicker">Backend</p>
            <h2>Status</h2>
          </div>
          <button type="button" className="secondary-button" onClick={() => void refreshBackendStatus()}>
            {backendStatusLoading ? "Checking..." : "Refresh"}
          </button>
        </div>

        <p className="backend-message">{backendStatus?.message ?? "Backend status has not been checked yet."}</p>

        <div className="status-grid">
          <StatusItem label="Service" value={backendStatus?.service ?? "Unavailable"} />
          <StatusItem label="Diagnostics" value={diagnosticsLabel} />
          <StatusItem
            label="Analyze"
            value={`${totalCounter(backendStatus?.diagnostics ?? null, "analysis_requests")} requests`}
          />
          <StatusItem
            label="Rate limits"
            value={`${totalCounter(backendStatus?.diagnostics ?? null, "rate_limited_requests")} hits`}
          />
        </div>

        <CapabilityGrid capabilities={backendStatus?.diagnostics?.capabilities ?? null} />
      </section>

      <p className="status-line" role="status">
        {status}
      </p>
    </main>
  );
}

function StatusItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CapabilityGrid({ capabilities }: { capabilities: DiagnosticsCapabilities | null }) {
  return (
    <div className="capability-grid" aria-label="Backend capabilities">
      <StatusItem
        label="Threat intel"
        value={capabilities ? capabilityLabel(capabilities.threat_intel_enabled, "Enabled", "Disabled") : "Unknown"}
      />
      <StatusItem
        label="TLS"
        value={capabilities ? capabilityLabel(capabilities.tls_analysis_enabled, "Enabled", "Disabled") : "Unknown"}
      />
      <StatusItem
        label="ML"
        value={capabilities ? capabilityLabel(capabilities.ml_model_available, "Model loaded", "Heuristic fallback") : "Unknown"}
      />
      <StatusItem
        label="Demo source"
        value={capabilities ? capabilityLabel(capabilities.demo_threat_source_enabled, "Enabled", "Disabled") : "Unknown"}
      />
    </div>
  );
}
