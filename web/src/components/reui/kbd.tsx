import * as React from "react"
import { cn } from "@/lib/utils"

export function Kbd({ className, children, ...props }: React.ComponentProps<"kbd">) {
  return (
    <kbd
      data-slot="kbd"
      className={cn(
        "inline-flex items-center justify-center font-mono font-bold text-xs uppercase px-2 py-1 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] shadow-2xs select-none",
        className
      )}
      {...props}
    >
      {children}
    </kbd>
  )
}
