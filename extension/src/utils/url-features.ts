import type { URLFeatures } from "../types/analysis";

const SUSPICIOUS_KEYWORDS = ["login", "verify", "account", "secure", "update", "password", "bank", "wallet"];
const IPV4_PATTERN = /^(?:\d{1,3}\.){3}\d{1,3}$/;
const IPV6_HINT_PATTERN = /:/;

export function extractUrlFeatures(rawUrl: string): URLFeatures {
  const parsed = new URL(rawUrl);
  const hostname = parsed.hostname.toLowerCase().replace(/\.$/, "");
  const labels = hostname.split(".").filter(Boolean);
  const usesIpDomain = IPV4_PATTERN.test(hostname) || IPV6_HINT_PATTERN.test(hostname);
  const registeredDomain = labels.length >= 2 ? labels.slice(-2).join(".") : hostname;
  // Limit keyword scan to hostname + path only; query strings like
  // ?q=bank+verify are common on legitimate search engines and cause
  // false positives when the full URL is checked.
  const hostnameAndPath = (hostname + parsed.pathname).toLowerCase();

  return {
    url_length: rawUrl.length,
    num_dots: count(hostnameAndPath, "."),  // query string excluded to avoid false positives
    num_hyphens: count(rawUrl, "-"),
    uses_ip_domain: usesIpDomain,
    has_at_symbol: rawUrl.includes("@"),
    uses_https: parsed.protocol === "https:",
    num_subdomains: usesIpDomain ? 0 : Math.max(0, labels.length - 2),
    suspicious_keywords: SUSPICIOUS_KEYWORDS.filter((keyword) => hostnameAndPath.includes(keyword)),
    uses_punycode: hostname.includes("xn--"),
    domain_entropy: Number(shannonEntropy(registeredDomain.replaceAll(".", "")).toFixed(3)),
    domain: hostname,
  };
}

function count(value: string, needle: string): number {
  return value.split(needle).length - 1;
}

function shannonEntropy(value: string): number {
  if (!value) {
    return 0;
  }

  const counts = new Map<string, number>();
  for (const character of value) {
    counts.set(character, (counts.get(character) ?? 0) + 1);
  }

  let entropy = 0;
  for (const itemCount of counts.values()) {
    const probability = itemCount / value.length;
    entropy -= probability * Math.log2(probability);
  }

  return entropy;
}
