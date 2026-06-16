import { afterEach, describe, expect, it, vi } from "vitest";

import { requestBackendStatus, totalCounter } from "./backend-status";
import { DEFAULT_SETTINGS } from "./settings";

describe("backend-status", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns online status with diagnostics", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ status: "ok", service: "phishlens-api" }), { status: 200 }),
        )
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              status: "ok",
              service: "phishlens-api",
              privacy: "aggregate only",
              capabilities: {
                diagnostics_enabled: true,
                rate_limiting_enabled: true,
                threat_intel_enabled: true,
                tls_analysis_enabled: true,
                ml_model_available: false,
                demo_threat_source_enabled: false,
              },
              counters: { analysis_requests: 3 },
              labels: { safe: 2, suspicious: 1 },
              sources: { heuristics: 3 },
            }),
            { status: 200 },
          ),
        ),
    );

    const status = await requestBackendStatus(DEFAULT_SETTINGS);

    expect(status.state).toBe("online");
    expect(status.diagnosticsAvailable).toBe(true);
    expect(totalCounter(status.diagnostics, "analysis_requests")).toBe(3);
  });

  it("keeps backend online when diagnostics are disabled", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ status: "ok", service: "phishlens-api" }), { status: 200 }),
        )
        .mockResolvedValueOnce(new Response(null, { status: 404 })),
    );

    const status = await requestBackendStatus(DEFAULT_SETTINGS);

    expect(status.state).toBe("diagnostics-disabled");
    expect(status.service).toBe("phishlens-api");
    expect(status.diagnosticsAvailable).toBe(false);
  });

  it("returns offline status when health cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );

    const status = await requestBackendStatus(DEFAULT_SETTINGS);

    expect(status.state).toBe("offline");
    expect(status.diagnostics).toBeNull();
  });
});
