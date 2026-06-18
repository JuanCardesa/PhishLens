// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from "vitest";

import { collectDomFeatures, hasExternalAction } from "./dom-analyzer";

afterEach(() => {
  document.body.innerHTML = "";
});

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

  it("detects external form action", () => {
    document.body.innerHTML = '<form action="https://evil.example.com/steal"></form>';
    expect(collectDomFeatures().external_form_action).toBe(true);
  });

  it("does not flag internal form action as external", () => {
    document.body.innerHTML = '<form action="/submit"></form>';
    expect(collectDomFeatures().external_form_action).toBe(false);
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

  it("returns false for a malformed action URL", () => {
    const origin = globalThis.location.origin;
    expect(hasExternalAction(makeForm(":::bad:::"), origin)).toBe(false);
  });
});
