"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Paperclip, ArrowUp, Square } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface AIChatInputProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSubmit?: () => void;
  onStop?: () => void;
  onFileSelect?: (file: File) => void;
  isLoading?: boolean;
  minHeight?: number;
  maxHeight?: number;
}

export const AIChatInput = React.forwardRef<HTMLTextAreaElement, AIChatInputProps>(
  (
    {
      className,
      value,
      onChange,
      onSubmit,
      onStop,
      onFileSelect,
      isLoading = false,
      placeholder = "Ask or enter directive...",
      minHeight = 44,
      maxHeight = 200,
      disabled,
      ...props
    },
    ref
  ) => {
    const internalRef = React.useRef<HTMLTextAreaElement | null>(null);
    const fileInputRef = React.useRef<HTMLInputElement | null>(null);
    const [selectedFileName, setSelectedFileName] = React.useState<string | null>(null);

    // Merge refs
    React.useImperativeHandle(ref, () => internalRef.current as HTMLTextAreaElement);

    // Auto-resizing textarea with spring transition
    const adjustHeight = React.useCallback(() => {
      const textarea = internalRef.current;
      if (!textarea) return;
      textarea.style.height = "auto";
      const newHeight = Math.min(Math.max(textarea.scrollHeight, minHeight), maxHeight);
      textarea.style.height = `${newHeight}px`;
    }, [minHeight, maxHeight]);

    React.useEffect(() => {
      adjustHeight();
    }, [value, adjustHeight]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (isLoading && onStop) {
          onStop();
        } else if (!isLoading && onSubmit && !disabled) {
          onSubmit();
        }
      }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        const file = files[0];
        setSelectedFileName(file.name);
        if (onFileSelect) {
          onFileSelect(file);
        }
      }
    };

    const canSubmit = Boolean(value && value.trim().length > 0) || Boolean(selectedFileName);

    return (
      <div
        className={cn(
          "group relative flex flex-col w-full rounded-2xl border border-[var(--border)] bg-[var(--card)]/90 backdrop-blur-xl shadow-lg transition-[border-color,box-shadow] duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] focus-within:border-[var(--accent)]/80 focus-within:ring-2 focus-within:ring-[var(--accent)]/20 p-2.5",
          className
        )}
      >
        {/* Selected file preview pill if present */}
        {selectedFileName && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 mb-1.5 rounded-lg bg-[var(--secondary)]/60 text-xs text-[var(--foreground)] w-fit border border-[var(--border)] animate-in fade-in slide-in-from-bottom-1">
            <Paperclip className="w-3.5 h-3.5 text-[var(--accent)] shrink-0" />
            <span className="truncate max-w-[240px] font-mono">{selectedFileName}</span>
            <button
              type="button"
              onClick={() => {
                setSelectedFileName(null);
                if (fileInputRef.current) fileInputRef.current.value = "";
              }}
              className="ml-1 text-[var(--muted-foreground)] hover:text-[var(--foreground)] p-0.5 rounded cursor-pointer"
            >
              ×
            </button>
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={internalRef}
          value={value}
          onChange={(e) => {
            onChange?.(e);
            adjustHeight();
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          className="w-full resize-none bg-transparent px-2 py-1 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none disabled:opacity-50 overflow-y-auto leading-relaxed transition-[height] duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]"
          style={{ minHeight: `${minHeight}px`, maxHeight: `${maxHeight}px` }}
          {...props}
        />

        {/* Bottom Control Bar */}
        <div className="flex items-center justify-between pt-1.5 mt-1 border-t border-[var(--border)]/40 px-1">
          {/* File Upload Trigger */}
          <div className="flex items-center">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileChange}
              id="ai-chat-input-file"
            />
            <label
              htmlFor="ai-chat-input-file"
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg hover:bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors cursor-pointer text-xs"
              title="Upload file or context"
            >
              <Paperclip className="w-3.5 h-3.5" />
              <span className="font-medium text-xs">Upload file</span>
            </label>
          </div>

          {/* Dynamic Send / Stop Action */}
          <div className="flex items-center">
            {isLoading ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={onStop}
                className="h-7 w-7 p-0 rounded-xl border border-[var(--border)] hover:bg-[var(--secondary)] text-[var(--foreground)] shadow-xs transition-all shrink-0 cursor-pointer flex items-center justify-center animate-in zoom-in-95"
                title="Stop generation"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
              </Button>
            ) : (
              <Button
                type="button"
                size="sm"
                onClick={onSubmit}
                disabled={!canSubmit || disabled}
                className={cn(
                  "h-7 w-7 p-0 rounded-xl shadow-xs transition-all shrink-0 cursor-pointer flex items-center justify-center font-semibold",
                  canSubmit
                    ? "bg-primary text-primary-foreground hover:opacity-90 shadow-sm"
                    : "bg-[var(--secondary)] text-[var(--muted-foreground)] opacity-60 cursor-not-allowed"
                )}
                title="Send message"
              >
                <ArrowUp className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }
);

AIChatInput.displayName = "AIChatInput";
