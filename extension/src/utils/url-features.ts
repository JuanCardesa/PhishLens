import type { URLFeatures } from "../types/analysis";

const SUSPICIOUS_KEYWORDS = ["login", "verify", "account", "secure", "update", "password", "bank", "wallet"];
const IPV4_PATTERN = /^(?:\d{1,3}\.){3}\d{1,3}$/;
const IPV6_HINT_PATTERN = /:/;

// Curated list of frequently-impersonated brand domains. Used as the
// reference set for typosquatting (Levenshtein) and combosquatting
// (brand name embedded in a longer label) detection. Keep in sync with
// backend/app/services/feature_extractor.py::KNOWN_BRAND_DOMAINS.
const KNOWN_BRAND_DOMAINS = [
  "google.com",
  "youtube.com",
  "facebook.com",
  "instagram.com",
  "whatsapp.com",
  "amazon.com",
  "apple.com",
  "icloud.com",
  "microsoft.com",
  "outlook.com",
  "office.com",
  "netflix.com",
  "paypal.com",
  "ebay.com",
  "linkedin.com",
  "twitter.com",
  "github.com",
  "dropbox.com",
  "yahoo.com",
  "bankofamerica.com",
  "chase.com",
  "wellsfargo.com",
  "americanexpress.com",
  "coinbase.com",
  "binance.com",
  "adobe.com",
];

// Brand names shorter than this produce too many coincidental matches
// (e.g. "x.com") to be a useful typosquatting signal.
const MIN_BRAND_NAME_LENGTH = 4;

// Maximum Levenshtein distance still considered a plausible typosquat.
const MAX_TYPOSQUAT_DISTANCE = 2;

// Common two-label public suffixes. This is intentionally conservative rather
// than a full PSL implementation so the extension and backend can stay in sync
// without adding bundle/runtime dependencies.
const COMMON_SECOND_LEVEL_PUBLIC_SUFFIX_LABELS = new Set(["ac", "co", "com", "edu", "gov", "net", "org"]);

export function extractUrlFeatures(rawUrl: string): URLFeatures {
  const parsed = new URL(rawUrl);
  const hostname = parsed.hostname.toLowerCase().replace(/\.$/, "");
  const labels = hostname.split(".").filter(Boolean);
  const usesIpDomain = IPV4_PATTERN.test(hostname) || IPV6_HINT_PATTERN.test(hostname);
  const registeredDomainParts = getRegistrableDomainParts(labels);
  const registeredDomain = registeredDomainParts.join(".");
  const registeredDomainLabel = registeredDomainParts[0] ?? "";
  // Limit keyword scan to hostname + path only; query strings like
  // ?q=bank+verify are common on legitimate search engines and cause
  // false positives when the full URL is checked.
  const hostnameAndPath = (hostname + parsed.pathname).toLowerCase();
  const [typosquatTarget, typosquatDistance] = usesIpDomain
    ? [null, null]
    : detectTyposquatting(registeredDomain, registeredDomainLabel);

  return {
    url_length: rawUrl.length,
    num_dots: count(hostnameAndPath, "."), // query string excluded to avoid false positives
    num_hyphens: count(rawUrl, "-"),
    uses_ip_domain: usesIpDomain,
    has_at_symbol: rawUrl.includes("@"),
    uses_https: parsed.protocol === "https:",
    num_subdomains: usesIpDomain ? 0 : Math.max(0, labels.length - registeredDomainParts.length),
    suspicious_keywords: SUSPICIOUS_KEYWORDS.filter((keyword) => hostnameAndPath.includes(keyword)),
    uses_punycode: hostname.includes("xn--"),
    domain_entropy: Number(shannonEntropy(registeredDomain.replaceAll(".", "")).toFixed(3)),
    domain: hostname,
    typosquat_target: typosquatTarget,
    typosquat_distance: typosquatDistance,
  };
}

/**
 * Compare the registered domain against known brand domains. Catches both
 * classic typosquatting (small Levenshtein distance between the registrable
 * label and brand label, e.g. "paypa1.net") and combosquatting (brand name as
 * a hyphen-delimited token in a longer label, e.g. "paypal-secure.com").
 * Returns [null, null] if no plausible match is found.
 */
function detectTyposquatting(registeredDomain: string, domainLabel: string): [string | null, number | null] {
  if (
    !registeredDomain ||
    KNOWN_BRAND_DOMAINS.includes(registeredDomain) ||
    !domainLabel ||
    domainLabel.length < MIN_BRAND_NAME_LENGTH
  ) {
    return [null, null];
  }

  let bestTarget: string | null = null;
  let bestDistance: number | null = null;

  for (const brandDomain of KNOWN_BRAND_DOMAINS) {
    const brandLabel = brandDomain.split(".")[0];
    if (brandLabel.length < MIN_BRAND_NAME_LENGTH) {
      continue;
    }

    let distance: number;
    if (isHyphenDelimitedCombo(domainLabel, brandLabel)) {
      distance = 1;
    } else {
      distance = levenshteinDistance(domainLabel, brandLabel);
      if (distance === 0) {
        continue;
      }
    }

    if (distance <= MAX_TYPOSQUAT_DISTANCE && (bestDistance === null || distance < bestDistance)) {
      bestDistance = distance;
      bestTarget = brandDomain;
    }
  }

  return [bestTarget, bestDistance];
}

function getRegistrableDomainParts(labels: string[]): string[] {
  if (labels.length < 2) {
    return labels;
  }

  if (
    labels.length >= 3 &&
    (labels.at(-1)?.length ?? 0) === 2 &&
    COMMON_SECOND_LEVEL_PUBLIC_SUFFIX_LABELS.has(labels.at(-2) ?? "")
  ) {
    return labels.slice(-3);
  }

  return labels.slice(-2);
}

function isHyphenDelimitedCombo(domainLabel: string, brandLabel: string): boolean {
  if (domainLabel === brandLabel || !domainLabel.includes("-")) {
    return false;
  }

  return domainLabel.split("-").filter(Boolean).includes(brandLabel);
}

function levenshteinDistance(a: string, b: string): number {
  if (a === b) {
    return 0;
  }
  if (!a) {
    return b.length;
  }
  if (!b) {
    return a.length;
  }

  let previousRow = Array.from({ length: b.length + 1 }, (_, index) => index);

  for (let i = 1; i <= a.length; i++) {
    const currentRow = [i, ...new Array<number>(b.length).fill(0)];
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      currentRow[j] = Math.min(
        previousRow[j] + 1, // deletion
        currentRow[j - 1] + 1, // insertion
        previousRow[j - 1] + cost, // substitution
      );
    }
    previousRow = currentRow;
  }

  return previousRow.at(-1) as number;
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
