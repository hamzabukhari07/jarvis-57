import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

/**
 * Forma OS Button primitive
 */
const buttonVariants = cva(
  "inline-flex items-center justify-center font-medium rounded-[var(--radius,0.5rem)] transition-all focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-[var(--ring)] disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer",
  {
    variants: {
      variant: {
        default: "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm hover:opacity-90 font-semibold",
        destructive: "bg-[var(--destructive,#ef4444)] text-[var(--destructive-foreground,#ffffff)] hover:opacity-90 shadow-sm",
        outline: "border border-[var(--border)] bg-[var(--input)]/80 text-[var(--foreground)] hover:bg-[var(--primary)]/15 hover:border-[var(--primary)]/50 hover:text-[var(--foreground)] shadow-2xs",
        secondary: "bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:opacity-85 shadow-2xs",
        ghost: "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--muted)]/70",
        link: "text-[var(--primary)] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2 text-xs",
        sm: "h-7 px-2.5 text-[11px]",
        lg: "h-10 px-5 text-sm",
        icon: "h-8 w-8 text-xs",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"
