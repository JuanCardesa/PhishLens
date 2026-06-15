import { describe, expect, it } from "vitest";

import { extractUrlFeatures } from "./url-features";

describe("extractUrlFeatures", () => {
  it("detects suspicious URL features", () => {
    const features = extractUrlFeatures("http://secure-login.example.test/account-update");

    expect(features.uses_https).toBe(false);
    expect(features.suspicious_keywords).toEqual(expect.arrayContaining(["secure", "login", "account", "update"]));
    expect(features.num_hyphens).toBeGreaterThan(0);
  });

  it("detects IP domains and @ symbols", () => {
    const features = extractUrlFeatures("https://user@example.com@192.168.0.1/login");

    expect(features.uses_ip_domain).toBe(true);
    expect(features.has_at_symbol).toBe(true);
  });
});
