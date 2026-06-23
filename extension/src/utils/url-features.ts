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

// Non-exhaustive table of Cyrillic/Greek characters commonly used in
// homograph (IDN spoofing) attacks, mapped to the Latin letter they visually
// resemble. Covers the lookalikes seen in real-world phishing reports (e.g.
// the "apple.com" -> "аррӏе.com" spoof); not a full Unicode confusables
// table. Keep in sync with feature_extractor.py::CONFUSABLE_MAP.
const CONFUSABLE_MAP: Record<string, string> = {
  // Cyrillic
  а: "a",
  е: "e",
  о: "o",
  р: "p",
  с: "c",
  х: "x",
  у: "y",
  ѕ: "s",
  і: "i",
  ј: "j",
  ӏ: "l",
  // Greek
  α: "a",
  ο: "o",
  ρ: "p",
  υ: "y",
  ι: "i",
  χ: "x",
};

// Unicode scripts checked for mixed-script labels. Digits, hyphens, and
// characters outside these scripts are treated as script-neutral to avoid
// false positives.
const SCRIPT_PATTERNS: Record<string, RegExp> = {
  latin: /\p{Script=Latin}/u,
  cyrillic: /\p{Script=Cyrillic}/u,
  greek: /\p{Script=Greek}/u,
  armenian: /\p{Script=Armenian}/u,
  hebrew: /\p{Script=Hebrew}/u,
  arabic: /\p{Script=Arabic}/u,
  han: /\p{Script=Han}/u,
  hiragana: /\p{Script=Hiragana}/u,
  katakana: /\p{Script=Katakana}/u,
  hangul: /\p{Script=Hangul}/u,
};

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

  const decodedLabel = decodeIdnaLabel(registeredDomainLabel).toLowerCase();
  const isNonAsciiLabel = [...decodedLabel].some((char) => char.codePointAt(0)! > 127);
  const normalizedLabel = normalizeConfusables(decodedLabel);
  const mixedScriptLabel = usesIpDomain ? false : hasMixedScript(decodedLabel);

  const [typosquatTarget, typosquatDistance, typosquatIsHomograph] = usesIpDomain
    ? [null, null, false]
    : detectTyposquatting(registeredDomain, normalizedLabel, isNonAsciiLabel);

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
    typosquat_is_homograph: typosquatIsHomograph,
    mixed_script_label: mixedScriptLabel,
  };
}

/**
 * Decode a single punycode label (e.g. "xn--80ak6aa92e") to Unicode. Returns
 * the label unchanged if it is not punycode-encoded or fails to decode
 * (malformed punycode).
 */
function decodeIdnaLabel(label: string): string {
  if (!label.startsWith("xn--")) {
    return label;
  }

  try {
    return decodePunycode(label.slice(4));
  } catch {
    return label;
  }
}

function normalizeConfusables(text: string): string {
  return [...text].map((char) => CONFUSABLE_MAP[char] ?? char).join("");
}

function charScript(char: string): string | null {
  if (/[0-9_-]/.test(char)) {
    return null;
  }

  for (const [script, pattern] of Object.entries(SCRIPT_PATTERNS)) {
    if (pattern.test(char)) {
      return script;
    }
  }

  return null;
}

function hasMixedScript(label: string): boolean {
  const scripts = new Set<string>();
  for (const char of label) {
    const script = charScript(char);
    if (script) {
      scripts.add(script);
    }
  }

  return scripts.size > 1;
}

/**
 * Compare the registered domain against known brand domains. `domainLabel`
 * is already IDNA-decoded and confusable-normalized, so this catches three
 * patterns with a single comparison: classic typosquatting (a small
 * Levenshtein edit distance, e.g. "paypa1.net"), combosquatting (the brand
 * name as a hyphen-delimited token in a longer label, e.g.
 * "paypal-secure.com"), and homograph attacks (look-alike Unicode characters
 * that normalize to the brand name, e.g. the punycode form of "аррӏе.com").
 *
 * An exact normalized match (distance 0) is only flagged when the label is
 * non-ASCII/homograph; an ASCII label that exactly matches a brand name on a
 * different suffix (e.g. "google.co.uk") is a plausible legitimate regional
 * domain and is not flagged.
 *
 * Returns [target, distance, isHomograph], or [null, null, false] if no
 * plausible match is found.
 */
function detectTyposquatting(
  registeredDomain: string,
  domainLabel: string,
  isNonAsciiLabel: boolean,
): [string | null, number | null, boolean] {
  if (
    !registeredDomain ||
    KNOWN_BRAND_DOMAINS.includes(registeredDomain) ||
    !domainLabel ||
    domainLabel.length < MIN_BRAND_NAME_LENGTH
  ) {
    return [null, null, false];
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
      if (distance === 0 && !isNonAsciiLabel) {
        continue;
      }
    }

    if (distance <= MAX_TYPOSQUAT_DISTANCE && (bestDistance === null || distance < bestDistance)) {
      bestDistance = distance;
      bestTarget = brandDomain;
    }
  }

  if (bestTarget === null) {
    return [null, null, false];
  }

  return [bestTarget, bestDistance, isNonAsciiLabel];
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

const PUNYCODE_BASE = 36;
const PUNYCODE_T_MIN = 1;
const PUNYCODE_T_MAX = 26;
const PUNYCODE_SKEW = 38;
const PUNYCODE_DAMP = 700;
const PUNYCODE_INITIAL_BIAS = 72;
const PUNYCODE_INITIAL_N = 128;
const PUNYCODE_DELIMITER = "-";

/** Decodes the bootstring-encoded part of a punycode label per RFC 3492. */
function decodePunycode(input: string): string {
  let n = PUNYCODE_INITIAL_N;
  let i = 0;
  let bias = PUNYCODE_INITIAL_BIAS;
  const output: number[] = [];

  let basicLength = input.lastIndexOf(PUNYCODE_DELIMITER);
  if (basicLength < 0) {
    basicLength = 0;
  }

  for (let j = 0; j < basicLength; j++) {
    const code = input.charCodeAt(j);
    if (code >= 0x80) {
      throw new Error("invalid punycode: non-ASCII character in basic code point segment");
    }
    output.push(code);
  }

  let index = basicLength > 0 ? basicLength + 1 : 0;
  const inputLength = input.length;

  while (index < inputLength) {
    const oldI = i;
    let weight = 1;
    for (let k = PUNYCODE_BASE; ; k += PUNYCODE_BASE) {
      if (index >= inputLength) {
        throw new Error("invalid punycode: truncated input");
      }
      const digit = decodePunycodeDigit(input.charCodeAt(index++));
      if (digit >= PUNYCODE_BASE) {
        throw new Error("invalid punycode: digit out of range");
      }
      i += digit * weight;
      const threshold = k <= bias ? PUNYCODE_T_MIN : Math.min(k - bias, PUNYCODE_T_MAX);
      if (digit < threshold) {
        break;
      }
      weight *= PUNYCODE_BASE - threshold;
    }

    const outLength = output.length + 1;
    bias = adaptPunycodeBias(i - oldI, outLength, oldI === 0);

    n += Math.floor(i / outLength);
    i %= outLength;
    output.splice(i, 0, n);
    i++;
  }

  return output.map((codePoint) => String.fromCodePoint(codePoint)).join("");
}

function decodePunycodeDigit(code: number): number {
  if (code - 0x30 < 0x0a) {
    return code - 0x16; // '0'-'9' -> 26-35
  }
  if (code - 0x41 < 0x1a) {
    return code - 0x41; // 'A'-'Z' -> 0-25
  }
  if (code - 0x61 < 0x1a) {
    return code - 0x61; // 'a'-'z' -> 0-25
  }
  return PUNYCODE_BASE; // out of range
}

function adaptPunycodeBias(delta: number, numPoints: number, firstTime: boolean): number {
  let scaledDelta = firstTime ? Math.floor(delta / PUNYCODE_DAMP) : delta >> 1;
  scaledDelta += Math.floor(scaledDelta / numPoints);

  let k = 0;
  const threshold = ((PUNYCODE_BASE - PUNYCODE_T_MIN) * PUNYCODE_T_MAX) >> 1;
  while (scaledDelta > threshold) {
    scaledDelta = Math.floor(scaledDelta / (PUNYCODE_BASE - PUNYCODE_T_MIN));
    k += PUNYCODE_BASE;
  }

  return k + Math.floor(((PUNYCODE_BASE - PUNYCODE_T_MIN + 1) * scaledDelta) / (scaledDelta + PUNYCODE_SKEW));
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
