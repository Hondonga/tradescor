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
});
