import * as React from "react"
import { cn } from "@/lib/utils"

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
 value?: number
 indicatorClassName?: string
}

export const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
 ({ className, value = 0, indicatorClassName, ...props }, ref) => {
 return (
 <div
 ref={ref}
 className={cn(
 "relative h-1.5 w-full overflow-hidden rounded-full bg-[var(--card)] border border-[var(--border)]",
 className
 )}
 {...props}
 >
 <div
 className={cn("h-full bg-[var(--primary)] transition-all duration-300", indicatorClassName)}
 style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
 />
 </div>
 )
 }
)
Progress.displayName = "Progress"
