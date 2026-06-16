import type { PopupAnalysis } from "../types/analysis";

export function buildReportSummary(analysis: PopupAnalysis): string {
  const host = hostFromUrl(analysis.url);
  const reasons = analysis.reasons.slice(0, 4).map((reason) => `- ${reason}`);
  return [
    "PhishLens report",
    `Host: ${host}`,
    `Label: ${analysis.label}`,
    `Risk score: ${analysis.risk_score}/100`,
    `Confidence: ${Math.round(analysis.confidence * 100)}%`,
    `Mode: ${modeText(analysis.mode)}`,
    "Signals:",
    ...(reasons.length > 0 ? reasons : ["- No high-risk signals were detected"]),
    "",
    "Privacy: this summary excludes full URLs, form values, page text, cookies, screenshots, and HTML.",
  ].join("\n");
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
  if (mode === "checking") {
    return "checking";
  }
  return "local only";
}
