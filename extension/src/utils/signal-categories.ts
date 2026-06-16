import type { AnalysisSources, RiskBreakdownCategory, RiskBreakdownItem } from "../types/analysis";

export type SignalCategoryId = "url" | "dom" | "threat-intel" | "tls" | "ml" | "general";

export interface SignalGroup {
  id: SignalCategoryId;
  title: string;
  score?: number;
  minScore?: number;
  maxScore?: number;
  source?: string;
  reasons: string[];
}

const CATEGORY_TITLES: Record<SignalCategoryId, string> = {
  url: "URL",
  dom: "Page structure",
  "threat-intel": "Threat intelligence",
  tls: "TLS",
  ml: "ML",
  general: "General",
};

export function groupReasonsBySignal(
  reasons: string[],
  sources: AnalysisSources,
  riskBreakdown?: RiskBreakdownItem[],
): SignalGroup[] {
  if (riskBreakdown?.length) {
    return riskBreakdown.map((item) => ({
      id: signalIdFromBreakdownCategory(item.category),
      title: CATEGORY_TITLES[signalIdFromBreakdownCategory(item.category)],
      score: item.score,
      minScore: item.min_score,
      maxScore: item.max_score,
      source: item.source,
      reasons: item.reasons.length > 0 ? item.reasons : [neutralReason(item)],
    }));
  }

  const grouped = new Map<SignalCategoryId, string[]>();

  for (const reason of reasons) {
    const category = categorizeReason(reason);
    grouped.set(category, [...(grouped.get(category) ?? []), reason]);
  }

  if (sources.phishtank && !grouped.has("threat-intel")) {
    grouped.set("threat-intel", ["Threat intelligence was checked without a positive match"]);
  }

  if (sources.tls && !grouped.has("tls")) {
    grouped.set("tls", ["TLS certificate checks did not add high-risk signals"]);
  }

  if (sources.ml && !grouped.has("ml")) {
    grouped.set("ml", ["Machine learning model was available without changing the score"]);
  }

  return (["url", "dom", "threat-intel", "tls", "ml", "general"] as SignalCategoryId[])
    .filter((id) => grouped.has(id))
    .map((id) => ({
      id,
      title: CATEGORY_TITLES[id],
      reasons: grouped.get(id) ?? [],
    }));
}

export function primarySignalReason(groups: SignalGroup[]): string {
  for (const group of groups) {
    const reason = group.reasons[0];
    if (reason && reason !== "No high-risk signals were detected" && (group.score ?? 1) !== 0) {
      return `${group.title}: ${reason}`;
    }
  }

  return "No high-risk signals were detected";
}

export function formatSignalScore(group: SignalGroup): string {
  if (group.score === undefined || group.maxScore === undefined) {
    return "";
  }

  if (group.minScore !== undefined && group.minScore < 0) {
    return `${group.score} (${group.minScore} to +${group.maxScore})`;
  }

  return `${group.score}/${group.maxScore}`;
}

function signalIdFromBreakdownCategory(category: RiskBreakdownCategory): SignalCategoryId {
  if (category === "threat_intel") {
    return "threat-intel";
  }
  return category;
}

function neutralReason(item: RiskBreakdownItem): string {
  if (item.category === "threat_intel") {
    return item.source === "fallback"
      ? "Threat intelligence was not available for this result"
      : "Threat intelligence did not add high-risk signals";
  }

  if (item.category === "tls") {
    return item.source === "fallback" ? "TLS analysis was not available for this result" : "TLS did not add high-risk signals";
  }

  if (item.category === "ml") {
    return item.source === "fallback" ? "ML model was not available; heuristic scoring was used" : "ML did not change the score";
  }

  return "No high-risk signals were detected";
}

function categorizeReason(reason: string): SignalCategoryId {
  const normalized = reason.toLowerCase();

  if (
    normalized.includes("page") ||
    normalized.includes("form") ||
    normalized.includes("password") ||
    normalized.includes("iframe") ||
    normalized.includes("hidden")
  ) {
    return "dom";
  }

  if (normalized.includes("url") || normalized.includes("domain") || normalized.includes("https")) {
    return "url";
  }

  if (normalized.includes("phishing intelligence") || normalized.includes("threat source")) {
    return "threat-intel";
  }

  if (normalized.includes("tls") || normalized.includes("certificate")) {
    return "tls";
  }

  if (normalized.includes("machine learning") || normalized.includes("model")) {
    return "ml";
  }

  return "general";
}
