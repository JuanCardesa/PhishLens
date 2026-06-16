import type { AnalysisResponse, DOMFeatures, RiskLabel } from "../types/analysis";
import { extractUrlFeatures } from "./url-features";

export function analyzeLocally(url: string, domFeatures: DOMFeatures): AnalysisResponse {
  const urlFeatures = extractUrlFeatures(url);
  const [urlScore, urlReasons] = scoreUrl(urlFeatures);
  const [domScore, domReasons] = scoreDom(domFeatures);
  const riskScore = Math.max(0, Math.min(100, Math.round(urlScore + domScore)));
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
  };
}

function labelFromScore(score: number): RiskLabel {
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

  if (features.uses_punycode) {
    score += 10;
    reasons.push("URL uses punycode");
  }

  if (features.domain_entropy > 3.8) {
    score += 5;
    reasons.push("Domain has high character entropy");
  }

  return [Math.min(score, 35), reasons];
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

  return [Math.min(score, 30), reasons];
}
