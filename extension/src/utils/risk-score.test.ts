import { describe, expect, it } from "vitest";

import type { DOMFeatures } from "../types/analysis";
import { analyzeLocally } from "./risk-score";

const EMPTY_DOM: DOMFeatures = {
  has_password_field: false,
  num_forms: 0,
  external_form_action: false,
  num_iframes: 0,
  external_links_ratio: 0,
  has_hidden_inputs: false,
};

describe("analyzeLocally", () => {
  it("returns safe for a low-risk page", () => {
    const result = analyzeLocally("https://example.com", EMPTY_DOM);

    expect(result.label).toBe("safe");
    expect(result.risk_score).toBeLessThan(35);
    expect(result.risk_breakdown?.map((item) => item.category)).toEqual(["url", "dom", "threat_intel", "tls", "ml"]);
  });

  it("combines URL and DOM signals into suspicious risk", () => {
    const result = analyzeLocally("http://verify-account.example.test/login-update", {
      has_password_field: true,
      num_forms: 1,
      external_form_action: true,
      num_iframes: 1,
      external_links_ratio: 0.2,
      has_hidden_inputs: true,
    });

    expect(result.label).toBe("suspicious");
    expect(result.reasons).toContain("Form submits data to an external domain");
    expect(result.risk_breakdown?.find((item) => item.category === "dom")?.max_score).toBe(30);
    expect(result.risk_breakdown?.find((item) => item.category === "ml")?.min_score).toBe(-10);
  });

  it("caps url score at 35", () => {
    const result = analyzeLocally(
      "http://secure-login-verify-account-update-password-bank.attacker.phishing.scam.evil.bad.com/wallet",
      EMPTY_DOM,
    );
    const urlScore = result.risk_breakdown?.find((item) => item.category === "url")?.score ?? 999;
    expect(urlScore).toBeLessThanOrEqual(35);
  });
});

// ---------------------------------------------------------------------------
// Parity vectors - mirrors backend/tests/test_scoring_parity.py exactly.
// If a value here diverges from the Python test, the offline fallback is wrong.
// ---------------------------------------------------------------------------

describe("scoring parity (mirrors backend/tests/test_scoring_parity.py)", () => {
  it("benign https URL scores 0 URL points", () => {
    const result = analyzeLocally("https://example.com", EMPTY_DOM);
    const urlScore = result.risk_breakdown?.find((item) => item.category === "url")?.score;
    expect(urlScore).toBe(0);
  });

  it("no-HTTPS adds 5 URL points", () => {
    const result = analyzeLocally("http://example.com", EMPTY_DOM);
    const urlScore = result.risk_breakdown?.find((item) => item.category === "url")?.score;
    expect(urlScore).toBe(5);
  });

  it("two suspicious keywords + no HTTPS = 13 URL points", () => {
    // http (+5) + keywords 'secure','login' -> min(8, 4*2=8)=8 -> total 13
    const result = analyzeLocally("http://secure-login.example.com", EMPTY_DOM);
    const urlScore = result.risk_breakdown?.find((item) => item.category === "url")?.score;
    expect(urlScore).toBe(13);
  });

  it("empty DOM scores 0 DOM points", () => {
    const result = analyzeLocally("https://example.com", EMPTY_DOM);
    const domScore = result.risk_breakdown?.find((item) => item.category === "dom")?.score;
    expect(domScore).toBe(0);
  });

  it("password field + form + external action = 22 DOM points", () => {
    // forms (+4) + password (+8) + external action (+10) = 22
    const result = analyzeLocally("https://example.com", {
      ...EMPTY_DOM,
      has_password_field: true,
      num_forms: 1,
      external_form_action: true,
    });
    const domScore = result.risk_breakdown?.find((item) => item.category === "dom")?.score;
    expect(domScore).toBe(22);
  });

  it("url 13 + dom 22 = total 35 -> suspicious", () => {
    const result = analyzeLocally("http://secure-login.example.com", {
      ...EMPTY_DOM,
      has_password_field: true,
      num_forms: 1,
      external_form_action: true,
    });
    expect(result.risk_score).toBe(35);
    expect(result.label).toBe("suspicious");
  });

  it("num_dots excludes query string", () => {
    // Both URLs have the same hostname+path dots; query string should not count
    const withQs = analyzeLocally("https://maps.example.com?q=1.5,2.3&zoom=1.0", EMPTY_DOM);
    const withoutQs = analyzeLocally("https://maps.example.com", EMPTY_DOM);
    const dotsWithQs = withQs.risk_breakdown?.find((i) => i.category === "url")?.score;
    const dotsWithout = withoutQs.risk_breakdown?.find((i) => i.category === "url")?.score;
    expect(dotsWithQs).toBe(dotsWithout);
  });

  it("typosquat domain adds 14 URL points", () => {
    // https (+0) + typosquat (+14) = 14
    const result = analyzeLocally("https://paypa1.com", EMPTY_DOM);
    const urlScore = result.risk_breakdown?.find((item) => item.category === "url")?.score;
    expect(urlScore).toBe(14);
    expect(result.reasons).toContain("Domain closely resembles paypal.com (possible typosquatting)");
  });
});
