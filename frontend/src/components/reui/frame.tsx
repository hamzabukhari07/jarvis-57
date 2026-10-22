import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

/**
 * Forma OS Frame & FramePanel Component
 */
const frameVariants = cva(
 "relative flex flex-col min-h-0 bg-transparent",
 {
 variants: {
 variant: {
 default: "",
 inverse: "bg-[var(--background)]",
 ghost: "",
 },
 spacing: {
 xs: "gap-1",
 sm: "gap-1.5",
 default: "gap-2",
 lg: "gap-3",
 },
 },
 defaultVariants: {
 variant: "default",
 spacing: "default",
 },
 }
)

export function Frame({
 className,
 variant,
 spacing,
 ...props
}: React.ComponentProps<"div"> & VariantProps<typeof frameVariants>) {
 return (
 <div
 className={cn(frameVariants({ variant, spacing }), className)}
 data-slot="frame"
 {...props}
 />
 )
}

export function FramePanel({
 className,
 fit,
 ...props
}: React.ComponentProps<"div"> & { fit?: boolean }) {
 return (
 <div
 className={cn(
 "relative overflow-hidden rounded-[var(--radius,0.625rem)] border border-[var(--border)] bg-[var(--card)] text-[var(--card-foreground,var(--foreground))] transition-colors duration-200",
 !fit && "grow",
 "p-3.5",
 className
 )}
 data-slot="frame-panel"
 {...props}
 />
 )
}

export function FrameHeader({ className, ...props }: React.ComponentProps<"header">) {
 return (
 <header
 className={cn("flex flex-col gap-1 pb-2", className)}
 data-slot="frame-panel-header"
 {...props}
 />
 )
}

export function FrameTitle({ className, ...props }: React.ComponentProps<"div">) {
 return (
 <div
 className={cn("text-xs font-semibold uppercase tracking-wider text-[var(--foreground)]", className)}
 data-slot="frame-panel-title"
 {...props}
 />
 )
}

export function FrameDescription({ className, ...props }: React.ComponentProps<"div">) {
 return (
 <div
 className={cn("text-xs text-[var(--muted-foreground)]", className)}
 data-slot="frame-panel-description"
 {...props}
 />
 )
}
