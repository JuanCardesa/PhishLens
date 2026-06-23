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

  it("detects typosquatting across TLDs", () => {
    const features = extractUrlFeatures("https://paypa1.net/login");

    expect(features.typosquat_target).toBe("paypal.com");
    expect(features.typosquat_distance).toBe(1);
  });

  it("detects combosquatting", () => {
    const features = extractUrlFeatures("https://paypal-secure-login.com/account");

    expect(features.typosquat_target).toBe("paypal.com");
    expect(features.typosquat_distance).toBe(1);
  });

  it("detects combosquatting on two-label public suffixes", () => {
    const features = extractUrlFeatures("https://paypal-secure.co.uk/account");

    expect(features.typosquat_target).toBe("paypal.com");
    expect(features.typosquat_distance).toBe(1);
    expect(features.num_subdomains).toBe(0);
  });

  it("does not flag the real brand domain", () => {
    const features = extractUrlFeatures("https://paypal.com/login");

    expect(features.typosquat_target).toBeNull();
    expect(features.typosquat_distance).toBeNull();
  });

  it("does not flag an exact brand label on an alternate suffix", () => {
    const features = extractUrlFeatures("https://accounts.google.co.uk/login");

    expect(features.typosquat_target).toBeNull();
    expect(features.typosquat_distance).toBeNull();
    expect(features.num_subdomains).toBe(1);
  });

  it.each([
    "https://raw.githubusercontent.com/JuanCardesa/PhishLens/main/README.md",
    "https://storage.googleapis.com/example-bucket/file.txt",
    "https://appleton.com/",
  ])("does not flag brand substrings without separators: %s", (url) => {
    const features = extractUrlFeatures(url);

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
    expect(features.mixed_script_label).toBe(false);
  });

  it("detects a full-script homograph", () => {
    // xn--80ak6aa92e decodes to "аррӏе" (all Cyrillic look-alikes of "apple")
    const features = extractUrlFeatures("https://xn--80ak6aa92e.com/login");

    expect(features.typosquat_target).toBe("apple.com");
    expect(features.typosquat_distance).toBe(0);
    expect(features.typosquat_is_homograph).toBe(true);
    // A single, consistently Cyrillic label is not "mixed" script.
    expect(features.mixed_script_label).toBe(false);
  });

  it("detects a mixed-script homograph", () => {
    // "gооgle.com": the two "o"s are Cyrillic look-alikes (U+043E).
    const features = extractUrlFeatures("https://gооgle.com/login");

    expect(features.typosquat_target).toBe("google.com");
    expect(features.typosquat_distance).toBe(0);
    expect(features.typosquat_is_homograph).toBe(true);
    expect(features.mixed_script_label).toBe(true);
  });

  it("flags mixed-script labels even without a brand match", () => {
    // "tеst-аbc.com": Cyrillic "е" and "а" mixed into an otherwise
    // Latin label that does not resemble any known brand.
    const features = extractUrlFeatures("https://tеst-аbc.com/");

    expect(features.mixed_script_label).toBe(true);
    expect(features.typosquat_target).toBeNull();
    expect(features.typosquat_distance).toBeNull();
    expect(features.typosquat_is_homograph).toBe(false);
  });

  it("does not flag an ASCII typosquat as a homograph", () => {
    const features = extractUrlFeatures("https://paypa1.com/login");

    expect(features.typosquat_is_homograph).toBe(false);
    expect(features.mixed_script_label).toBe(false);
  });
});
