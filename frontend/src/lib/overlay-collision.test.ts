import { describe, expect, it } from "vitest";
import { resolveCollisions } from "./overlay-collision";

describe("resolveCollisions", () => {
  it("leaves non-overlapping items in their natural position", () => {
    const items = [
      { id: "a", y: 10, height: 12, priority: 100 },
      { id: "b", y: 100, height: 12, priority: 90 },
    ];
    const resolved = resolveCollisions(items);
    expect(resolved.find((r) => r.id === "a")!.resolvedY).toBe(10);
    expect(resolved.find((r) => r.id === "b")!.resolvedY).toBe(100);
  });

  it("offsets a lower-priority overlapping item away from a higher-priority one", () => {
    const items = [
      { id: "high", y: 50, height: 14, priority: 100 },
      { id: "low", y: 52, height: 14, priority: 20 },
    ];
    const resolved = resolveCollisions(items, { minGap: 2 });
    const high = resolved.find((r) => r.id === "high")!;
    const low = resolved.find((r) => r.id === "low")!;
    expect(high.resolvedY).toBe(50); // higher priority keeps its natural slot
    expect(Math.abs(low.resolvedY - high.resolvedY)).toBeGreaterThanOrEqual(14 / 2 + 14 / 2 + 2);
    expect(low.offset).not.toBe(0);
  });

  it("no two resolved items occupy overlapping vertical space", () => {
    const items = [
      { id: "a", y: 40, height: 10, priority: 100 },
      { id: "b", y: 41, height: 10, priority: 90 },
      { id: "c", y: 42, height: 10, priority: 80 },
      { id: "d", y: 43, height: 10, priority: 70 },
    ];
    const resolved = resolveCollisions(items, { minGap: 1 });
    const sorted = [...resolved].sort((x, y) => x.resolvedY - y.resolvedY);
    for (let i = 1; i < sorted.length; i++) {
      const prevBottom = sorted[i - 1].resolvedY + sorted[i - 1].height / 2;
      const top = sorted[i].resolvedY - sorted[i].height / 2;
      expect(top).toBeGreaterThanOrEqual(prevBottom - 0.001);
    }
  });

  it("hides the lowest-priority items first when the viewport is too small", () => {
    const items = [
      { id: "a", y: 15, height: 20, priority: 100 },
      { id: "b", y: 32, height: 20, priority: 50 },
      { id: "c", y: 60, height: 20, priority: 10 },
    ];
    const resolved = resolveCollisions(items, { minGap: 2, viewportHeight: 50 });
    expect(resolved.find((r) => r.id === "a")!.visible).toBe(true);
    expect(resolved.find((r) => r.id === "c")!.visible).toBe(false);
  });

  it("is deterministic for the same input", () => {
    const items = [
      { id: "a", y: 10, height: 10, priority: 60 },
      { id: "b", y: 12, height: 10, priority: 60 },
    ];
    expect(resolveCollisions(items)).toEqual(resolveCollisions(items));
  });
});
