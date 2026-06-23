import type { AnalysisResponse, DOMFeatures, RiskBreakdownItem, RiskLabel } from "../types/analysis";
import { extractUrlFeatures } from "./url-features";

const URL_SCORE_CAP = 35;
const DOM_SCORE_CAP = 30;
const THREAT_INTEL_SCORE_CAP = 40;
const TLS_SCORE_CAP = 15;
const ML_MIN_ADJUSTMENT = -10;
const ML_MAX_ADJUSTMENT = 20;

// Local-only mode never has threat-intel/TLS/ML signals, so its raw max
// (URL_SCORE_CAP + DOM_SCORE_CAP = 65) is always lower than the backend's. Scaling
// the combined local score onto the same 0-100 range before applying the backend's
// thresholds (label_from_score in scoring_service.py) keeps "dangerous" reachable
// locally and makes the label mean the same thing in both modes: how much of the
// signals that ARE available fired, not an absolute score on different scales.
const LOCAL_MAX_SCORE = URL_SCORE_CAP + DOM_SCORE_CAP;

function stripFragment(url: string): string {
  try {
    const parsed = new URL(url);
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return url.split("#")[0];
  }
}

export function analyzeLocally(url: string, domFeatures: DOMFeatures): AnalysisResponse {
  const urlFeatures = extractUrlFeatures(stripFragment(url));
  const [urlScore, urlReasons] = scoreUrl(urlFeatures);
  const [domScore, domReasons] = scoreDom(domFeatures);
  const scaledScore = Math.round(((urlScore + domScore) / LOCAL_MAX_SCORE) * 100);
  const riskScore = Math.max(0, Math.min(100, scaledScore));
  const reasons = [...urlReasons, ...domReasons];

  return {
    risk_score: riskScore,
    label: labelFromScore(riskScore),
    confidence: Math.min(0.9, Number((0.55 + Math.abs(riskScore - 50) / 100).toFixed(2))),
    reasons: reasons.length > 0 ? reasons : ["No high-risk signals were detected"],
    sources: {
      heuristics: true,
      ml: false,
      phishtank: false,
      tls: false,
      demo: false,
    },
    risk_breakdown: buildLocalRiskBreakdown(urlScore, urlReasons, domScore, domReasons),
  };
}

function labelFromScore(score: number): RiskLabel {
  // Same thresholds as label_from_score in backend/app/services/scoring_service.py.
  // The score passed in is already scaled to the 0-100 range (see LOCAL_MAX_SCORE),
  // so the same absolute thresholds apply in both local-only and backend-enriched mode.
  if (score >= 70) {
    return "dangerous";
  }
  if (score >= 35) {
    return "suspicious";
  }
  return "safe";
}

function scoreUrl(features: ReturnType<typeof extractUrlFeatures>): [number, string[]] {
  let score = 0;
  const reasons: string[] = [];

  if (features.url_length > 120) {
    score += 12;
    reasons.push("URL is unusually long");
  } else if (features.url_length > 75) {
    score += 7;
    reasons.push("URL is longer than typical");
  }

  if (features.num_dots > 4) {
    score += 6;
    reasons.push("URL contains many dots");
  }

  if (features.num_hyphens > 2) {
    score += 4;
    reasons.push("URL contains multiple hyphens");
  }

  if (features.uses_ip_domain) {
    score += 9;
    reasons.push("URL uses an IP address as the domain");
  }

  if (features.has_at_symbol) {
    score += 8;
    reasons.push("URL contains an @ symbol");
  }

  if (!features.uses_https) {
    score += 5;
    reasons.push("URL does not use HTTPS");
  }

  if (features.num_subdomains > 2) {
    score += 4;
    reasons.push("URL contains many subdomains");
  }

  if (features.suspicious_keywords.length > 0) {
    score += Math.min(8, 4 * features.suspicious_keywords.length);
    reasons.push("Domain or path contains suspicious keywords");
  }

  if (features.typosquat_target) {
    const [typosquatPoints, typosquatReason] = scoreTyposquat(features.typosquat_target, features.typosquat_is_homograph);
    score += typosquatPoints;
    reasons.push(typosquatReason);
  }

  if (features.mixed_script_label) {
    score += 8;
    reasons.push("Domain label mixes multiple writing scripts (possible homograph attack)");
  }

  if (features.domain_entropy > 3.8) {
    score += 5;
    reasons.push("Domain has high character entropy");
  }

  return [Math.min(score, URL_SCORE_CAP), reasons];
}

function scoreTyposquat(target: string, isHomograph: boolean): [number, string] {
  if (isHomograph) {
    return [16, `Domain uses look-alike Unicode characters resembling ${target} (homograph attack)`];
  }
  return [14, `Domain closely resembles ${target} (possible typosquatting)`];
}

function scoreDom(features: DOMFeatures): [number, string[]] {
  let score = 0;
  const reasons: string[] = [];

  if (features.num_forms > 0) {
    score += 4;
    reasons.push("Page contains forms");
  }

  if (features.has_password_field) {
    score += 8;
    reasons.push("Page contains a password field");
  }

  if (features.external_form_action) {
    score += 10;
    reasons.push("Form submits data to an external domain");
  }

  if (features.num_iframes > 2) {
    score += 6;
    reasons.push("Page contains multiple iframes");
  } else if (features.num_iframes > 0) {
    score += 3;
    reasons.push("Page contains iframes");
  }

  if (features.external_links_ratio > 0.5) {
    score += 5;
    reasons.push("Page has a high ratio of external links");
  }

  if (features.has_hidden_inputs) {
    score += 4;
    reasons.push("Page contains hidden form inputs");
  }

  return [Math.min(score, DOM_SCORE_CAP), reasons];
}

function buildLocalRiskBreakdown(
  urlScore: number,
  urlReasons: string[],
  domScore: number,
  domReasons: string[],
): RiskBreakdownItem[] {
  return [
    {
      category: "url",
      score: urlScore,
      min_score: 0,
      max_score: URL_SCORE_CAP,
      reasons: urlReasons,
      source: "heuristics",
    },
    {
      category: "dom",
      score: domScore,
      min_score: 0,
      max_score: DOM_SCORE_CAP,
      reasons: domReasons,
      source: "dom",
    },
    {
      category: "threat_intel",
      score: 0,
      min_score: 0,
      max_score: THREAT_INTEL_SCORE_CAP,
      reasons: [],
      source: "fallback",
    },
    {
      category: "tls",
      score: 0,
      min_score: 0,
      max_score: TLS_SCORE_CAP,
      reasons: [],
      source: "fallback",
    },
    {
      category: "ml",
      score: 0,
      min_score: ML_MIN_ADJUSTMENT,
      max_score: ML_MAX_ADJUSTMENT,
      reasons: [],
      source: "fallback",
    },
  ];
}
