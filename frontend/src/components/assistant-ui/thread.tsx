import { useState, type FC } from "react";
import {
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  ActionBarPrimitive,
  BranchPickerPrimitive,
  makeAssistantToolUI,
  useAuiState,
  AuiIf,
} from "@assistant-ui/react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import { ThinkingTool } from "@/components/assistant-ui/elements/thinking-indicator";
import { WebSearchTool } from "@/components/assistant-ui/elements/web-search-tool";
import { TurnProcessPill } from "@/components/assistant-ui/elements/turn-process-pill";
import {
  Message as PKMessage,
  MessageAvatar as PKMessageAvatar,
  MessageContent as PKMessageContent,
} from "@/components/prompt-kit/message";
import {
  ChainOfThought,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
  ChainOfThoughtContent,
  ChainOfThoughtItem,
} from "@/components/prompt-kit/chain-of-thought";
import { CodeBlock, CodeBlockCode } from "@/components/prompt-kit/code-block";
import {
  ArrowUp,
  Square,
  Loader2,
  Check,
  Copy,
  ChevronLeft,
  ChevronRight,
  BrainCircuit,
  CheckCircle2,
  XCircle,
  Code2,
} from "lucide-react";
import { Blobatar } from "blobatar/react";
import { Button } from "../ui/button";
import { cn } from "@/lib/utils";

/* ── 1. Official Assistant-UI Tool Calling Elements ── */
export const WebSearchToolUI = makeAssistantToolUI({
  toolName: "web_search",
  render: ({ args, result, status }) => {
    const isRunning = status.type === "running";
    const sources = (result as any)?.sources || [];
    const query = (args as any)?.query || (args as any)?.target || "";

    return (
      <WebSearchTool
        query={query}
        sources={sources}
        isSearching={isRunning}
        defaultOpen={true}
      />
    );
  },
});

export const ActionApprovalToolUI = makeAssistantToolUI({
  toolName: "destructive_action_gate",
  render: ({ args, result }) => {
    const isApproved = (result as any)?.approved === true;
    return (
      <div className="my-2.5 rounded-xl border border-amber-500/30 bg-amber-500/5 p-3.5 text-xs text-[var(--foreground)] ">
        <div className="flex items-center gap-2 mb-2 text-amber-400 font-semibold text-xs">
          <span>⚠️</span>
          <span>Autonomous L1 Safety Gate — Approval Required</span>
        </div>
        <p className="text-[11px] text-[var(--muted-foreground)] mb-3 leading-relaxed">
          The agent requested to run: <code className="px-1.5 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] font-mono text-amber-300">{(args as any)?.command || 'system action'}</code>. Confirm whether this execution is authorized.
        </p>
        {isApproved ? (
          <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-mono">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Authorized by lead engineer. Action dispatched.</span>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-black font-semibold text-[11px] transition-all "
            >
              ✓ Authorize Execution
            </button>
            <button
              type="button"
              className="px-3 py-1.5 rounded-lg bg-[var(--secondary)] hover:bg-[var(--card)] text-[var(--muted-foreground)] text-[11px] border border-[var(--border)] transition-all"
            >
              ✕ Deny
            </button>
          </div>
        )}
      </div>
    );
  },
});

export const FleetTaskToolUI = makeAssistantToolUI({
  toolName: "fleet_task",
  render: ({ args, result, status }) => {
    const isRunning = status.type === "running";
    const isFailed =
      (result as any)?.status === "failed" ||
      (result as any)?.success === false ||
      Boolean((result as any)?.error);
    const agent = (args as any)?.agent || "Agent";
    const target = (args as any)?.target || (args as any)?.task || "Task";
    const prompt = (args as any)?.prompt || "";
    const output = (result as any)?.output || (result as any)?.result || "";
    const errorMsg =
      typeof (result as any)?.error === "object"
        ? JSON.stringify((result as any)?.error, null, 2)
        : (result as any)?.error || output || "Task execution failed.";

    return (
      <div className="my-2 rounded-xl border border-[var(--border)] bg-[var(--card)] p-3 text-xs text-[var(--foreground)] shadow-xs">
        <ChainOfThought>
          <ChainOfThoughtStep defaultOpen={true}>
            <ChainOfThoughtTrigger
              leftIcon={<BrainCircuit className="size-4 text-[var(--accent)] animate-pulse" />}
            >
              <span className="font-semibold text-xs">
                Fleet Agent Dispatch: <strong>{agent}</strong>
              </span>
              <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--secondary)] text-[var(--muted-foreground)]">
                {isRunning ? (
                  <span className="flex items-center gap-1 text-[var(--accent)]">
                    <Loader2 className="size-2.5 animate-spin" />
                    Executing...
                  </span>
                ) : isFailed ? (
                  <span className="flex items-center gap-1 text-red-400 font-semibold">
                    <XCircle className="size-2.5" />
                    Failed
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-emerald-400">
                    <CheckCircle2 className="size-2.5" />
                    Completed
                  </span>
                )}
              </span>
            </ChainOfThoughtTrigger>
            <ChainOfThoughtContent>
              <ChainOfThoughtItem>
                Agent <strong>{agent}</strong> dispatched on target <code>{target}</code>
                {prompt && <div className="mt-1 text-[var(--muted-foreground)] italic">"{prompt}"</div>}
              </ChainOfThoughtItem>
            </ChainOfThoughtContent>
          </ChainOfThoughtStep>

          {/* Phase 2: Execution Result & Code Trace */}
          <ChainOfThoughtStep defaultOpen={true}>
            <ChainOfThoughtTrigger
              leftIcon={
                isFailed ? (
                  <XCircle className="size-4 text-red-400" />
                ) : (
                  <Code2 className="size-4 text-emerald-400" />
                )
              }
            >
              <span className={isFailed ? "text-red-400 font-medium" : ""}>
                {isFailed ? "Execution Failure Trace" : "Command & AST Synthesis Output"}
              </span>
            </ChainOfThoughtTrigger>
            <ChainOfThoughtContent>
              {isRunning ? (
                <ChainOfThoughtItem className="flex items-center gap-2">
                  <Loader2 className="size-3 animate-spin text-[var(--accent)]" />
                  <span>Synthesizing code refactoring, AST invariants & safety matrices...</span>
                </ChainOfThoughtItem>
              ) : isFailed ? (
                <ChainOfThoughtItem>
                  <div className="rounded-md border border-red-500/30 bg-red-950/20 p-2 text-red-300 font-mono text-[11px] whitespace-pre-wrap">
                    {errorMsg}
                  </div>
                </ChainOfThoughtItem>
              ) : (
                <ChainOfThoughtItem>
                  <CodeBlock className="my-1 text-[11px]">
                    <CodeBlockCode code={output || "Task execution finished successfully."} language="typescript" />
                  </CodeBlock>
                </ChainOfThoughtItem>
              )}
            </ChainOfThoughtContent>
          </ChainOfThoughtStep>
        </ChainOfThought>
      </div>
    );
  },
});


/* ── 2. User Message Component ── */
export const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root
      data-slot="aui-user-message"
      className="w-full max-w-3xl py-2 mx-auto group"
    >
      <PKMessage className="justify-end">
        <PKMessageContent className="rounded-2xl rounded-tr-xs px-3.5 py-2.5 bg-primary text-primary-foreground font-normal text-xs leading-relaxed max-w-xl break-words shadow-xs">
          <MessagePrimitive.Parts />
        </PKMessageContent>
      </PKMessage>

      <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity pr-1">
        <BranchPicker />
        <ActionBarPrimitive.Root hideWhenRunning className="flex items-center gap-0.5">
          <ActionBarPrimitive.Copy asChild>
            <button
              type="button"
              className="p-1 text-[var(--muted-foreground)] hover:text-[var(--foreground)] rounded text-[10px] transition-colors"
              title="Copy"
            >
              <Copy className="w-3 h-3" />
            </button>
          </ActionBarPrimitive.Copy>
        </ActionBarPrimitive.Root>
      </div>
    </MessagePrimitive.Root>
  );
};

const ReasoningPart: FC<{ text?: string }> = ({ text }) => {
  const isRunning = useAuiState((s) => s.message.status?.type === "running");
  const [internalOpen, setInternalOpen] = useState<boolean | null>(null);

  // If user explicitly clicked toggle, honor it; otherwise expand while running
  const isOpen = internalOpen ?? isRunning;

  return (
    <ThinkingTool
      state={isRunning ? "thinking" : "thought"}
      content={text}
      expanded={isOpen}
      onToggleExpand={() => setInternalOpen(!isOpen)}
      className="my-1.5"
    />
  );
};

const EmptyPart: FC = () => null;
const TextPart: FC = () => <MarkdownTextPrimitive />;

export const AssistantMessage: FC<{ agentName?: string; avatarName?: string }> = ({
  agentName,
  avatarName,
}) => {
  const isRunning = useAuiState((s) => s.message.status?.type === "running");
  const hasContent = useAuiState((s) => {
    const parts = s.message.parts;
    if (!parts || parts.length === 0) return false;
    return parts.some((p: any) =>
      (p.type === "text" && Boolean(p.text && p.text.trim().length > 0)) ||
      (p.type === "reasoning" && Boolean(p.text && p.text.trim().length > 0))
    );
  });
  const toolCallCount = useAuiState((s) => s.message.parts.reduce((count, p) => p.type === "tool-call" ? count + 1 : count, 0));
  const hasWebSearch = useAuiState((s) => s.message.parts.some((p) => p.type === "tool-call" && (p as any).toolName === "web_search"));
  const [showProcessSteps, setShowProcessSteps] = useState(true);

  const hasSteps = toolCallCount > 0;
  const displayName = avatarName || agentName || "ZEZO";
  const isZezo =
    (!agentName || ["zezo", "jarvis", "ai"].includes(agentName.toLowerCase())) &&
    (!avatarName || ["zezo", "jarvis", "ai"].includes(avatarName.toLowerCase()));

  return (
    <MessagePrimitive.Root
      data-slot="aui-assistant-message"
      className="w-full max-w-3xl py-2 mx-auto group"
    >
      <PKMessage className="justify-start items-start">
        {/* Prompt-Kit MessageAvatar with fallback and Zezo / Agent Avatar */}
        <PKMessageAvatar
          fallback={displayName.slice(0, 2).toUpperCase()}
          alt={displayName}
          className="shrink-0 w-8 h-8 rounded-full border border-[var(--border)] bg-card overflow-hidden flex items-center justify-center p-0.5"
        >
          {isZezo ? (
            <img
              src="/zezo-avatar.png"
              alt="ZEZO"
              className="w-full h-full object-contain transform scale-105"
            />
          ) : (
            <Blobatar name={displayName} size={28} animate="hover" className="w-full h-full object-contain" />
          )}
        </PKMessageAvatar>

        {/* Prompt-Kit MessageContent with markdown styling */}
        <PKMessageContent markdown className="flex-1 min-w-0 bg-transparent p-0 text-xs text-[var(--foreground)] leading-relaxed space-y-2">
          {/* DeepSeek Turn Process Summary Pill */}
          {!isRunning && hasSteps && (
            <TurnProcessPill
              elapsedSeconds={1.8}
              toolCallCount={toolCallCount}
              sourcesCount={hasWebSearch ? 3 : 0}
              isComplete={!isRunning}
              isOpen={showProcessSteps}
              onToggle={() => setShowProcessSteps((v) => !v)}
            />
          )}

          {/* Clean animated thinking indicator while generating */}
          {isRunning && !hasContent && (
            <div className="flex items-center py-1 text-xs text-[var(--muted-foreground)]">
              <ThinkingTool state="thinking" />
            </div>
          )}

          <div className={cn(showProcessSteps || isRunning ? "space-y-2" : "space-y-0")}>
            <MessagePrimitive.Parts
              components={{
                Text: TextPart,
                Reasoning: showProcessSteps || isRunning ? ReasoningPart : EmptyPart,
              }}
            />
          </div>
        </PKMessageContent>
      </PKMessage>

      {/* Official Assistant Action Bar & Branch Picker Element */}
      <div className="flex items-center gap-2 mt-1 pl-11 text-[var(--muted-foreground)]">
        <BranchPicker />
        <ActionBarPrimitive.Root
          hideWhenRunning
          className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100"
        >
          <ActionBarPrimitive.Copy asChild>
            <button
              type="button"
              className="p-1.5 hover:text-[var(--foreground)] hover:bg-[var(--secondary)] rounded-md text-[10px] transition-colors"
              title="Copy response"
            >
              <AuiIf condition={(s) => s.message.isCopied}>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              </AuiIf>
              <AuiIf condition={(s) => !s.message.isCopied}>
                <Copy className="w-3.5 h-3.5" />
              </AuiIf>
            </button>
          </ActionBarPrimitive.Copy>
        </ActionBarPrimitive.Root>
      </div>
    </MessagePrimitive.Root>
  );
};

export const BranchPicker: FC = () => {
  return (
    <BranchPickerPrimitive.Root
      hideWhenSingleBranch
      className="inline-flex items-center text-[10px] font-mono text-[var(--muted-foreground)] select-none mr-1"
    >
      <BranchPickerPrimitive.Previous asChild>
        <button type="button" className="p-0.5 hover:text-[var(--foreground)]">
          <ChevronLeft className="w-3 h-3" />
        </button>
      </BranchPickerPrimitive.Previous>
      <span className="px-1">
        <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      </span>
      <BranchPickerPrimitive.Next asChild>
        <button type="button" className="p-0.5 hover:text-[var(--foreground)]">
          <ChevronRight className="w-3 h-3" />
        </button>
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  );
};

/* ── 3. ZezoChatThread Main Export Component ── */
export const ZezoChatThread: FC<{
  placeholder?: string;
  agentName?: string;
  avatarName?: string;
  className?: string;
  emptyTitle?: string;
  emptySubtitle?: string;
  showUpload?: boolean;
}> = ({
  placeholder,
  agentName,
  avatarName,
  className,
}) => {
  return (
    <ThreadPrimitive.Root className={cn("flex flex-col h-full w-full bg-transparent overflow-hidden", className)}>
      <ThreadPrimitive.Viewport
        data-slot="aui-thread-viewport"
        className="flex-1 overflow-y-auto px-4 py-3 space-y-4 focus:outline-none scroll-smooth"
      >
        <ThreadPrimitive.Messages
          components={{
            UserMessage: UserMessage,
            AssistantMessage: () => <AssistantMessage agentName={agentName} avatarName={avatarName} />,
          }}
        />
      </ThreadPrimitive.Viewport>

      <div className="p-3 pb-3 shrink-0 bg-transparent relative z-10">
        <div className="max-w-3xl mx-auto w-full">
          <ComposerPrimitive.Root
            data-slot="aui-composer-root"
            className="group relative flex items-center w-full rounded-full border border-[var(--border)] bg-[var(--card)]/90 backdrop-blur-xl hover:border-[var(--border)]/80 focus-within:border-[var(--accent)]/80 focus-within:ring-2 focus-within:ring-[var(--accent)]/20 pl-3.5 pr-1.5 py-1 transition-[border-color,box-shadow] duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]"
          >
            <ComposerPrimitive.Input
              data-slot="aui-composer-input"
              placeholder={placeholder || "Ask or enter directive..."}
              className="flex-1 bg-transparent border-0 px-1 py-1 text-xs text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none resize-none leading-normal min-h-[28px] max-h-[80px]"
              rows={1}
              autoFocus={false}
            />

            <div className="flex items-center shrink-0 ml-1.5">
              <AuiIf condition={(s) => s.thread.isRunning}>
                <ComposerPrimitive.Cancel asChild>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 w-7 p-0 rounded-full border border-[var(--border)] hover:bg-[var(--secondary)] text-[var(--foreground)] transition-all shrink-0 cursor-pointer flex items-center justify-center animate-in zoom-in-95"
                    title="Stop speaking"
                  >
                    <Square className="w-3.5 h-3.5 fill-current" />
                  </Button>
                </ComposerPrimitive.Cancel>
              </AuiIf>
              <AuiIf condition={(s) => !s.thread.isRunning}>
                <ComposerPrimitive.Send asChild>
                  <Button
                    size="sm"
                    className="h-7 w-7 p-0 rounded-full bg-primary hover:bg-primary/90 text-primary-foreground transition-all shrink-0 cursor-pointer flex items-center justify-center shadow-xs"
                    title="Send directive"
                  >
                    <ArrowUp className="w-3.5 h-3.5" />
                  </Button>
                </ComposerPrimitive.Send>
              </AuiIf>
            </div>
          </ComposerPrimitive.Root>
        </div>
      </div>
    </ThreadPrimitive.Root>
  );
};

export const AssistantUIThread = ZezoChatThread;

