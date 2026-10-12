import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

/**
 * ReUI Chat Message Bubble & Container Primitive
 * Standards: shadcn / ReUI AI Chat Block
 */
const chatMessageVariants = cva(
  "flex w-full gap-2.5",
  {
    variants: {
      role: {
        user: "justify-end",
        assistant: "justify-start",
        system: "justify-center",
      },
    },
    defaultVariants: {
      role: "assistant",
    },
  }
)

export interface ChatMessageProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof chatMessageVariants> {
  role?: "user" | "assistant" | "system"
}

export function ChatMessage({
  className,
  role = "assistant",
  children,
  ...props
}: ChatMessageProps) {
  return (
    <div className={cn(chatMessageVariants({ role }), className)} {...props}>
      {children}
    </div>
  )
}

const chatBubbleVariants = cva(
  "rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed max-w-[85%] break-words shadow-sm transition-colors",
  {
    variants: {
      variant: {
        user: "bg-[#1e1d1c] border border-white/10 text-[#e4e0d8] rounded-tr-xs font-normal selection:bg-white/20",
        assistant: "bg-[#121110] border border-white/10 text-[#e4e0d8] rounded-tl-xs",
        system: "bg-[#121110]/80 border border-white/10 text-[#9a948a] text-[11px] font-mono",
      },
    },
    defaultVariants: {
      variant: "assistant",
    },
  }
)

export interface ChatBubbleProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof chatBubbleVariants> {}

export function ChatBubble({
  className,
  variant,
  children,
  ...props
}: ChatBubbleProps) {
  return (
    <div className={cn(chatBubbleVariants({ variant, className }))} {...props}>
      {children}
    </div>
  )
}

export function ChatAvatar({
  className,
  isUser,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { isUser?: boolean }) {
  return (
    <div
      className={cn(
        "w-6 h-6 rounded-lg shrink-0 flex items-center justify-center text-[10px] font-semibold mt-0.5 select-none",
        isUser
          ? "bg-[#1a1918] text-[#e4e0d8] border border-white/10"
          : "bg-white/10 text-[#e4e0d8] border border-white/15 shadow-sm",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

