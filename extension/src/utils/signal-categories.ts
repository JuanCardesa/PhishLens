import type { AnalysisSources } from "../types/analysis";

export type SignalCategoryId = "url" | "dom" | "threat-intel" | "tls" | "ml" | "general";

export interface SignalGroup {
  id: SignalCategoryId;
  title: string;
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

export function groupReasonsBySignal(reasons: string[], sources: AnalysisSources): SignalGroup[] {
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
    if (reason && reason !== "No high-risk signals were detected") {
      return `${group.title}: ${reason}`;
    }
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
