// @vitest-environment happy-dom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as analysisApi from "../services/analysis-api";
import type { AnalysisResponse } from "../types/analysis";
import { Popup } from "./Popup";

function makeBackendResponse(overrides: Partial<AnalysisResponse> = {}): AnalysisResponse {
  return {
    risk_score: 12,
    label: "safe",
    confidence: 0.95,
    reasons: ["URL uses HTTPS"],
    sources: { heuristics: true, ml: true, phishtank: true, tls: true, demo: false },
    risk_breakdown: [],
    ...overrides,
  };
}

function mockActiveTab(url: string) {
  const impl = (_query: chrome.tabs.QueryInfo, callback: (tabs: chrome.tabs.Tab[]) => void) => {
    callback([{ id: 1, url } as chrome.tabs.Tab]);
  };
  vi.mocked(chrome.tabs.query).mockImplementation(impl as never);
}

function mockDomCollection() {
  const impl = (_tabId: number, _message: unknown, callback: (response: unknown) => void) => {
    callback({
      ok: true,
      dom_features: {
        has_password_field: false,
        num_forms: 0,
        external_form_action: false,
        num_iframes: 0,
        external_links_ratio: 0,
        has_hidden_inputs: false,
      },
    });
  };
  vi.mocked(chrome.tabs.sendMessage).mockImplementation(impl as never);
}

describe("Popup", () => {
  beforeEach(() => {
    mockActiveTab("https://example.test/");
    mockDomCollection();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state before analysis resolves", () => {
    vi.spyOn(analysisApi, "requestBackendAnalysis").mockImplementation(() => new Promise(() => {}));
    render(<Popup />);

    expect(screen.getByText("Analyzing current page...")).toBeInTheDocument();
  });

  it("renders the backend-enriched result once analysis resolves", async () => {
    vi.spyOn(analysisApi, "requestBackendAnalysis").mockResolvedValue(makeBackendResponse());
    render(<Popup />);

    await waitFor(() => expect(screen.getByText("Safe")).toBeInTheDocument());
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Backend enrichment is active for this result.")).toBeInTheDocument();
  });

  it("falls back to local-only analysis when the backend is unavailable", async () => {
    vi.spyOn(analysisApi, "requestBackendAnalysis").mockResolvedValue(null);
    render(<Popup />);

    await waitFor(() => expect(screen.getAllByText(/Backend unavailable/).length).toBeGreaterThan(0));
  });

  it("shows an error when the active tab cannot be analyzed", async () => {
    mockActiveTab("chrome://extensions");
    render(<Popup />);

    await waitFor(() =>
      expect(screen.getByText("This page cannot be analyzed by the extension.")).toBeInTheDocument(),
    );
  });

  it("sends feedback and shows a confirmation message", async () => {
    vi.spyOn(analysisApi, "requestBackendAnalysis").mockResolvedValue(makeBackendResponse());
    vi.spyOn(analysisApi, "submitFeedbackReport").mockResolvedValue(true);
    render(<Popup />);

    await waitFor(() => expect(screen.getByText("Safe")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Mark as safe" }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Feedback sent"));
    expect(analysisApi.submitFeedbackReport).toHaveBeenCalledWith(
      { url: "https://example.test/", observed_label: "safe", expected_label: "safe" },
      expect.anything(),
    );
  });

  it("opens the options page when Settings is clicked", async () => {
    vi.spyOn(analysisApi, "requestBackendAnalysis").mockResolvedValue(makeBackendResponse());
    render(<Popup />);

    await waitFor(() => expect(screen.getByText("Safe")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Open settings" }));

    expect(chrome.runtime.openOptionsPage).toHaveBeenCalled();
  });
});
