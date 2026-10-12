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
  Sparkles,
  Loader2,
  Check,
  Copy,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Paperclip,
  Activity,
  BrainCircuit,
  CheckCircle2,
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
      <div className="my-2.5 rounded-xl border border-amber-500/30 bg-amber-500/5 p-3.5 text-xs text-[var(--foreground)] shadow-xs">
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
              className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-black font-semibold text-[11px] transition-all shadow-xs"
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

export const SystemStatusToolUI = makeAssistantToolUI({
  toolName: "system_status",
  render: ({ args: _args, result, status }) => {
    const isRunning = status.type === "running";
    return (
      <div className="my-2.5 w-full max-w-3xl">
        <ChainOfThought>
          <ChainOfThoughtStep defaultOpen={true}>
            <ChainOfThoughtTrigger
              leftIcon={<Activity className="size-4 text-[var(--accent)]" />}
            >
              <span>System Telemetry & Health Probe</span>
              <span className="ml-auto flex items-center gap-1 text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-[var(--secondary)] border border-[var(--border)] text-[var(--muted-foreground)]">
                {isRunning ? (
                  <>
                    <Loader2 className="w-2.5 h-2.5 animate-spin text-[var(--accent)]" />
                    <span>Polling Telemetry</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                    <span>Healthy</span>
                  </>
                )}
              </span>
            </ChainOfThoughtTrigger>
            <ChainOfThoughtContent>
              <ChainOfThoughtItem>
                {isRunning
                  ? `Gathering live system metrics: CPU, RAM, battery, active background processes...`
                  : `Telemetry collected successfully across core system monitors.`}
              </ChainOfThoughtItem>
              {Boolean(result) && (
                <ChainOfThoughtItem>
                  <CodeBlock className="mt-1.5">
                    <CodeBlockCode
                      code={typeof result === "object" ? JSON.stringify(result, null, 2) : String(result)}
                      language="json"
                    />
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

export const OpencodeAgentToolUI = makeAssistantToolUI({
  toolName: "opencode_agent",
  render: ({ args, result, status }) => {
    const isRunning = status.type === "running";
    const action = (args as any)?.action || "execute";
    const agent = (args as any)?.agent || "Jim";
    const target = (args as any)?.target || "active repository";
    const prompt = (args as any)?.prompt || (args as any)?.instruction || "";

    return (
      <div className="my-2.5 w-full max-w-3xl">
        <ChainOfThought>
          {/* Phase 1: Agent & Target Context Step */}
          <ChainOfThoughtStep defaultOpen={true}>
            <ChainOfThoughtTrigger
              leftIcon={<BrainCircuit className="size-4 text-[var(--accent)]" />}
            >
              <span>Autonomous Action: {action} ({agent})</span>
              <span className="ml-auto flex items-center gap-1 text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-[var(--secondary)] border border-[var(--border)] text-[var(--muted-foreground)]">
                {isRunning ? (
                  <>
                    <Loader2 className="w-2.5 h-2.5 animate-spin text-[var(--accent)]" />
                    <span>Executing</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                    <span>Completed</span>
                  </>
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
              leftIcon={<Code2 className="size-4 text-emerald-400" />}
            >
              <span>Command & AST Synthesis Output</span>
            </ChainOfThoughtTrigger>
            <ChainOfThoughtContent>
              {isRunning ? (
                <ChainOfThoughtItem className="flex items-center gap-2">
                  <Loader2 className="size-3 animate-spin text-[var(--accent)]" />
                  <span>Synthesizing code refactoring, AST invariants & safety matrices...</span>
                </ChainOfThoughtItem>
              ) : (
                <ChainOfThoughtItem>
                  <CodeBlock className="mt-1">
                    <CodeBlockCode
                      code={
                        result
                          ? (typeof result === "object" ? JSON.stringify(result, null, 2) : String(result))
                          : JSON.stringify(args || {}, null, 2)
                      }
                      language={typeof result === "object" ? "json" : "bash"}
                    />
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

/* ── 2. Official Assistant-UI Element Components ── */

export const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root
      data-slot="aui-user-message"
      className="w-full max-w-3xl py-2 mx-auto group"
    >
      <PKMessage className="justify-end">
        <PKMessageContent className="rounded-2xl rounded-tr-xs px-4 py-2.5 bg-primary text-primary-foreground font-normal text-xs leading-relaxed shadow-xs max-w-xl break-words">
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
          className="shrink-0 w-8 h-8 rounded-full border border-[var(--border)] bg-[#090d16] overflow-hidden shadow-xs flex items-center justify-center p-0.5"
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

          <ActionBarPrimitive.Reload asChild>
            <button
              type="button"
              className="p-1.5 hover:text-[var(--foreground)] hover:bg-[var(--secondary)] rounded-md text-[10px] transition-colors"
              title="Regenerate"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </ActionBarPrimitive.Reload>
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

export const Composer: FC<{ placeholder?: string; agentModel?: string; showUpload?: boolean }> = ({
  placeholder,
  showUpload = false,
}) => {
  const isRunning = useAuiState((s) => s.thread.isRunning);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  return (
    <div className="p-3 pb-4 shrink-0 bg-transparent relative z-10">
      <div className="max-w-3xl mx-auto w-full">
        {/* Hossain Jahed Signature AI Chat Input Container */}
        <ComposerPrimitive.Root
          data-slot="aui-composer-root"
          className="group relative flex flex-col w-full rounded-2xl border border-[var(--border)] bg-[var(--card)]/90 backdrop-blur-xl shadow-lg hover:border-[var(--border)]/80 focus-within:border-[var(--accent)]/80 focus-within:ring-2 focus-within:ring-[var(--accent)]/20 p-2.5 transition-[border-color,box-shadow] duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]"
        >
          {/* File Attachment Pill Badge */}
          {showUpload && selectedFile && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 mb-1.5 rounded-lg bg-[var(--secondary)]/70 text-xs text-[var(--foreground)] w-fit border border-[var(--border)] animate-in fade-in slide-in-from-bottom-1">
              <Paperclip className="w-3.5 h-3.5 text-[var(--accent)] shrink-0" />
              <span className="truncate max-w-[240px] font-mono text-[11px]">{selectedFile}</span>
              <button
                type="button"
                onClick={() => setSelectedFile(null)}
                className="ml-1 text-[var(--muted-foreground)] hover:text-[var(--foreground)] p-0.5 rounded cursor-pointer leading-none"
              >
                ×
              </button>
            </div>
          )}

          {/* Dynamic Auto-resizing Input Field */}
          <div className="w-full">
            <ComposerPrimitive.Input
              data-slot="aui-composer-input"
              placeholder={placeholder || "Ask or enter directive..."}
              className="w-full bg-transparent border-0 px-2 py-1 text-xs sm:text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none resize-none min-h-[42px] max-h-[180px] leading-relaxed transition-[height] duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]"
              rows={1}
              autoFocus={false}
            />
          </div>

          {/* Bottom Control Bar */}
          <div className={cn("flex items-center pt-1.5 mt-1 border-t border-[var(--border)]/40 px-1", showUpload ? "justify-between" : "justify-end")}>
            {/* Left Action Toolbar: File Upload (Only when showUpload is explicitly enabled) */}
            {showUpload && (
              <div className="flex items-center">
                <label
                  className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg hover:bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors cursor-pointer text-xs"
                  title="Attach file or context"
                >
                  <Paperclip className="w-3.5 h-3.5" />
                  <span className="font-normal text-xs">Upload file</span>
                  <input
                    type="file"
                    className="hidden"
                    onChange={(e) => {
                      const files = e.target.files;
                      if (files && files.length > 0) {
                        setSelectedFile(files[0].name);
                      }
                    }}
                  />
                </label>
              </div>
            )}

            {/* Right Action: Dynamic Send / Stop Toggle Button with Jahed pill styling */}
            <div className="flex items-center">
              {isRunning ? (
                <ComposerPrimitive.Cancel asChild>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 w-7 p-0 rounded-xl border border-[var(--border)] hover:bg-[var(--secondary)] text-[var(--foreground)] shadow-xs transition-all shrink-0 cursor-pointer flex items-center justify-center animate-in zoom-in-95"
                    title="Stop generation"
                  >
                    <Square className="w-3.5 h-3.5 fill-current" />
                  </Button>
                </ComposerPrimitive.Cancel>
              ) : (
                <ComposerPrimitive.Send asChild>
                  <Button
                    size="sm"
                    className="h-7 w-7 p-0 bg-primary hover:opacity-90 text-primary-foreground font-semibold rounded-xl shadow-xs transition-all shrink-0 cursor-pointer flex items-center justify-center"
                    title="Send message"
                  >
                    <ArrowUp className="w-3.5 h-3.5" />
                  </Button>
                </ComposerPrimitive.Send>
              )}
            </div>
          </div>
        </ComposerPrimitive.Root>
      </div>
    </div>
  );
};

/* ── 3. Official Thread Root ── */
export interface AssistantUIThreadProps {
  className?: string;
  agentName?: string;
  avatarName?: string;
  placeholder?: string;
  emptyTitle?: string;
  emptySubtitle?: string;
  showUpload?: boolean;
}

export const AssistantUIThread: FC<AssistantUIThreadProps> = ({
  className,
  agentName,
  avatarName,
  placeholder,
  emptyTitle,
  emptySubtitle,
  showUpload = false,
}) => {
  const isZezo =
    (!agentName || ["zezo", "jarvis", "ai"].includes(agentName.toLowerCase())) &&
    (!avatarName || ["zezo", "jarvis", "ai"].includes(avatarName.toLowerCase()));

  return (
    <ThreadPrimitive.Root
      data-slot="aui-thread-root"
      className={cn("flex flex-col h-full w-full min-h-0 bg-transparent", className)}
    >
      {/* Official Tool Calling UIs */}
      <WebSearchToolUI />
      <ActionApprovalToolUI />
      <SystemStatusToolUI />
      <OpencodeAgentToolUI />

      {/* Official Viewport Element */}
      <ThreadPrimitive.Viewport
        data-slot="aui-thread-viewport"
        className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0"
      >
        <div className="max-w-3xl mx-auto w-full space-y-4">
          <ThreadPrimitive.Empty>
            <div className="flex flex-col items-center justify-center h-full text-center text-[var(--muted-foreground)] py-16">
              <div className="w-12 h-12 rounded-2xl bg-[#090d16] border border-[var(--border)] flex items-center justify-center mb-3 shadow-sm overflow-hidden p-1">
                {isZezo ? (
                  <img
                    src="/zezo-avatar.png"
                    alt="ZEZO"
                    className="w-full h-full object-contain transform scale-105"
                  />
                ) : avatarName || agentName ? (
                  <Blobatar name={(avatarName || agentName) ?? 'Jarvis'} size={48} animate="always" className="w-full h-full object-contain" />
                ) : (
                  <Sparkles className="w-5 h-5 text-[var(--accent)]" />
                )}
              </div>
              <div className="text-sm font-semibold text-[var(--foreground)]">
                {emptyTitle || (agentName ? `Start Conversation with ${agentName}` : "Start Conversation with ZEZO")}
              </div>
              <div className="text-xs font-mono text-[var(--muted-foreground)] mt-1.5 max-w-[280px] leading-relaxed">
                {emptySubtitle || (agentName ? `Autonomous agent session with ${agentName}. Multi-agent tools and reasoning active.` : "Forma OS Autonomous assistant thread. Real-time reasoning and multi-agent tools active.")}
              </div>
            </div>
          </ThreadPrimitive.Empty>

          <ThreadPrimitive.Messages
            components={{
              UserMessage: UserMessage,
              AssistantMessage: (props: any) => (
                <AssistantMessage
                  {...props}
                  agentName={agentName || "Jarvis"}
                  avatarName={avatarName || agentName || "Jarvis"}
                />
              ),
            }}
          />
        </div>
      </ThreadPrimitive.Viewport>

      {/* Official Floating Composer Element without Upload File by default */}
      <Composer placeholder={placeholder} agentModel={agentName ? `${agentName} Agent` : undefined} showUpload={showUpload} />
    </ThreadPrimitive.Root>
  );
};
