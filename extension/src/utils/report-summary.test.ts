import { describe, expect, it } from "vitest";

import type { PopupAnalysis } from "../types/analysis";
import { buildReportSummary } from "./report-summary";

describe("buildReportSummary", () => {
  it("uses host-level context instead of the full URL", () => {
    const analysis: PopupAnalysis = {
      url: "https://login.example.test/private/path?token=secret",
      risk_score: 72,
      label: "dangerous",
      confidence: 0.82,
      reasons: ["Page contains a password field", "URL is longer than typical"],
      sources: {
        heuristics: true,
        ml: false,
        phishtank: false,
        tls: true,
        demo: false,
      },
      backendAvailable: true,
      mode: "backend-enriched",
      analyzedAt: "2026-06-16T00:00:00.000Z",
    };

    const summary = buildReportSummary(analysis);

    expect(summary).toContain("Host: login.example.test");
    expect(summary).toContain("Risk score: 72/100");
    expect(summary).not.toContain("/private/path");
    expect(summary).not.toContain("secret");
    expect(summary).not.toContain(analysis.url);
  });

  it("qualifies heuristic-only confidence instead of stating a bare percentage", () => {
    const base: PopupAnalysis = {
      url: "https://example.com",
      risk_score: 20,
      label: "safe",
      confidence: 0.82,
      reasons: [],
      sources: { heuristics: true, ml: false, phishtank: false, tls: false, demo: false },
      backendAvailable: false,
      mode: "backend-unavailable",
      analyzedAt: "2026-06-16T00:00:00.000Z",
    };

    expect(buildReportSummary(base)).toContain("Confidence: heuristic (not a calibrated probability)");
    expect(buildReportSummary(base)).not.toContain("Confidence: 82%");

    const withMl: PopupAnalysis = { ...base, sources: { ...base.sources, ml: true } };
    expect(buildReportSummary(withMl)).toContain("Confidence: 82%");
  });
});
