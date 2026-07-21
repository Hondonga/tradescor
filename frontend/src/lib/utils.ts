import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { InstrumentPrecision } from "@/types";
export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));
export const titleCase = (value?: string | null) =>
  (value || "")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
export const formatPrice = (
  value?: number | null,
  precision?: InstrumentPrecision,
) => {
  if (value == null) return "—";
  if (!precision || !Number.isInteger(precision.price_decimals))
    return String(value);
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: precision.price_decimals,
    maximumFractionDigits: precision.price_decimals,
    useGrouping: false,
  }).format(value);
};

export const chartPriceFormat = (precision?: InstrumentPrecision) => {
  if (!precision || !Number.isInteger(precision.price_decimals)) return undefined;
  const decimalMove = 10 ** -precision.price_decimals;
  return {
    type: "price" as const,
    precision: precision.price_decimals,
    minMove:
      precision.tick_size && precision.tick_size > 0
        ? precision.tick_size
        : decimalMove,
  };
};
export const friendlyError = (error: unknown) =>
  error instanceof Error
    ? "Market data is temporarily unavailable. Retry when the connection recovers."
    : "The request could not be completed.";
