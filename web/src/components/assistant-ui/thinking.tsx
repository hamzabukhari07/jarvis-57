"use client";

import { useAuiState } from "@assistant-ui/react";
import { ThinkingTool } from "@/components/assistant-ui/elements/thinking-indicator";

export function AssistantThinking() {
  const isRunning = useAuiState((s) => s.message.status?.type === "running");
  const reasoningPart = useAuiState((s) =>
    s.message.parts.find((p) => p.type === "reasoning"),
  );

  return (
    <ThinkingTool
      state={isRunning ? "thinking" : "thought"}
      content={(reasoningPart as any)?.text}
      defaultOpen={isRunning}
      className="my-1.5"
    />
  );
}
