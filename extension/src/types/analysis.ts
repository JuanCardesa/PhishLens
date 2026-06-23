export type RiskLabel = "safe" | "suspicious" | "dangerous";
export type AnalysisMode = "checking" | "local-only" | "backend-enriched" | "backend-unavailable" | "cached";

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
  typosquat_target: string | null;
  typosquat_distance: number | null;
  typosquat_is_homograph: boolean;
  mixed_script_label: boolean;
}

export interface AnalysisSources {
  heuristics: boolean;
  ml: boolean;
  phishtank: boolean;
  tls: boolean;
  demo?: boolean;
}

export type RiskBreakdownCategory = "url" | "dom" | "threat_intel" | "tls" | "ml";

export interface RiskBreakdownItem {
  category: RiskBreakdownCategory;
  score: number;
  min_score: number;
  max_score: number;
  reasons: string[];
  source: string;
}

export interface AnalysisResponse {
  risk_score: number;
  label: RiskLabel;
  confidence: number;
  reasons: string[];
  sources: AnalysisSources;
  risk_breakdown?: RiskBreakdownItem[];
}

export interface PopupAnalysis extends AnalysisResponse {
  url: string;
  backendAvailable: boolean;
  mode: AnalysisMode;
  analyzedAt: string;
}

export interface ExtensionSettings {
  backendBaseUrl: string;
  requestTimeoutMs: number;
  dangerOverlayEnabled: boolean;
}

export interface FeedbackReport {
  url: string;
  observed_label: RiskLabel;
  expected_label: RiskLabel;
  notes?: string;
}

export interface BackendHealthResponse {
  status: "ok" | string;
  service: string;
}

export interface DiagnosticsCapabilities {
  diagnostics_enabled: boolean;
  rate_limiting_enabled: boolean;
  threat_intel_enabled: boolean;
  tls_analysis_enabled: boolean;
  ml_model_available: boolean;
  demo_threat_source_enabled: boolean;
}

export interface DiagnosticsResponse {
  status: "ok" | string;
  service: string;
  privacy: string;
  capabilities: DiagnosticsCapabilities;
  counters: Record<string, number>;
  labels: Record<string, number>;
  sources: Record<string, number>;
}

export type BackendStatusState = "online" | "diagnostics-disabled" | "offline";

export interface BackendStatus {
  state: BackendStatusState;
  service: string | null;
  diagnosticsAvailable: boolean;
  diagnostics: DiagnosticsResponse | null;
  message: string;
  checkedAt: string;
}
