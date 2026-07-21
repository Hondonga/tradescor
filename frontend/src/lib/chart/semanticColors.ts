// Single canonical source for every color used in canvas-rendered chart
// output (lightweight-charts draws to a <canvas>, so it cannot read CSS
// custom properties at draw time -- these values must be literal hex/rgba).
// DOM-rendered chrome uses the matching CSS custom properties declared in
// styles.css's `@theme` block; the two must be kept numerically in sync.
export const SEMANTIC_COLORS = {
  bullish: "#36bd80",
  bearish: "#e2685f",
  neutral: "#8b97ab",
  warning: "#e0b064",
  research: "#8a7cd6",
  actionable: "#5d98f8",
  historical: "#5b6b85",
  disabled: "#454e5c",
} as const;

export type SemanticColorToken = keyof typeof SEMANTIC_COLORS;
