import { AlertTriangle, Check, Circle, Clock3, X } from "lucide-react";
import { cn } from "@/lib/utils";
export type StatusTone =
  "ready" | "developing" | "waiting" | "neutral" | "error";
const map = {
  ready: {
    Icon: Check,
    style: "border-emerald-400/25 bg-emerald-400/8 text-emerald-300",
  },
  developing: {
    Icon: Circle,
    style: "border-blue-400/25 bg-blue-400/8 text-blue-300",
  },
  waiting: {
    Icon: Clock3,
    style: "border-amber-400/25 bg-amber-400/8 text-amber-300",
  },
  neutral: { Icon: X, style: "border-white/10 bg-white/[.035] text-zinc-400" },
  error: {
    Icon: AlertTriangle,
    style: "border-red-400/25 bg-red-400/8 text-red-300",
  },
};
export function StatusBadge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: StatusTone;
  children: React.ReactNode;
  className?: string;
}) {
  const { Icon, style } = map[tone];
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center gap-1.5 rounded-md border px-2 font-mono text-[10px] font-semibold uppercase tracking-wide",
        style,
        className,
      )}
    >
      <Icon size={11} />
      {children}
    </span>
  );
}
