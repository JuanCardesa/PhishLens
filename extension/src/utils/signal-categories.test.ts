import { describe, expect, it } from "vitest";

import { groupReasonsBySignal, primarySignalReason } from "./signal-categories";

const SOURCES = {
  heuristics: true,
  ml: false,
  phishtank: false,
  tls: false,
};

describe("signal-categories", () => {
  it("groups URL and DOM reasons separately", () => {
    const groups = groupReasonsBySignal(
      ["URL contains many dots", "Page contains a password field", "Form submits data to an external domain"],
      SOURCES,
    );

    expect(groups.map((group) => group.id)).toEqual(["url", "dom"]);
    expect(groups[1].reasons).toHaveLength(2);
  });

  it("adds neutral source explanations when backend sources were checked", () => {
    const groups = groupReasonsBySignal(["No high-risk signals were detected"], {
      ...SOURCES,
      phishtank: true,
      tls: true,
      ml: true,
    });

    expect(groups.map((group) => group.id)).toEqual(["threat-intel", "tls", "ml", "general"]);
  });

  it("selects a primary reason with category context", () => {
    const groups = groupReasonsBySignal(["TLS certificate appears to be expired"], {
      ...SOURCES,
      tls: true,
    });

    expect(primarySignalReason(groups)).toBe("TLS: TLS certificate appears to be expired");
  });
});
