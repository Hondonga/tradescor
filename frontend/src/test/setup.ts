import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// This repo's vitest config doesn't set `globals: true`, so Testing
// Library's automatic per-test cleanup (which hooks the global `afterEach`)
// never registers. Without this, DOM from one render() leaks into the next
// test in the same file, causing "found multiple elements" false failures.
afterEach(() => cleanup());

const values = new Map<string, string>();
Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
    key: (index: number) => [...values.keys()][index] ?? null,
    get length() {
      return values.size;
    },
  },
});
