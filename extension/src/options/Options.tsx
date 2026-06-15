import { type FormEvent, useEffect, useState } from "react";

import { DEFAULT_SETTINGS, getExtensionSettings, saveExtensionSettings } from "../services/settings";
import type { ExtensionSettings } from "../types/analysis";
import "./options.css";

export function Options() {
  const [settings, setSettings] = useState<ExtensionSettings>(DEFAULT_SETTINGS);
  const [status, setStatus] = useState<string>("Loading settings...");

  useEffect(() => {
    void getExtensionSettings().then((storedSettings) => {
      setSettings(storedSettings);
      setStatus("Settings loaded");
    });
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const saved = await saveExtensionSettings(settings);
    setSettings(saved);
    setStatus("Settings saved");
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

      <p className="status-line" role="status">
        {status}
      </p>
    </main>
  );
}
