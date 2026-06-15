export type RiskLabel = "safe" | "suspicious" | "dangerous";

export interface DOMFeatures {
  has_password_field: boolean;
  num_forms: number;
  external_form_action: boolean;
  num_iframes: number;
  external_links_ratio: number;
  has_hidden_inputs: boolean;
}

export interface URLFeatures {
  url_length: number;
  num_dots: number;
  num_hyphens: number;
  uses_ip_domain: boolean;
  has_at_symbol: boolean;
  uses_https: boolean;
  num_subdomains: number;
  suspicious_keywords: string[];
  uses_punycode: boolean;
  domain_entropy: number;
  domain: string;
}

export interface AnalysisSources {
  heuristics: boolean;
  ml: boolean;
  phishtank: boolean;
  tls: boolean;
}

export interface AnalysisResponse {
  risk_score: number;
  label: RiskLabel;
  confidence: number;
  reasons: string[];
  sources: AnalysisSources;
}

export interface PopupAnalysis extends AnalysisResponse {
  url: string;
  backendAvailable: boolean;
  analyzedAt: string;
}
