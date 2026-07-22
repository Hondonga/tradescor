import { describe, expect, it } from "vitest";
import {
  canonicalStatus,
  canonicalStatusTone,
  directionLabel,
  entryTimingCopy,
  isLateEntryTiming,
} from "./status-labels";
import type { NormalizedDecision } from "@/types";

function decisionWith(overrides: {
  trade_ready?: boolean;
  status?: string;
  stage?: string;
  direction?: string | null;
  entry_timing_status?: string;
}): NormalizedDecision {
  return {
    decision: {
      status: overrides.status ?? "SELL SETUP DEVELOPING",
      direction: (overrides.direction ?? "sell") as "buy" | "sell",
      stage: overrides.stage ?? "WAITING_FOR_DISPLACEMENT",
      headline: "",
      summary: "",
      next_action: "",
      trade_ready: overrides.trade_ready ?? false,
    },
    entry_timing: overrides.entry_timing_status
      ? {
          status: overrides.entry_timing_status,
          message: "",
          next_action: "",
          can_enter_now: false,
        }
      : undefined,
  } as unknown as NormalizedDecision;
}

describe("canonicalStatus — the only three statuses the UI ever shows", () => {
  it("maps a trade-ready decision to TRADE READY regardless of the raw status string", () => {
    expect(canonicalStatus(decisionWith({ trade_ready: true, status: "ENTRY READY" }))).toBe("TRADE READY");
    expect(canonicalStatus(decisionWith({ trade_ready: true, status: "READY TO SELL" }))).toBe("TRADE READY");
  });

  it("maps NO TRADE / INVALIDATED / TOO LATE / EXPIRED / STATE CONTRADICTION to AVOID", () => {
    expect(canonicalStatus(decisionWith({ status: "NO TRADE" }))).toBe("AVOID");
    expect(canonicalStatus(decisionWith({ status: "SETUP INVALIDATED", stage: "INVALIDATED" }))).toBe("AVOID");
    expect(canonicalStatus(decisionWith({ status: "TOO LATE", stage: "TOO_LATE" }))).toBe("AVOID");
    expect(canonicalStatus(decisionWith({ status: "SETUP EXPIRED", stage: "EXPIRED" }))).toBe("AVOID");
    expect(canonicalStatus(decisionWith({ status: "STATE CONTRADICTION" }))).toBe("AVOID");
  });

  it("maps WAIT / WAITING FOR RETEST / WAITING FOR CONFIRMATION / developing setups to WATCHLIST", () => {
    expect(canonicalStatus(decisionWith({ status: "WAIT" }))).toBe("WATCHLIST");
    expect(canonicalStatus(decisionWith({ status: "WAITING FOR RETEST" }))).toBe("WATCHLIST");
    expect(canonicalStatus(decisionWith({ status: "WAITING FOR CONFIRMATION" }))).toBe("WATCHLIST");
    expect(canonicalStatus(decisionWith({ status: "SELL SETUP DEVELOPING" }))).toBe("WATCHLIST");
    expect(canonicalStatus(decisionWith({ status: "MARKET CONTEXT", direction: null }))).toBe("WATCHLIST");
  });

  it("maps a too_late entry-timing classification to AVOID even when the raw status looks neutral", () => {
    expect(canonicalStatus(decisionWith({ status: "SELL SETUP DEVELOPING", entry_timing_status: "too_late" }))).toBe("AVOID");
    expect(canonicalStatus(decisionWith({ status: "BUY SETUP DEVELOPING", entry_timing_status: "missed" }))).toBe("AVOID");
    expect(canonicalStatus(decisionWith({ status: "BUY SETUP DEVELOPING", entry_timing_status: "invalid" }))).toBe("AVOID");
  });

  it("never returns anything other than one of the three canonical statuses", () => {
    const statuses = ["NO TRADE", "WAIT", "ENTRY READY", "WAITING FOR RETEST", "WAITING FOR CONFIRMATION", "INVALIDATED", "READY TO BUY", "MARKET CONTEXT", "TOO LATE"];
    for (const status of statuses) {
      expect(["TRADE READY", "WATCHLIST", "AVOID"]).toContain(canonicalStatus(decisionWith({ status })));
    }
  });
});

describe("canonicalStatusTone", () => {
  it("maps each canonical status to a distinct badge tone", () => {
    expect(canonicalStatusTone("TRADE READY")).toBe("ready");
    expect(canonicalStatusTone("WATCHLIST")).toBe("waiting");
    expect(canonicalStatusTone("AVOID")).toBe("error");
  });
});

describe("directionLabel", () => {
  it("renders BUY setup / SELL setup / Neutral", () => {
    expect(directionLabel("buy")).toBe("BUY setup");
    expect(directionLabel("sell")).toBe("SELL setup");
    expect(directionLabel(null)).toBe("Neutral");
    expect(directionLabel(undefined)).toBe("Neutral");
  });
});

describe("entryTimingCopy — exact required wording", () => {
  it("returns the exact required message for each entry-timing status", () => {
    expect(entryTimingCopy("at_entry")).toEqual({
      label: "AT ENTRY",
      message: "Price is inside the entry zone. Confirm risk before entering.",
    });
    expect(entryTimingCopy("near_entry")).toEqual({
      label: "NEAR ENTRY",
      message: "Price is near the entry zone. Entry may still be valid if risk/reward holds.",
    });
    expect(entryTimingCopy("extended")).toEqual({
      label: "EXTENDED",
      message: "Price has moved away from entry. Do not chase. Wait for a pullback.",
    });
    expect(entryTimingCopy("too_late")).toEqual({
      label: "TOO LATE",
      message: "Too late to enter now. Price is too far from entry and reward is reduced.",
    });
    expect(entryTimingCopy("missed")).toEqual({
      label: "MISSED",
      message: "Setup already moved to target area. Wait for the next setup.",
    });
    expect(entryTimingCopy("invalid")).toEqual({
      label: "INVALID",
      message: "Setup is invalidated. Do not enter.",
    });
  });

  it("is case-insensitive and returns null for an unknown or missing status", () => {
    expect(entryTimingCopy("TOO_LATE")).toEqual(entryTimingCopy("too_late"));
    expect(entryTimingCopy(undefined)).toBeNull();
    expect(entryTimingCopy("")).toBeNull();
    expect(entryTimingCopy("unknown_status")).toBeNull();
  });
});

describe("isLateEntryTiming", () => {
  it("is true only for extended/too_late/missed/invalid", () => {
    expect(isLateEntryTiming("extended")).toBe(true);
    expect(isLateEntryTiming("too_late")).toBe(true);
    expect(isLateEntryTiming("missed")).toBe(true);
    expect(isLateEntryTiming("invalid")).toBe(true);
    expect(isLateEntryTiming("at_entry")).toBe(false);
    expect(isLateEntryTiming("near_entry")).toBe(false);
    expect(isLateEntryTiming(undefined)).toBe(false);
  });
});
