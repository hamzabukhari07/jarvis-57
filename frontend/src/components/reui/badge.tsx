import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

/**
 * Forma OS Badge Component
 */
const badgeVariants = cva(
  "inline-flex items-center justify-center font-medium font-mono text-[10px] uppercase tracking-wider transition-colors rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))]",
  {
    variants: {
      variant: {
        default: "bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/35",
        secondary: "bg-[var(--secondary)] text-[var(--secondary-foreground,var(--muted-foreground))] border border-[var(--border)]",
        outline: "border border-[var(--border)] text-[var(--foreground)] bg-transparent",
        accent: "bg-[var(--accent)]/15 text-[var(--foreground)] border border-[var(--accent)]/35",
        running: "bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/40 shadow-2xs",
        completed: "bg-emerald-500/15 text-emerald-500 border border-emerald-500/30",
        queued: "bg-[var(--muted)] text-[var(--muted-foreground)] border border-[var(--border)]",
        destructive: "bg-red-500/15 text-red-500 border border-red-500/30",
        warning: "bg-amber-500/15 text-amber-500 border border-amber-500/30",
        success: "bg-emerald-500/15 text-emerald-500 border border-emerald-500/30",
      },
      size: {
        xs: "px-1.5 py-0.5 text-[9px] h-4",
        sm: "px-2 py-0.5 text-[10px] h-5",
        default: "px-2.5 py-1 text-[11px] h-6",
      },
      radius: {
        default: "rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))]",
        full: "rounded-full",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "sm",
      radius: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, size, radius, ...props }: BadgeProps) {
  return (
    <span
      className={cn(badgeVariants({ variant, size, radius }), className)}
      data-slot="badge"
      {...props}
    />
  )
}
