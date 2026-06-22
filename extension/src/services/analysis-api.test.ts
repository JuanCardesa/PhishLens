import { afterEach, describe, expect, it, vi } from "vitest";

import { requestBackendAnalysis, submitFeedbackReport } from "./analysis-api";
import { DEFAULT_SETTINGS } from "./settings";

const EMPTY_DOM = {
  has_password_field: false,
  num_forms: 0,
  external_form_action: false,
  num_iframes: 0,
  external_links_ratio: 0,
  has_hidden_inputs: false,
};

describe("analysis-api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts analysis requests to the configured backend", async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          risk_score: 72,
          label: "dangerous",
          confidence: 0.8,
          reasons: ["URL appears risky"],
          sources: { heuristics: true, ml: false, phishtank: false, tls: false },
        }),
        { status: 200 },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await requestBackendAnalysis(
      "https://example.test/login",
      {
        has_password_field: true,
        num_forms: 1,
        external_form_action: false,
        num_iframes: 0,
        external_links_ratio: 0.1,
        has_hidden_inputs: false,
      },
      DEFAULT_SETTINGS,
    );

    expect(result?.label).toBe("dangerous");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/analyze",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("returns false when feedback cannot be sent", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 503 })),
    );

    const ok = await submitFeedbackReport(
      {
        url: "https://example.test/login",
        observed_label: "dangerous",
        expected_label: "safe",
      },
      DEFAULT_SETTINGS,
    );

    expect(ok).toBe(false);
  });

  it("retries once on a network error before returning null", async () => {
    let callCount = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        callCount += 1;
        throw new TypeError("Failed to fetch");
      }),
    );

    const result = await requestBackendAnalysis("https://example.test/login", EMPTY_DOM, DEFAULT_SETTINGS);

    expect(result).toBeNull();
    expect(callCount).toBe(2);
  });

  it("does not retry on timeout (AbortError)", async () => {
    let callCount = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        callCount += 1;
        throw new DOMException("The operation was aborted.", "AbortError");
      }),
    );

    const result = await requestBackendAnalysis("https://example.test/login", EMPTY_DOM, DEFAULT_SETTINGS);

    expect(result).toBeNull();
    expect(callCount).toBe(1);
  });

  it("does not retry on a non-ok HTTP response (e.g. 429)", async () => {
    let callCount = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        callCount += 1;
        return new Response(null, { status: 429 });
      }),
    );

    const result = await requestBackendAnalysis("https://example.test/login", EMPTY_DOM, DEFAULT_SETTINGS);

    expect(result).toBeNull();
    expect(callCount).toBe(1);
  });
});
