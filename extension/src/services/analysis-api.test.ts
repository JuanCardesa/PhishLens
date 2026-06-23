import { afterEach, describe, expect, it, vi } from "vitest";

import type { DOMFeatures } from "../types/analysis";
import { requestBackendAnalysis, submitFeedbackReport } from "./analysis-api";
import { DEFAULT_SETTINGS } from "./settings";

const EMPTY_DOM: DOMFeatures = {
  has_password_field: false,
  num_forms: 0,
  external_form_action: false,
  num_iframes: 0,
  external_links_ratio: 0,
  has_hidden_inputs: false,
};

const DOM_FEATURES: DOMFeatures = {
  has_password_field: true,
  num_forms: 1,
  external_form_action: false,
  num_iframes: 0,
  external_links_ratio: 0.1,
  has_hidden_inputs: false,
};

const VALID_ANALYSIS_RESPONSE = {
  risk_score: 72,
  label: "dangerous",
  confidence: 0.8,
  reasons: ["URL appears risky"],
  sources: { heuristics: true, ml: false, phishtank: false, tls: false },
};

describe("requestBackendAnalysis", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts to the configured backend and returns parsed JSON", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(VALID_ANALYSIS_RESPONSE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await requestBackendAnalysis("https://example.test/login", DOM_FEATURES, DEFAULT_SETTINGS);

    expect(result?.label).toBe("dangerous");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/analyze",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("sends url and dom_features in the request body", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(JSON.stringify(VALID_ANALYSIS_RESPONSE), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await requestBackendAnalysis("https://example.test/login", DOM_FEATURES, DEFAULT_SETTINGS);

    const init = fetchMock.mock.calls[0]?.[1];
    if (!init) {
      throw new Error("Missing fetch init");
    }
    const body = JSON.parse(init.body as string) as { url: string; dom_features: DOMFeatures };
    expect(body.url).toBe("https://example.test/login");
    expect(body.dom_features).toEqual(DOM_FEATURES);
  });

  it("uses a custom backendBaseUrl from settings", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(VALID_ANALYSIS_RESPONSE), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await requestBackendAnalysis("https://example.test/login", DOM_FEATURES, {
      ...DEFAULT_SETTINGS,
      backendBaseUrl: "https://api.example.com",
    });

    expect(fetchMock).toHaveBeenCalledWith("https://api.example.com/analyze", expect.anything());
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

describe("submitFeedbackReport", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns true on successful submission", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 200 })));

    const ok = await submitFeedbackReport(
      { url: "https://example.test/login", observed_label: "safe", expected_label: "dangerous" },
      DEFAULT_SETTINGS,
    );
    expect(ok).toBe(true);
  });

  it("returns false when feedback cannot be sent (non-OK status)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 503 })));

    const ok = await submitFeedbackReport(
      { url: "https://example.test/login", observed_label: "dangerous", expected_label: "safe" },
      DEFAULT_SETTINGS,
    );
    expect(ok).toBe(false);
  });

  it("returns false when the network request throws", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("Network error");
      }),
    );

    const ok = await submitFeedbackReport(
      { url: "https://example.test/login", observed_label: "dangerous", expected_label: "safe" },
      DEFAULT_SETTINGS,
    );
    expect(ok).toBe(false);
  });

  it("posts to the /report endpoint", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await submitFeedbackReport(
      { url: "https://example.test/login", observed_label: "safe", expected_label: "dangerous" },
      DEFAULT_SETTINGS,
    );

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/report", expect.objectContaining({ method: "POST" }));
  });

  it("includes optional notes when provided", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await submitFeedbackReport(
      {
        url: "https://example.test/login",
        observed_label: "dangerous",
        expected_label: "safe",
        notes: "This page looks legitimate",
      },
      DEFAULT_SETTINGS,
    );

    const init = fetchMock.mock.calls[0]?.[1];
    if (!init) {
      throw new Error("Missing fetch init");
    }
    const body = JSON.parse(init.body as string) as { notes?: string };
    expect(body.notes).toBe("This page looks legitimate");
  });
});
