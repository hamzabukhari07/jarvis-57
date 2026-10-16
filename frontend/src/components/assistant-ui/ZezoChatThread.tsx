import { type FC } from "react";
import {
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  ActionBarPrimitive,
  useAuiState,
  AuiIf,
} from "@assistant-ui/react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import {
  Message as PKMessage,
  MessageAvatar as PKMessageAvatar,
  MessageContent as PKMessageContent,
} from "@/components/prompt-kit/message";
import {
  ArrowUp,
  Square,
  Check,
  Copy,
  RefreshCw,
} from "lucide-react";
import { Button } from "../ui/button";
import { cn } from "@/lib/utils";

function formatMessageTime(date?: Date | string | number): string {
  if (!date) return "";
  const d = typeof date === "string" || typeof date === "number" ? new Date(date) : date;
  if (!(d instanceof Date) || isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
}

/* ── 1. User Message (Spoken / Typed Directive) ── */
export const UserMessage: FC = () => {
  const createdAt = useAuiState((s) => s.message.createdAt);
  const timeStr = formatMessageTime(createdAt);

  return (
    <MessagePrimitive.Root
      data-slot="aui-user-message"
      className="w-full max-w-3xl py-1.5 mx-auto group"
    >
      <PKMessage className="justify-end">
        <PKMessageContent className="rounded-2xl rounded-tr-xs px-3.5 py-2 bg-primary text-primary-foreground font-normal text-xs leading-relaxed shadow-xs max-w-xl break-words">
          <MessagePrimitive.Parts />
        </PKMessageContent>
      </PKMessage>

      <div className="flex items-center justify-end gap-1.5 pr-1 mt-1">
        {timeStr && (
          <span className="text-[10px] text-[var(--muted-foreground)] font-mono select-none">
            {timeStr}
          </span>
        )}
        <ActionBarPrimitive.Root hideWhenRunning className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <ActionBarPrimitive.Copy asChild>
            <button
              type="button"
              className="p-1 text-[var(--muted-foreground)] hover:text-[var(--foreground)] rounded text-[10px] transition-colors cursor-pointer"
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

const TextPart: FC = () => <MarkdownTextPrimitive />;

/* ── 2. Assistant Message (Zezo Live Voice Speech & Dialogue) ── */
export const AssistantMessage: FC = () => {
  const isRunning = useAuiState((s) => s.message.status?.type === "running");
  const createdAt = useAuiState((s) => s.message.createdAt);
  const timeStr = formatMessageTime(createdAt);

  return (
    <MessagePrimitive.Root
      data-slot="aui-assistant-message"
      className="w-full max-w-3xl py-1.5 mx-auto group"
    >
      <PKMessage className="justify-start items-start gap-2.5">
        {/* Official Zezo Cosmic Avatar Badge */}
        <PKMessageAvatar
          fallback="ZZ"
          alt="ZEZO"
          className="shrink-0 w-8 h-8 rounded-full border border-[var(--border)] bg-[#090d16] overflow-hidden shadow-xs flex items-center justify-center p-0.5"
        >
          <img
            src="/zezo-avatar.png"
            alt="ZEZO"
            className="w-full h-full object-contain transform scale-105"
          />
        </PKMessageAvatar>

        {/* Live Speech Dialogue & Real-time Transcription Stream */}
        <PKMessageContent markdown className="flex-1 min-w-0 bg-transparent p-0 text-xs text-[var(--foreground)] leading-relaxed">
          <div className="space-y-1">
            <MessagePrimitive.Parts
              components={{
                Text: TextPart,
              }}
            />

            {/* Realtime Speaking Waveform Pulse during active speech generation */}
            {isRunning && (
              <span className="inline-flex items-center gap-1.5 text-[10px] text-[var(--accent)] font-mono mt-1">
                <span className="flex items-center gap-0.5 h-2.5">
                  <span className="w-0.5 h-2 bg-[var(--accent)] animate-pulse rounded-full" />
                  <span className="w-0.5 h-3 bg-[var(--accent)] animate-pulse delay-75 rounded-full" />
                  <span className="w-0.5 h-1.5 bg-[var(--accent)] animate-pulse delay-150 rounded-full" />
                </span>
                <span>transcribing speech...</span>
              </span>
            )}
          </div>
        </PKMessageContent>
      </PKMessage>

      {/* Assistant Action Bar & Timestamp */}
      <div className="flex items-center gap-2 mt-1 pl-10.5">
        {timeStr && (
          <span className="text-[10px] text-[var(--muted-foreground)] font-mono select-none">
            {timeStr}
          </span>
        )}
        <ActionBarPrimitive.Root
          hideWhenRunning
          className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <ActionBarPrimitive.Copy asChild>
            <button
              type="button"
              className="p-1 hover:text-[var(--foreground)] hover:bg-[var(--secondary)] rounded-md text-[10px] transition-colors cursor-pointer"
              title="Copy transcription"
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
              className="p-1 hover:text-[var(--foreground)] hover:bg-[var(--secondary)] rounded-md text-[10px] transition-colors cursor-pointer"
              title="Regenerate speech"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </ActionBarPrimitive.Reload>
        </ActionBarPrimitive.Root>
      </div>
    </MessagePrimitive.Root>
  );
};

/* ── 3. Single-Row Pill Composer [ Ask or enter directive... (↑) ] ── */
export const ZezoPillComposer: FC<{ placeholder?: string }> = ({
  placeholder,
}) => {
  const isRunning = useAuiState((s) => s.thread.isRunning);

  return (
    <div className="p-3 pb-3 shrink-0 bg-transparent relative z-10">
      <div className="max-w-3xl mx-auto w-full">
        <ComposerPrimitive.Root
          data-slot="aui-composer-root"
          className="group relative flex items-center w-full rounded-full border border-[var(--border)] bg-[var(--card)]/90 backdrop-blur-xl shadow-xs hover:border-[var(--border)]/80 focus-within:border-[var(--accent)]/80 focus-within:ring-2 focus-within:ring-[var(--accent)]/20 pl-3.5 pr-1.5 py-1 transition-[border-color,box-shadow] duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]"
        >
          <ComposerPrimitive.Input
            data-slot="aui-composer-input"
            placeholder={placeholder || "Ask or enter directive..."}
            className="flex-1 bg-transparent border-0 px-1 py-1 text-xs text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none resize-none leading-normal min-h-[28px] max-h-[80px]"
            rows={1}
            autoFocus={false}
          />

          <div className="flex items-center shrink-0 ml-1.5">
            {isRunning ? (
              <ComposerPrimitive.Cancel asChild>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 w-7 p-0 rounded-full border border-[var(--border)] hover:bg-[var(--secondary)] text-[var(--foreground)] shadow-xs transition-all shrink-0 cursor-pointer flex items-center justify-center animate-in zoom-in-95"
                  title="Stop speaking"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                </Button>
              </ComposerPrimitive.Cancel>
            ) : (
              <ComposerPrimitive.Send asChild>
                <Button
                  size="sm"
                  className="h-7 w-7 p-0 bg-primary hover:opacity-90 text-primary-foreground font-semibold rounded-full shadow-xs transition-all shrink-0 cursor-pointer flex items-center justify-center"
                  title="Send directive"
                >
                  <ArrowUp className="w-3.5 h-3.5" />
                </Button>
              </ComposerPrimitive.Send>
            )}
          </div>
        </ComposerPrimitive.Root>
      </div>
    </div>
  );
};

/* ── 4. Dedicated Zezo OS Real-Time Voice Conversation Thread ── */
export interface ZezoChatThreadProps {
  className?: string;
  placeholder?: string;
  emptyTitle?: string;
  emptySubtitle?: string;
  systemState?: 'idle' | 'listening' | 'speaking' | 'thinking' | 'sleeping';
}

export const ZezoChatThread: FC<ZezoChatThreadProps> = ({
  className,
  placeholder,
  emptyTitle,
  emptySubtitle,
  systemState,
}) => {
  return (
    <ThreadPrimitive.Root
      data-slot="aui-thread-root"
      className={cn("flex flex-col h-full w-full min-h-0 bg-transparent", className)}
    >
      {/* Viewport for Live Voice Speech Transcript Turns */}
      <ThreadPrimitive.Viewport
        data-slot="aui-thread-viewport"
        className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0"
      >
        <div className="max-w-3xl mx-auto w-full space-y-3">
          <ThreadPrimitive.Empty>
            <div className="flex flex-col items-center justify-center h-full text-center text-[var(--muted-foreground)] py-14">
              <div className="w-12 h-12 rounded-2xl bg-[#090d16] border border-[var(--border)] flex items-center justify-center mb-3 shadow-sm overflow-hidden p-1">
                <img
                  src="/zezo-avatar.png"
                  alt="ZEZO"
                  className="w-full h-full object-contain transform scale-105"
                />
              </div>
              <div className="text-sm font-semibold text-[var(--foreground)]">
                {emptyTitle || "Ready to talk with ZEZO"}
              </div>
              <div className="text-xs font-mono text-[var(--muted-foreground)] mt-1.5 max-w-[280px] leading-relaxed">
                {emptySubtitle || "Live voice transcription & directives. Speak into your microphone or enter directives below."}
              </div>
            </div>
          </ThreadPrimitive.Empty>

          <ThreadPrimitive.Messages
            components={{
              UserMessage: UserMessage,
              AssistantMessage: AssistantMessage,
            }}
          />

          {/* Real-time Thinking & Task Execution Indicator */}
          {systemState === 'thinking' && (
            <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-[var(--card)]/80 border border-amber-500/30 text-[var(--foreground)] max-w-xs shadow-xs animate-in fade-in duration-200">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
              </span>
              <span className="text-[11px] font-mono text-amber-300 font-medium tracking-wide">
                Thinking & executing task...
              </span>
            </div>
          )}
        </div>
      </ThreadPrimitive.Viewport>

      {/* Ultra-Clean Single-Row Pill Composer */}
      <ZezoPillComposer placeholder={placeholder} />
    </ThreadPrimitive.Root>
  );
};
