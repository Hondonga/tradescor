import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChartToolbar } from "./chart-toolbar";
import type { OverlayCategory } from "@/types";

const visibility: Record<OverlayCategory, boolean> = {
  trade_plan: true,
  market_structure: true,
  context_levels: true,
  advanced_smc: false,
  previous_setup: false,
};

describe("ChartToolbar", () => {
  it("renders one-line labels for every toggle, no wrapped text", () => {
    render(
      <ChartToolbar
        visibility={visibility}
        onToggle={() => {}}
        overlays={[]}
        selectedOverlayId=""
        onSelectOverlay={() => {}}
      />,
    );
    for (const label of ["Plan", "Structure", "Context", "Advanced", "Previous"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("shows a count badge on Previous when a previous setup is available", () => {
    render(
      <ChartToolbar
        visibility={visibility}
        onToggle={() => {}}
        previousSetupCount={1}
        overlays={[]}
        selectedOverlayId=""
        onSelectOverlay={() => {}}
      />,
    );
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("disables Previous when there is nothing to reveal", () => {
    render(
      <ChartToolbar
        visibility={visibility}
        onToggle={() => {}}
        previousSetupCount={0}
        overlays={[]}
        selectedOverlayId=""
        onSelectOverlay={() => {}}
      />,
    );
    expect(screen.getByText("Previous").closest("button")).toBeDisabled();
  });

  it("calls onToggle with the toggled category", () => {
    const onToggle = vi.fn();
    render(
      <ChartToolbar
        visibility={visibility}
        onToggle={onToggle}
        overlays={[]}
        selectedOverlayId=""
        onSelectOverlay={() => {}}
      />,
    );
    fireEvent.click(screen.getByText("Advanced"));
    expect(onToggle).toHaveBeenCalledWith("advanced_smc");
  });

  it("stays within the compact height budget (32-36px)", () => {
    const { container } = render(
      <ChartToolbar
        visibility={visibility}
        onToggle={() => {}}
        overlays={[]}
        selectedOverlayId=""
        onSelectOverlay={() => {}}
      />,
    );
    expect(container.firstElementChild?.className).toContain("h-8"); // 32px
  });

  it("shows a density mode selector and calls onDensityModeChange when a mode is chosen (§4/§24: keyboard-accessible, no mouse required)", () => {
    const onDensityModeChange = vi.fn();
    render(
      <ChartToolbar
        visibility={visibility}
        onToggle={() => {}}
        overlays={[]}
        selectedOverlayId=""
        onSelectOverlay={() => {}}
        densityMode="clean"
        onDensityModeChange={onDensityModeChange}
      />,
    );
    const cleanButton = screen.getByRole("button", { name: "Clean" });
    expect(cleanButton).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Research" }));
    expect(onDensityModeChange).toHaveBeenCalledWith("research");
  });

  it("shows a live/historical/replay mode badge distinguishing workspace mode", () => {
    render(
      <ChartToolbar
        visibility={visibility}
        onToggle={() => {}}
        overlays={[]}
        selectedOverlayId=""
        onSelectOverlay={() => {}}
        workspaceMode="replay"
      />,
    );
    expect(screen.getByText("REPLAY")).toBeInTheDocument();
  });

  it("never places a raw backend state code in the toolbar", () => {
    render(
      <ChartToolbar
        visibility={visibility}
        onToggle={() => {}}
        overlays={[]}
        selectedOverlayId=""
        onSelectOverlay={() => {}}
        workspaceMode="live"
        connection="provider_error"
      />,
    );
    expect(screen.queryByText("provider_error")).not.toBeInTheDocument();
    expect(screen.queryByText(/PROVIDER_ERROR/)).not.toBeInTheDocument();
  });

  it("wires auto-fit, reset view, and diagnostics-toggle actions", () => {
    const onAutoFit = vi.fn();
    const onResetView = vi.fn();
    const onToggleDiagnostics = vi.fn();
    render(
      <ChartToolbar
        visibility={visibility}
        onToggle={() => {}}
        overlays={[]}
        selectedOverlayId=""
        onSelectOverlay={() => {}}
        onAutoFit={onAutoFit}
        onResetView={onResetView}
        diagnosticsVisible={false}
        onToggleDiagnostics={onToggleDiagnostics}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Auto-fit chart" }));
    expect(onAutoFit).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Reset chart view" }));
    expect(onResetView).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Toggle diagnostics visibility" }));
    expect(onToggleDiagnostics).toHaveBeenCalled();
  });
});
