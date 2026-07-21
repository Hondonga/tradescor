import type { Meta, StoryObj } from "@storybook/react-vite";
import {
  ContradictionState,
  DataLoadingState,
  DecisionHeader,
  DevelopingSetup,
  EmptyEvidence,
  NoOpportunityState,
  ProviderErrorState,
  ReplayProgress,
  ScannerRowPreview,
  StaleConnectionState,
  SymbolSelectorPreview,
  TradeReadyPlan,
} from "./status-components";
import { StatusBadge } from "@/components/ui/status-badge";
import type { NormalizedDecision } from "@/types";
const decision = {
  decision_id: "d",
  overlay_mode: "LIVE",
  precision: {
    symbol_id: "deriv:R_50",
    price_decimals: 4,
    pip_size: null,
    tick_size: 0.0001,
    quantity_decimals: null,
  },
  meta: {
    symbol: "R_50",
    display_symbol: "Volatility 50",
    timeframe: "M5",
    family: "VOLATILITY",
    analysis_time: "2026-07-19T12:00:00Z",
    live: true,
    market_schedule: "24_7",
    analysis_clock: "UTC",
  },
  ownership: {
    selected_model_id: "smc_auto",
    decision_owner_id: "smc_auto",
    overlay_owner_id: "smc_auto",
  },
  readiness: { state: "ready" },
  market: {
    external_structure: "bearish",
    internal_structure: "bearish",
    current_price: 86.1,
  },
  decision: {
    status: "SELL SETUP DEVELOPING",
    direction: "sell",
    stage: "WAITING_FOR_CONFIRMATION",
    headline: "Bearish pullback developing",
    summary: "",
    next_action: "Wait",
    trade_ready: false,
  },
  setup: {
    setup_id: "s",
    setup_type: "structure_pullback",
    direction: "sell",
    stage: "WAITING_FOR_CONFIRMATION",
    status: "SELL SETUP DEVELOPING",
    context_summary:
      "H1 structure is bearish. Price is approaching the selected M15 premium area.",
    next_required_condition: "Completed bearish M5 MSS.",
    trade_ready: false,
    targets: [],
    quality_score: 78,
    quality_grade: "B",
  },
  diagnostics: {},
  overlays: [],
  current_market: {
    external_structure: "bearish",
    internal_structure: "pullback",
    current_price: 86.1,
  },
  active_setup: {
    setup_id: "s",
    setup_type: "structure_pullback",
    direction: "sell",
    stage: "WAITING_FOR_CONFIRMATION",
    status: "SELL SETUP DEVELOPING",
    context_summary:
      "H1 structure is bearish. Price is approaching the selected M15 premium area.",
    next_required_condition: "Completed bearish M5 MSS.",
    trade_ready: false,
    targets: [],
    quality_score: 78,
    quality_grade: "B",
  },
} as NormalizedDecision;
const ready = {
  ...decision,
  decision: {
    ...decision.decision,
    status: "READY TO SELL",
    trade_ready: true,
  },
  setup: {
    ...decision.setup,
    trade_ready: true,
    entry: 86.2,
    stop: 86.5,
    targets: [{ name: "TP1", price: 85.6, risk_reward: 2 }],
    target_source: "internal_swing",
    target_timeframe: "M15",
  },
  active_setup: {
    ...decision.setup,
    trade_ready: true,
    stage: "TRADE_READY",
    entry: 86.2,
    stop: 86.5,
    targets: [{ name: "TP1", price: 85.6, risk_reward: 2 }],
    target_source: "internal_swing",
    target_timeframe: "M15",
  },
  trade_plan: {
    available: true,
    status: "VALID",
    entry: 86.2,
    stop: 86.5,
    targets: [{ name: "TP1", price: 85.6, risk_reward: 2 }],
  },
} as NormalizedDecision;
const meta: Meta = {
  title: "Terminal/Required states",
  parameters: {
    backgrounds: {
      default: "terminal",
      values: [{ name: "terminal", value: "#07090d" }],
    },
  },
};
export default meta;
type Story = StoryObj;
export const SymbolSelector: Story = {
  render: () => <SymbolSelectorPreview />,
};
export const StatusBadges: Story = {
  render: () => (
    <div className="flex gap-2">
      <StatusBadge tone="ready">Ready</StatusBadge>
      <StatusBadge tone="developing">Developing</StatusBadge>
      <StatusBadge tone="waiting">Waiting</StatusBadge>
    </div>
  ),
};
export const ScannerRow: Story = { render: () => <ScannerRowPreview /> };
export const DecisionHeaderState: Story = {
  render: () => (
    <div className="w-80 bg-[#0b0e14]">
      <DecisionHeader decision={decision} />
    </div>
  ),
};
export const DevelopingSetupState: Story = {
  render: () => (
    <div className="w-80 bg-[#0b0e14]">
      <DevelopingSetup decision={decision} />
    </div>
  ),
};
export const TradeReadyPlanState: Story = {
  render: () => (
    <div className="w-80 bg-[#0b0e14]">
      <TradeReadyPlan decision={ready} />
    </div>
  ),
};
export const NoOpportunity: Story = { render: () => <NoOpportunityState /> };
export const DataLoading: Story = { render: () => <DataLoadingState /> };
export const ProviderError: Story = { render: () => <ProviderErrorState /> };
export const StaleConnection: Story = {
  render: () => <StaleConnectionState />,
};
export const Contradiction: Story = { render: () => <ContradictionState /> };
export const ReplayProgressState: Story = { render: () => <ReplayProgress /> };
export const EmptyEvidenceState: Story = { render: () => <EmptyEvidence /> };
