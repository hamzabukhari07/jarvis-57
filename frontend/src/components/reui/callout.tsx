import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const calloutVariants = cva(
 "relative w-full rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] border p-3 text-xs [&>svg~*]:pl-6 [&>svg+div]:translate-y-[-2px] [&>svg]:absolute [&>svg]:left-3 [&>svg]:top-3.5 [&>svg]:text-foreground",
 {
 variants: {
 variant: {
 default: "bg-[var(--input)]/60 border-[var(--border)] text-[var(--foreground)]",
 info: "bg-[var(--primary)]/10 border-[var(--primary)]/30 text-[var(--foreground)] [&>svg]:text-[var(--primary)]",
 success: "bg-emerald-500/10 border-emerald-500/30 text-[var(--foreground)] [&>svg]:text-emerald-500",
 warning: "bg-amber-500/10 border-amber-500/30 text-[var(--foreground)] [&>svg]:text-amber-500",
 destructive: "bg-red-500/10 border-red-500/30 text-[var(--foreground)] [&>svg]:text-red-500",
 },
 },
 defaultVariants: {
 variant: "default",
 },
 }
)

export function Callout({
 className,
 variant,
 ...props
}: React.ComponentProps<"div"> & VariantProps<typeof calloutVariants>) {
 return (
 <div
 data-slot="callout"
 role="alert"
 className={cn(calloutVariants({ variant }), className)}
 {...props}
 />
 )
}
