import { describe, expect, it } from "vitest";

import type { AnalysisMode, PopupAnalysis } from "../types/analysis";
import { cacheKey, labelSymbol, labelText, modeBannerText, modeLabel, sourceList } from "./Popup";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeAnalysis(overrides: Partial<PopupAnalysis> = {}): PopupAnalysis {
  return {
    url: "https://example.test/",
    risk_score: 10,
    label: "safe",
    confidence: 0.9,
    reasons: [],
    sources: { heuristics: true, ml: false, phishtank: false, tls: false, demo: false },
    risk_breakdown: [],
    backendAvailable: true,
    mode: "backend-enriched",
    analyzedAt: new Date().toISOString(),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// labelText
// ---------------------------------------------------------------------------

describe("labelText", () => {
  it("maps safe → Safe", () => {
    expect(labelText("safe")).toBe("Safe");
  });

  it("maps suspicious → Suspicious", () => {
    expect(labelText("suspicious")).toBe("Suspicious");
  });

  it("maps dangerous → Dangerous", () => {
    expect(labelText("dangerous")).toBe("Dangerous");
  });
});

// ---------------------------------------------------------------------------
// labelSymbol
// ---------------------------------------------------------------------------

describe("labelSymbol", () => {
  it("returns checkmark for safe", () => {
    expect(labelSymbol("safe")).toBe("✓");
  });

  it("returns exclamation for suspicious", () => {
    expect(labelSymbol("suspicious")).toBe("!");
  });

  it("returns cross for dangerous", () => {
    expect(labelSymbol("dangerous")).toBe("✕");
  });
});

// ---------------------------------------------------------------------------
// modeLabel
// ---------------------------------------------------------------------------

describe("modeLabel", () => {
  it.each<[AnalysisMode, string]>([
    ["backend-enriched", "Backend enriched"],
    ["backend-unavailable", "Backend unavailable"],
    ["cached", "Cached"],
    ["checking", "Checking"],
    ["local-only", "Local only"],
  ])("maps %s → %s", (mode, expected) => {
    expect(modeLabel(mode)).toBe(expected);
  });
});

// ---------------------------------------------------------------------------
// modeBannerText
// ---------------------------------------------------------------------------

describe("modeBannerText", () => {
  it("returns enriched message when backend is active", () => {
    expect(modeBannerText(makeAnalysis({ mode: "backend-enriched" }))).toBe(
      "Backend enrichment is active for this result.",
    );
  });

  it("returns cached message for cached mode", () => {
    expect(modeBannerText(makeAnalysis({ mode: "cached" }))).toBe(
      "Showing a recent cached result while refreshing.",
    );
  });

  it("returns local-only fallback for local-only mode", () => {
    expect(modeBannerText(makeAnalysis({ mode: "local-only" }))).toBe(
      "Local-only analysis. Backend enrichment is not active.",
    );
  });

  it("lists all skipped services when all three are unavailable", () => {
    const text = modeBannerText(
      makeAnalysis({
        mode: "backend-unavailable",
        sources: { heuristics: true, ml: false, phishtank: false, tls: false },
      }),
    );
    expect(text).toContain("Backend unavailable");
    expect(text).toContain("TLS");
    expect(text).toContain("threat intelligence");
    expect(text).toContain("ML");
    expect(text).toContain("were not checked");
  });

  it("uses singular 'was' when only one service is skipped", () => {
    const text = modeBannerText(
      makeAnalysis({
        mode: "backend-unavailable",
        sources: { heuristics: true, ml: false, phishtank: true, tls: true },
      }),
    );
    expect(text).toContain("ML was not checked");
  });

  it("omits skipped list when all services ran", () => {
    const text = modeBannerText(
      makeAnalysis({
        mode: "backend-unavailable",
        sources: { heuristics: true, ml: true, phishtank: true, tls: true },
      }),
    );
    expect(text).toContain("Backend unavailable");
    expect(text).not.toContain("was not checked");
    expect(text).not.toContain("were not checked");
  });
});

// ---------------------------------------------------------------------------
// sourceList
// ---------------------------------------------------------------------------

describe("sourceList", () => {
  it("always includes heuristics", () => {
    expect(sourceList(makeAnalysis())).toContain("heuristics");
  });

  it("includes optional sources when enabled", () => {
    const sources = sourceList(
      makeAnalysis({
        sources: { heuristics: true, ml: true, phishtank: true, tls: true, demo: true },
      }),
    );
    expect(sources).toEqual(["heuristics", "tls", "phishtank", "ml", "demo"]);
  });

  it("excludes disabled sources", () => {
    const sources = sourceList(
      makeAnalysis({
        sources: { heuristics: true, ml: false, phishtank: false, tls: false },
      }),
    );
    expect(sources).toEqual(["heuristics"]);
  });

  it("preserves ordering: tls before phishtank before ml before demo", () => {
    const sources = sourceList(
      makeAnalysis({
        sources: { heuristics: true, ml: true, phishtank: true, tls: true, demo: true },
      }),
    );
    expect(sources.indexOf("tls")).toBeLessThan(sources.indexOf("phishtank"));
    expect(sources.indexOf("phishtank")).toBeLessThan(sources.indexOf("ml"));
    expect(sources.indexOf("ml")).toBeLessThan(sources.indexOf("demo"));
  });
});

// ---------------------------------------------------------------------------
// cacheKey
// ---------------------------------------------------------------------------

describe("cacheKey", () => {
  it("returns an analysis:-prefixed 16-char hex string", async () => {
    const key = await cacheKey("https://example.com");
    expect(key).toMatch(/^analysis:[0-9a-f]{16}$/);
  });

  it("returns the same key for the same URL", async () => {
    const key1 = await cacheKey("https://example.com");
    const key2 = await cacheKey("https://example.com");
    expect(key1).toBe(key2);
  });

  it("returns different keys for different URLs", async () => {
    const key1 = await cacheKey("https://example.com");
    const key2 = await cacheKey("https://other.com");
    expect(key1).not.toBe(key2);
  });

  it("distinguishes URLs that share a common prefix", async () => {
    const key1 = await cacheKey("https://bank.example.com/login");
    const key2 = await cacheKey("https://bank.example.com/logout");
    expect(key1).not.toBe(key2);
  });
});
