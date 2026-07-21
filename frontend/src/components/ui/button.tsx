import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
const variants = cva(
  "inline-flex h-8 items-center justify-center gap-2 rounded-md border px-3 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        primary: "border-blue-400/50 bg-blue-500 text-white hover:bg-blue-400",
        secondary:
          "border-white/10 bg-white/[.035] text-zinc-200 hover:bg-white/[.07]",
        ghost:
          "border-transparent text-zinc-400 hover:bg-white/[.05] hover:text-zinc-100",
        danger: "border-red-400/25 bg-red-500/10 text-red-300",
      },
    },
    defaultVariants: { variant: "secondary" },
  },
);
export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof variants> {}
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(variants({ variant }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";
