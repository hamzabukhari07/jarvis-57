import * as DialogPrimitive from "@radix-ui/react-dialog"
import { AlertTriangle, Trash2, X, Loader2 } from "lucide-react"
import { Button } from "../ui/button"
import { Badge } from "./badge"
import { Callout } from "./callout"
import { Kbd } from "./kbd"
import { cn } from "@/lib/utils"

export interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  warningText?: string
  confirmText?: string
  cancelText?: string
  variant?: "destructive" | "warning" | "default"
  isLoading?: boolean
  onConfirm: () => void | Promise<void>
  onCancel?: () => void
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  warningText,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "destructive",
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const handleCancel = () => {
    if (isLoading) return
    onCancel?.()
    onOpenChange(false)
  }

  const handleConfirm = async () => {
    if (isLoading) return
    await onConfirm()
  }

  const isDestructive = variant === "destructive"

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        {/* Overlay without blur to prevent QtWebEngine compositor flicker */}
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/80 transition-opacity duration-150 data-[state=open]:opacity-100 data-[state=closed]:opacity-0" />
        <DialogPrimitive.Content
          className={cn(
            "fixed left-[50%] top-[50%] z-50 grid w-full max-w-md translate-x-[-50%] translate-y-[-50%] gap-4",
            "border border-[var(--border)] bg-[#0d0d0d] p-5 shadow-2xl rounded-2xl",
            "transition-opacity duration-150 data-[state=open]:opacity-100 data-[state=closed]:opacity-0",
            "focus:outline-hidden"
          )}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-3 border-b border-[var(--border)]/70 pb-3.5">
            <div className="flex items-center gap-2.5">
              <div
                className={cn(
                  "p-2 rounded-xl flex items-center justify-center shrink-0 border",
                  isDestructive
                    ? "bg-red-500/10 border-red-500/30 text-red-400"
                    : "bg-amber-500/10 border-amber-500/30 text-amber-400"
                )}
              >
                {isDestructive ? (
                  <Trash2 className="w-4 h-4" />
                ) : (
                  <AlertTriangle className="w-4 h-4" />
                )}
              </div>
              <div className="flex flex-col gap-0.5">
                <div className="flex items-center gap-2">
                  <DialogPrimitive.Title className="text-sm font-semibold tracking-tight text-[var(--foreground)]">
                    {title}
                  </DialogPrimitive.Title>
                  <Badge
                    variant={isDestructive ? "destructive" : "warning"}
                    size="xs"
                    className="font-mono"
                  >
                    {isDestructive ? "IRREVERSIBLE" : "ACTION"}
                  </Badge>
                </div>
                {description && (
                  <DialogPrimitive.Description className="text-xs text-[var(--muted-foreground)] leading-relaxed">
                    {description}
                  </DialogPrimitive.Description>
                )}
              </div>
            </div>

            <button
              type="button"
              onClick={handleCancel}
              disabled={isLoading}
              className="p-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--input)] transition-colors disabled:opacity-50"
            >
              <X className="w-4 h-4" />
              <span className="sr-only">Close</span>
            </button>
          </div>

          {/* Warning Callout */}
          {warningText && (
            <Callout
              variant={isDestructive ? "destructive" : "warning"}
              className="text-xs leading-relaxed"
            >
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              <div>{warningText}</div>
            </Callout>
          )}

          {/* Actions / Footer */}
          <div className="flex items-center justify-end gap-2.5 pt-1">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={isLoading}
              className="gap-1.5 text-xs font-mono"
            >
              {cancelText}
              <Kbd className="text-[9px] px-1 py-0 h-4">Esc</Kbd>
            </Button>
            <Button
              type="button"
              variant={isDestructive ? "destructive" : "default"}
              size="sm"
              onClick={handleConfirm}
              disabled={isLoading}
              className={cn(
                "gap-1.5 text-xs font-mono font-semibold",
                isDestructive && "bg-red-600 hover:bg-red-700 text-white shadow-sm"
              )}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Wiping...
                </>
              ) : (
                <>
                  {isDestructive && <Trash2 className="w-3.5 h-3.5" />}
                  {confirmText}
                </>
              )}
            </Button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
