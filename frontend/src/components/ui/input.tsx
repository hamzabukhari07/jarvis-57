import * as React from "react"
import { cn } from "@/lib/utils"

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
 ({ className, type, ...props }, ref) => {
 return (
 <input
 type={type}
 className={cn(
 "flex h-9 w-full rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] border border-[var(--border)] bg-[var(--input)]/70 px-3 py-1 text-xs text-[var(--foreground)] transition-colors file:border-0 file:bg-transparent file:text-xs file:font-medium placeholder:text-[var(--muted-foreground)] focus-visible:outline-hidden focus-visible:border-[var(--primary)] focus-visible:ring-1 focus-visible:ring-[var(--ring)] disabled:cursor-not-allowed disabled:opacity-50 font-mono",
 className
 )}
 ref={ref}
 {...props}
 />
 )
 }
)
Input.displayName = "Input"
