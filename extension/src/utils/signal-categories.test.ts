import { describe, expect, it } from "vitest";

import { formatSignalScore, groupReasonsBySignal, primarySignalReason } from "./signal-categories";

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

  it("builds groups from structured risk breakdown", () => {
    const groups = groupReasonsBySignal(["URL contains many dots"], SOURCES, [
      {
        category: "url",
        score: 12,
        min_score: 0,
        max_score: 35,
        reasons: ["URL contains many dots"],
        source: "heuristics",
      },
      {
        category: "ml",
        score: -5,
        min_score: -10,
        max_score: 20,
        reasons: ["Machine learning model reduced the estimated risk"],
        source: "ml",
      },
    ]);

    expect(groups.map((group) => group.id)).toEqual(["url", "ml"]);
    expect(formatSignalScore(groups[0])).toBe("12/35");
    expect(formatSignalScore(groups[1])).toBe("-5 (-10 to +20)");
  });

  it("prefixes positive ML adjustments with a plus sign", () => {
    const group = {
      id: "ml" as const,
      title: "ML",
      score: 12,
      minScore: -10,
      maxScore: 20,
      reasons: ["Machine learning model increased the estimated risk"],
    };

    expect(formatSignalScore(group)).toBe("+12 (-10 to +20)");
  });

  it("does not add a prefix to zero ML adjustment", () => {
    const group = {
      id: "ml" as const,
      title: "ML",
      score: 0,
      minScore: -10,
      maxScore: 20,
      reasons: [],
    };

    expect(formatSignalScore(group)).toBe("0 (-10 to +20)");
  });
});
