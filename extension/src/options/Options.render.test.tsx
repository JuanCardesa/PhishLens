// @vitest-environment happy-dom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as backendStatus from "../services/backend-status";
import type { BackendStatus } from "../types/analysis";
import { Options } from "./Options";

function makeBackendStatus(overrides: Partial<BackendStatus> = {}): BackendStatus {
  return {
    state: "online",
    service: "phishlens-api",
    diagnosticsAvailable: true,
    diagnostics: null,
    message: "Backend is online with diagnostics enabled.",
    checkedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe("Options", () => {
  beforeEach(() => {
    vi.spyOn(backendStatus, "requestBackendStatus").mockResolvedValue(makeBackendStatus());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads stored settings and checks backend status on mount", async () => {
    render(<Options />);

    await waitFor(() => expect(screen.getByText("Settings loaded")).toBeInTheDocument());
    expect(backendStatus.requestBackendStatus).toHaveBeenCalled();
    expect(screen.getByDisplayValue("http://localhost:8000")).toBeInTheDocument();
  });

  it("saves settings and refreshes backend status on submit", async () => {
    render(<Options />);
    await waitFor(() => expect(screen.getByText("Settings loaded")).toBeInTheDocument());

    fireEvent.change(screen.getByDisplayValue("http://localhost:8000"), {
      target: { value: "http://127.0.0.1:8000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));

    await waitFor(() => expect(screen.getByText("Settings saved")).toBeInTheDocument());
    expect(backendStatus.requestBackendStatus).toHaveBeenCalledTimes(2);
  });

  it("refreshes backend status when Refresh is clicked", async () => {
    render(<Options />);
    await waitFor(() => expect(screen.getByText("Settings loaded")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => expect(backendStatus.requestBackendStatus).toHaveBeenCalledTimes(2));
  });

  it("shows Unavailable diagnostics label when the backend is offline", async () => {
    vi.spyOn(backendStatus, "requestBackendStatus").mockResolvedValue(
      makeBackendStatus({ state: "offline", diagnosticsAvailable: false, message: "Backend is unreachable." }),
    );
    render(<Options />);

    await waitFor(() => expect(screen.getByText("Backend is unreachable.")).toBeInTheDocument());
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
  });
});
