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

  it("detects typosquatting via Levenshtein distance", () => {
    const features = extractUrlFeatures("https://paypa1.com/login");

    expect(features.typosquat_target).toBe("paypal.com");
    expect(features.typosquat_distance).toBe(1);
  });

  it("detects combosquatting", () => {
    const features = extractUrlFeatures("https://paypal-secure-login.com/account");

    expect(features.typosquat_target).toBe("paypal.com");
    expect(features.typosquat_distance).toBe(1);
  });

  it("does not flag the real brand domain", () => {
    const features = extractUrlFeatures("https://paypal.com/login");

    expect(features.typosquat_target).toBeNull();
    expect(features.typosquat_distance).toBeNull();
  });

  it("does not flag unrelated domains", () => {
    const features = extractUrlFeatures("https://example.com");

    expect(features.typosquat_target).toBeNull();
    expect(features.typosquat_distance).toBeNull();
  });

  it("skips the typosquat check for IP domains", () => {
    const features = extractUrlFeatures("http://192.168.0.1/login");

    expect(features.typosquat_target).toBeNull();
    expect(features.typosquat_distance).toBeNull();
  });
});
