import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import type { DOMFeatures } from "../types/analysis";
import { analyzeLocally } from "./risk-score";

// The scoring logic is reimplemented in two languages (this file's analyzeLocally
// and the backend's scoring_service.py). Both load the same vectors from
// contracts/scoring-vectors.json and assert identical per-category scores and
// reason strings, so a weight or wording changed on only one side fails here.
// The mirror is backend/tests/test_scoring_contract.py.
interface ScoringVector {
  name: string;
  url: string;
  dom: Partial<DOMFeatures>;
  url_score: number;
  url_reasons: string[];
  dom_score: number;
  dom_reasons: string[];
}

interface ScoringContract {
  dom_defaults: DOMFeatures;
  vectors: ScoringVector[];
}

const contractPath = fileURLToPath(new URL("../../../contracts/scoring-vectors.json", import.meta.url));
const contract = JSON.parse(readFileSync(contractPath, "utf8")) as ScoringContract;

describe("scoring contract (mirrors backend/tests/test_scoring_contract.py)", () => {
  for (const vector of contract.vectors) {
    it(vector.name, () => {
      const domFeatures: DOMFeatures = { ...contract.dom_defaults, ...vector.dom };
      const result = analyzeLocally(vector.url, domFeatures);
      const urlItem = result.risk_breakdown?.find((item) => item.category === "url");
      const domItem = result.risk_breakdown?.find((item) => item.category === "dom");

      expect(urlItem?.score).toBe(vector.url_score);
      expect(urlItem?.reasons).toEqual(vector.url_reasons);
      expect(domItem?.score).toBe(vector.dom_score);
      expect(domItem?.reasons).toEqual(vector.dom_reasons);
    });
  }
});
