"use client";

import { CheckCircle2, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TurnProcessPillProps {
  elapsedSeconds?: number;
  toolCallCount?: number;
  sourcesCount?: number;
  isComplete?: boolean;
  isOpen?: boolean;
  onToggle?: () => void;
  className?: string;
}

export const TurnProcessPill: React.FC<TurnProcessPillProps> = ({
  elapsedSeconds = 2.4,
  toolCallCount = 0,
  sourcesCount = 0,
  isComplete = true,
  isOpen = false,
  onToggle,
  className,
}) => {
  if (!isComplete) return null;

  // Build compact execution summary
  const summaryParts: string[] = [];
  if (sourcesCount > 0) summaryParts.push(`${sourcesCount} source${sourcesCount > 1 ? "s" : ""}`);
  if (toolCallCount > 0) summaryParts.push(`${toolCallCount} tool${toolCallCount > 1 ? "s" : ""}`);

  const detailsText = summaryParts.length > 0 ? ` (${summaryParts.join(", ")})` : "";

  return (
    <div className={cn("inline-flex items-center my-1 select-none", className)}>
      <button
        type="button"
        onClick={onToggle}
        className="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--secondary)]/70 hover:bg-[var(--secondary)] border border-[var(--border)] text-[11px] font-mono text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-all cursor-pointer shadow-2xs"
        title="Toggle execution steps"
      >
        <span className="flex items-center gap-1 text-emerald-400">
          <CheckCircle2 className="w-3 h-3" />
        </span>

        <span className="font-sans font-medium text-[var(--foreground)]">
          Worked for {elapsedSeconds.toFixed(1)}s
        </span>

        {detailsText && (
          <span className="text-[10px] text-[var(--muted-foreground)]">
            {detailsText}
          </span>
        )}

        <ChevronDown
          className={cn(
            "w-3 h-3 transition-transform duration-150 ease-out opacity-60 group-hover:opacity-100",
            isOpen ? "rotate-180" : "rotate-0"
          )}
        />
      </button>
    </div>
  );
};
