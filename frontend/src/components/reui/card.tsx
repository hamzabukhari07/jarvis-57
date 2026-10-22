import * as React from "react"
import { cn } from "@/lib/utils"

export function Card({ className, ...props }: React.ComponentProps<"div">) {
 return (
 <div
 data-slot="card"
 className={cn(
 "rounded-[var(--radius,0.625rem)] border border-[var(--border)] bg-[var(--card)] text-[var(--card-foreground,var(--foreground))] transition-colors",
 className
 )}
 {...props}
 />
 )
}

export function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
 return (
 <div
 data-slot="card-header"
 className={cn("flex flex-col space-y-1.5 p-4", className)}
 {...props}
 />
 )
}

export function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
 return (
 <div
 data-slot="card-title"
 className={cn("font-semibold leading-none tracking-tight text-sm text-[var(--foreground)]", className)}
 {...props}
 />
 )
}

export function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
 return (
 <div
 data-slot="card-description"
 className={cn("text-xs text-[var(--muted-foreground)] font-mono", className)}
 {...props}
 />
 )
}

export function CardContent({ className, ...props }: React.ComponentProps<"div">) {
 return (
 <div
 data-slot="card-content"
 className={cn("p-4 pt-0", className)}
 {...props}
 />
 )
}

export function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
 return (
 <div
 data-slot="card-footer"
 className={cn("flex items-center p-4 pt-0", className)}
 {...props}
 />
 )
}
