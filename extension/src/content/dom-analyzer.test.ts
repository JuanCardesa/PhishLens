// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from "vitest";

import { collectDomFeatures, hasExternalAction } from "./dom-analyzer";

afterEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  document.title = "";
  vi.unstubAllGlobals();
});

function stubLocation(hostname: string): void {
  vi.stubGlobal("location", { hostname, href: `https://${hostname}/`, origin: `https://${hostname}` });
}

function makeForm(action: string | null): HTMLFormElement {
  const form = document.createElement("form");
  if (action !== null) {
    form.setAttribute("action", action);
  }
  return form;
}

// ---------------------------------------------------------------------------
// collectDomFeatures — integration over real happy-dom globals
// ---------------------------------------------------------------------------

describe("collectDomFeatures", () => {
  it("returns all-false defaults on an empty page", () => {
    const result = collectDomFeatures();
    expect(result).toEqual({
      has_password_field: false,
      num_forms: 0,
      external_form_action: false,
      num_iframes: 0,
      external_links_ratio: 0,
      has_hidden_inputs: false,
      brand_text_mismatch: false,
      favicon_hotlinked_brand: false,
    });
  });

  it("detects a password field", () => {
    document.body.innerHTML = '<input type="password" />';
    expect(collectDomFeatures().has_password_field).toBe(true);
  });

  it("counts forms correctly", () => {
    document.body.innerHTML = "<form></form><form></form>";
    expect(collectDomFeatures().num_forms).toBe(2);
  });

  it("counts iframes", () => {
    document.body.innerHTML = "<iframe></iframe><iframe></iframe><iframe></iframe>";
    expect(collectDomFeatures().num_iframes).toBe(3);
  });

  it("detects hidden inputs", () => {
    document.body.innerHTML = '<input type="hidden" name="csrf" value="token" />';
    expect(collectDomFeatures().has_hidden_inputs).toBe(true);
  });

  it("returns external_links_ratio of 0 when there are no links", () => {
    document.body.innerHTML = "<p>No links here</p>";
    expect(collectDomFeatures().external_links_ratio).toBe(0);
  });

  it("computes external_links_ratio correctly", () => {
    // 2 internal, 2 external → ratio = 0.5
    document.body.innerHTML = `
      <a href="/page">internal 1</a>
      <a href="/other">internal 2</a>
      <a href="https://external.example.com/">external 1</a>
      <a href="https://another.example.net/">external 2</a>
    `;
    const result = collectDomFeatures();
    expect(result.external_links_ratio).toBeCloseTo(0.5, 2);
  });

  it("excludes a link with an unparseable href without throwing", () => {
    const anchor = document.createElement("a");
    anchor.setAttribute("href", "https://example.com/");
    Object.defineProperty(anchor, "href", { value: "http://[invalid", configurable: true });
    document.body.appendChild(anchor);

    expect(() => collectDomFeatures()).not.toThrow();
    expect(collectDomFeatures().external_links_ratio).toBe(0);
  });

  it("detects external form action", () => {
    document.body.innerHTML = '<form action="https://evil.example.com/steal"></form>';
    expect(collectDomFeatures().external_form_action).toBe(true);
  });

  it("does not flag internal form action as external", () => {
    document.body.innerHTML = '<form action="/submit"></form>';
    expect(collectDomFeatures().external_form_action).toBe(false);
  });

  it("flags brand text mismatch when title names a brand on an unrelated domain", () => {
    stubLocation("totally-unrelated-login-portal.tk");
    document.title = "PayPal - Log In to Your Account";
    expect(collectDomFeatures().brand_text_mismatch).toBe(true);
  });

  it("does not flag brand text mismatch on the brand's own domain", () => {
    stubLocation("paypal.com");
    document.title = "PayPal - Log In to Your Account";
    expect(collectDomFeatures().brand_text_mismatch).toBe(false);
  });

  it("flags brand text mismatch via og:site_name even without a matching title", () => {
    stubLocation("free-hosting-site.example");
    document.title = "Welcome";
    document.head.innerHTML = '<meta property="og:site_name" content="Microsoft" />';
    expect(collectDomFeatures().brand_text_mismatch).toBe(true);
  });

  it("flags brand text mismatch via h1 heading text", () => {
    stubLocation("free-hosting-site.example");
    document.body.innerHTML = "<h1>Netflix Account Verification</h1>";
    expect(collectDomFeatures().brand_text_mismatch).toBe(true);
  });

  it("does not flag unrelated short text as a brand match", () => {
    stubLocation("example.com");
    document.title = "My Personal Blog";
    expect(collectDomFeatures().brand_text_mismatch).toBe(false);
  });

  it("flags a favicon hotlinked from a known brand's domain", () => {
    stubLocation("totally-unrelated-login-portal.tk");
    document.head.innerHTML = '<link rel="icon" href="https://www.paypal.com/favicon.ico" />';
    expect(collectDomFeatures().favicon_hotlinked_brand).toBe(true);
  });

  it("does not flag a same-domain favicon", () => {
    stubLocation("example.com");
    document.head.innerHTML = '<link rel="icon" href="/favicon.ico" />';
    expect(collectDomFeatures().favicon_hotlinked_brand).toBe(false);
  });

  it("does not flag a favicon hotlinked from a non-brand external domain", () => {
    stubLocation("example.com");
    document.head.innerHTML = '<link rel="icon" href="https://cdn.unrelated-host.example/icon.ico" />';
    expect(collectDomFeatures().favicon_hotlinked_brand).toBe(false);
  });

  it("does not throw on a malformed favicon href", () => {
    stubLocation("example.com");
    document.head.innerHTML = '<link rel="icon" href="not a valid url" />';
    expect(() => collectDomFeatures()).not.toThrow();
    expect(collectDomFeatures().favicon_hotlinked_brand).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// hasExternalAction — unit tests with controlled inputs
// ---------------------------------------------------------------------------

describe("hasExternalAction", () => {
  it("returns false when form has no action attribute", () => {
    expect(hasExternalAction(makeForm(null), "https://example.com")).toBe(false);
  });

  it("returns false for a same-origin absolute action URL", () => {
    const origin = globalThis.location.origin;
    expect(hasExternalAction(makeForm(`${origin}/submit`), origin)).toBe(false);
  });

  it("returns false for a relative path action", () => {
    // Relative URLs resolve against window.location and share the same origin.
    const origin = globalThis.location.origin;
    expect(hasExternalAction(makeForm("/submit"), origin)).toBe(false);
  });

  it("returns true for a cross-origin absolute action URL", () => {
    const origin = globalThis.location.origin;
    expect(hasExternalAction(makeForm("https://attacker.example.net/steal"), origin)).toBe(true);
  });

  it("returns true for a same-host action on a different port (distinct origin)", () => {
    // Different port → different origin, even if hostname matches.
    expect(hasExternalAction(makeForm("http://localhost:9999/steal"), "http://localhost:8080")).toBe(true);
  });

  it("returns false for a non-http action scheme", () => {
    const origin = globalThis.location.origin;
    expect(hasExternalAction(makeForm("mailto:someone@example.com"), origin)).toBe(false);
  });

  it("returns false for an action that resolves to a relative path", () => {
    const origin = globalThis.location.origin;
    expect(hasExternalAction(makeForm(":::bad:::"), origin)).toBe(false);
  });

  it("returns false when the action URL cannot be parsed at all", () => {
    const origin = globalThis.location.origin;
    expect(hasExternalAction(makeForm("http://[invalid"), origin)).toBe(false);
  });
});
