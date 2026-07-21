import type { LucideIcon } from "lucide-react";
import { Button } from "./button";
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  onAction,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action: string;
  onAction?: () => void;
}) {
  return (
    <div className="grid min-h-52 place-items-center px-8 py-12 text-center">
      <div className="max-w-sm">
        <Icon className="mx-auto mb-4 text-zinc-600" size={24} />
        <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
        <p className="mt-2 text-xs leading-5 text-zinc-500">{description}</p>
        <Button variant="primary" className="mt-5" onClick={onAction}>
          {action}
        </Button>
      </div>
    </div>
  );
}
