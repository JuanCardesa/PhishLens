import type { PopupAnalysis } from "../types/analysis";

export function buildReportSummary(analysis: PopupAnalysis): string {
  const host = hostFromUrl(analysis.url);
  const reasons = analysis.reasons.slice(0, 4).map((reason) => `- ${reason}`);
  return [
    "PhishLens report",
    `Host: ${host}`,
    `Label: ${analysis.label}`,
    `Risk score: ${analysis.risk_score}/100`,
    `Confidence: ${confidenceText(analysis)}`,
    `Mode: ${modeText(analysis.mode)}`,
    "Signals:",
    ...(reasons.length > 0 ? reasons : ["- No high-risk signals were detected"]),
    "",
    "Privacy: this summary excludes full URLs, form values, page text, cookies, screenshots, and HTML.",
  ].join("\n");
}

function confidenceText(analysis: PopupAnalysis): string {
  // The heuristic-only confidence is uncalibrated (see docs/ml-methodology.md),
  // so a copied report qualifies it rather than stating a bare percentage.
  if (!analysis.sources.ml) {
    return "heuristic (not a calibrated probability)";
  }
  return `${Math.round(analysis.confidence * 100)}%`;
}

function hostFromUrl(url: string): string {
  try {
    return new URL(url).hostname || "unknown";
  } catch {
    return "unknown";
  }
}

function modeText(mode: PopupAnalysis["mode"]): string {
  if (mode === "backend-enriched") {
    return "backend enriched";
  }
  if (mode === "backend-unavailable") {
    return "backend unavailable";
  }
  if (mode === "cached") {
    return "cached";
  }
  return "checking";
}
