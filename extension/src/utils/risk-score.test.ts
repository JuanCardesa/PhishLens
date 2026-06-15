import { describe, expect, it } from "vitest";

import { analyzeLocally } from "./risk-score";

describe("analyzeLocally", () => {
  it("returns safe for a low-risk page", () => {
    const result = analyzeLocally("https://example.com", {
      has_password_field: false,
      num_forms: 0,
      external_form_action: false,
      num_iframes: 0,
      external_links_ratio: 0,
      has_hidden_inputs: false,
    });

    expect(result.label).toBe("safe");
    expect(result.risk_score).toBeLessThan(35);
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
  });
});
