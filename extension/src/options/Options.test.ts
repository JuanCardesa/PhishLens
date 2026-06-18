import { describe, expect, it } from "vitest";

import { diagnosticsLabelFor } from "./Options";
import type { BackendStatus } from "../types/analysis";

function makeBackendStatus(overrides: Partial<BackendStatus> = {}): BackendStatus {
  return {
    state: "online",
    service: "phishlens-api",
    diagnosticsAvailable: true,
    diagnostics: null,
    message: "Backend is reachable.",
    checkedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe("diagnosticsLabelFor", () => {
  it("returns Enabled when diagnostics are available", () => {
    expect(diagnosticsLabelFor(makeBackendStatus({ diagnosticsAvailable: true }))).toBe("Enabled");
  });

  it("returns Disabled when state is diagnostics-disabled", () => {
    expect(
      diagnosticsLabelFor(makeBackendStatus({ diagnosticsAvailable: false, state: "diagnostics-disabled" })),
    ).toBe("Disabled");
  });

  it("returns Unavailable when backend is offline", () => {
    expect(
      diagnosticsLabelFor(makeBackendStatus({ diagnosticsAvailable: false, state: "offline" })),
    ).toBe("Unavailable");
  });

  it("returns Unavailable when backendStatus is null (not yet checked)", () => {
    expect(diagnosticsLabelFor(null)).toBe("Unavailable");
  });
});
