import { type FC, useState, useEffect } from "react";
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
  MessageContent as PKMessageContent,
} from "@/components/prompt-kit/message";
import {
  ArrowUp,
  Square,
  Check,
  Copy,
  Paperclip,
  Mic,
  MicOff,
  X,
  FileCode,
  FolderOpen,
  Brain,
  RotateCcw,
  EyeOff,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../reui/badge";
import { cn } from "@/lib/utils";
import { ChatAvatarIcon } from "../avatar/ChatAvatarIcon";
import type { MemoryActivityEntry } from "@/types/zezo";
import { api } from "@/lib/api";

function formatMessageTime(date?: Date | string | number): string {
  if (!date) return "";
  const d = typeof date === "string" || typeof date === "number" ? new Date(date) : date;
  if (!(d instanceof Date) || isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
}

/* ── Memory Activity Chip (Fast-Path Read-Your-Writes Micro-State Chip) ── */
export const ChatMemoryChip: FC<{
  entry: MemoryActivityEntry;
  onUndo?: (entry: MemoryActivityEntry) => void;
  onRetry?: (entry: MemoryActivityEntry) => void;
}> = ({ entry, onUndo, onRetry }) => {
  const [isDismissed, setIsDismissed] = useState(false);
  const [isUndoing, setIsUndoing] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  // Keyboard accessibility: Escape key dismisses chip without deleting/forgetting fact
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsDismissed(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  if (isDismissed) return null;

  const handleUndo = async () => {
    if (isUndoing || !onUndo) return;
    setIsUndoing(true);
    try {
      await onUndo(entry);
      setIsDismissed(true);
    } catch (err) {
      console.error("[ChatMemoryChip] Undo failed:", err);
      setIsUndoing(false);
    }
  };

  const handleRetry = async () => {
    if (isRetrying || !onRetry) return;
    setIsRetrying(true);
    try {
      await onRetry(entry);
    } catch (err) {
      console.error("[ChatMemoryChip] Retry failed:", err);
    } finally {
      setIsRetrying(false);
    }
  };

  if (entry.status === "queued") {
    return (
      <Badge
        variant="queued"
        size="sm"
        className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-sans font-medium text-[var(--muted-foreground)] bg-[var(--card)]/90 border border-[var(--border)] shadow-2xs rounded-full transition-opacity duration-300 animate-pulse select-none"
      >
        <Loader2 className="w-3 h-3 animate-spin text-[var(--primary)] shrink-0" />
        <span>Saving:</span>
        <span className="font-semibold text-[var(--foreground)]">{entry.key}</span>
        {entry.value && (
          <span className="text-[var(--muted-foreground)] font-mono text-[10px] truncate max-w-[120px]">
            ({entry.value})
          </span>
        )}
      </Badge>
    );
  }

  if (entry.status === "failed") {
    return (
      <Badge
        variant="destructive"
        size="sm"
        title={entry.reason || "Failed to persist memory fact"}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-sans font-medium bg-red-500/10 text-red-400 border border-red-500/30 rounded-full transition-opacity duration-300 shadow-2xs select-none"
      >
        <AlertTriangle className="w-3 h-3 text-red-400 shrink-0" />
        <span>Save failed:</span>
        <span className="font-semibold text-red-300">{entry.key}</span>
        {onRetry && (
          <button
            type="button"
            onClick={handleRetry}
            disabled={isRetrying}
            className="inline-flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider text-red-300 hover:text-white bg-red-500/20 hover:bg-red-500/40 px-1.5 py-0.5 rounded cursor-pointer transition-colors ml-1"
            title="Retry memory save"
          >
            <RotateCcw className={cn("w-2.5 h-2.5", isRetrying && "animate-spin")} />
            <span>Retry</span>
          </button>
        )}
      </Badge>
    );
  }

  // entry.status === "persisted"
  const isForgotten = entry.action === "forgotten";
  return (
    <Badge
      variant="completed"
      size="sm"
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-sans font-medium rounded-full shadow-2xs transition-opacity duration-300 select-none",
        isForgotten
          ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
          : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
      )}
    >
      <Brain className="w-3 h-3 shrink-0" />
      <span>{isForgotten ? "Fact removed from memory:" : "Remembered:"}</span>
      <span className="font-semibold text-[var(--foreground)]">{entry.key}</span>
      {!isForgotten && entry.value && (
        <span className="text-[var(--muted-foreground)] font-mono text-[10px] truncate max-w-[140px]">
          ({entry.value})
        </span>
      )}
      {onUndo && (
        <button
          type="button"
          onClick={handleUndo}
          disabled={isUndoing}
          aria-label={`Forget memory ${entry.key}`}
          className="ml-1 p-0.5 text-[var(--muted-foreground)] hover:text-red-400 hover:bg-[var(--secondary)] rounded-full transition-colors cursor-pointer"
          title={isForgotten ? "Undo removal" : "Forget this fact"}
        >
          {isUndoing ? <Loader2 className="w-3 h-3 animate-spin" /> : <X className="w-3 h-3" />}
        </button>
      )}
    </Badge>
  );
};

/* ── 1. User Message (Spoken / Typed Directive) ── */
export const UserMessage: FC = () => {
  const createdAt = useAuiState((s) => s.message.createdAt);
  const timeStr = formatMessageTime(createdAt);

  return (
    <MessagePrimitive.Root
      data-slot="aui-user-message"
      className="w-full max-w-3xl py-1 mx-auto group"
    >
      <PKMessage className="justify-end py-1">
        <PKMessageContent className="rounded-2xl rounded-tr-xs px-3.5 py-2 bg-primary text-primary-foreground font-normal text-xs leading-relaxed max-w-xl break-words">
          <MessagePrimitive.Parts />
        </PKMessageContent>
      </PKMessage>

      <div className="flex items-center justify-end gap-1.5 pr-1 mt-0.5">
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

  // Read-Your-Writes In-Chat Memory Activities
  const [activities, setActivities] = useState<MemoryActivityEntry[]>([]);

  useEffect(() => {
    const handleActivity = (e: Event) => {
      const customEvt = e as CustomEvent<MemoryActivityEntry>;
      if (!customEvt.detail || !customEvt.detail.id) return;
      const entry = customEvt.detail;

      setActivities((prev) => {
        const existingIdx = prev.findIndex((a) => a.id === entry.id);
        if (existingIdx >= 0) {
          const updated = [...prev];
          updated[existingIdx] = {
            ...updated[existingIdx],
            status: entry.status,
            value: entry.value ?? updated[existingIdx].value,
            reason: entry.reason ?? updated[existingIdx].reason,
          };
          return updated;
        }
        // Keep up to 5 recent activity chips
        return [...prev.slice(-4), entry];
      });
    };

    window.addEventListener("zezo_memory_activity", handleActivity);
    return () => window.removeEventListener("zezo_memory_activity", handleActivity);
  }, []);

  const handleUndo = async (entry: MemoryActivityEntry) => {
    if (entry.action === "forgotten") {
      // Revert forget by restoring previous value if known
      if (entry.value) {
        await api.retryFact(entry.category, entry.key, entry.value);
      }
    } else {
      // Forget fact (or revert to previous value)
      await api.deleteFact(entry.category, entry.key, entry.previous_value);
    }
  };

  const handleRetry = async (entry: MemoryActivityEntry) => {
    if (entry.value) {
      await api.retryFact(entry.category, entry.key, entry.value);
    }
  };

  return (
    <MessagePrimitive.Root
      data-slot="aui-assistant-message"
      className="w-full max-w-3xl py-1 mx-auto group"
    >
      <PKMessage className="justify-start items-start gap-2.5 py-1">
        {/* Dynamic Holographic Qivi Companion Avatar Badge */}
        <div className="shrink-0 w-8 h-8 rounded-full border border-[var(--border)] bg-card overflow-hidden flex items-center justify-center p-0.5">
          <ChatAvatarIcon
            size={26}
            expression={isRunning ? 'thinking' : 'happy'}
            state={isRunning ? 'talking' : 'idle'}
          />
        </div>

        {/* Live Speech Dialogue & Real-time Transcription Stream */}
        <PKMessageContent markdown className="flex-1 min-w-0 bg-transparent p-0 text-xs text-[var(--foreground)] leading-relaxed">
          <div className="space-y-1.5">
            <MessagePrimitive.Parts
              components={{
                Text: TextPart,
              }}
            />

            {/* In-Chat Fast-Path Memory Chips */}
            {activities.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {activities.map((act) => (
                  <ChatMemoryChip
                    key={act.id}
                    entry={act}
                    onUndo={handleUndo}
                    onRetry={handleRetry}
                  />
                ))}
              </div>
            )}

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

            {/* Assistant Action Bar & Timestamp - compact inline footer */}
            <div className="flex items-center gap-2 mt-1">
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
              </ActionBarPrimitive.Root>
            </div>
          </div>
        </PKMessageContent>
      </PKMessage>
    </MessagePrimitive.Root>
  );
};

/* ── 3. Single-Row Pill Composer [ Ask or enter directive... (↑) ] ── */
export const ZezoPillComposer: FC<{
  placeholder?: string;
  onAttachFile?: () => void;
  uploadedFiles?: { name: string; size: string; type: string }[];
  onRemoveFile?: (index: number) => void;
  isDictating?: boolean;
  onToggleDictate?: () => void;
}> = ({
  placeholder,
  onAttachFile,
  uploadedFiles,
  onRemoveFile,
  isDictating,
  onToggleDictate,
}) => {
  const isRunning = useAuiState((s) => s.thread.isRunning);

  return (
    <div className="p-3 pb-3 shrink-0 bg-transparent relative z-10">
      <div className="max-w-3xl mx-auto w-full">
        {/* Uploaded Files Chips Strip */}
        {uploadedFiles && uploadedFiles.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2 max-h-24 overflow-y-auto px-1">
            {uploadedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--card)] border border-[var(--border)] text-[11px] text-[var(--foreground)] shadow-2xs"
              >
                {file.type === 'FOLDER' ? (
                  <FolderOpen className="w-3.5 h-3.5 text-[var(--primary)] shrink-0" />
                ) : (
                  <FileCode className="w-3.5 h-3.5 text-[var(--muted-foreground)] shrink-0" />
                )}
                <span className="truncate max-w-[140px] font-medium">{file.name}</span>
                <span className="text-[10px] text-[var(--muted-foreground)] font-mono">({file.size})</span>
                {onRemoveFile && (
                  <button
                    type="button"
                    onClick={() => onRemoveFile(idx)}
                    className="text-[var(--muted-foreground)] hover:text-red-400 transition-colors ml-0.5 cursor-pointer p-0.5 rounded"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        <ComposerPrimitive.Root
          data-slot="aui-composer-root"
        className="group relative flex min-h-[52px] w-full items-center rounded-full border border-[var(--border)] bg-[var(--card)]/90 backdrop-blur-xl hover:border-[var(--border)]/80 focus-within:border-[var(--accent)]/80 focus-within:ring-2 focus-within:ring-[var(--accent)]/20 pl-3 pr-2 py-2 transition-[border-color,box-shadow] duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]"
        >
          {/* File Attachment Action Button */}
          {onAttachFile && (
            <button
              type="button"
              onClick={onAttachFile}
              className="p-2 text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors rounded-full cursor-pointer shrink-0"
              title="Attach files or folder"
            >
              <Paperclip className="w-4 h-4" />
            </button>
          )}


          {/* Voice Dictation Button */}
          {onToggleDictate && (
            <button
              type="button"
              onClick={onToggleDictate}
              className={cn(
                "p-2 transition-colors rounded-full cursor-pointer shrink-0 mr-1",
                isDictating
                  ? "text-red-400 bg-red-500/20 animate-pulse ring-1 ring-red-400/40"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--secondary)]"
              )}
              title={isDictating ? "Stop voice dictation" : "Dictate with voice"}
            >
              {isDictating ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
          )}

          <ComposerPrimitive.Input
            data-slot="aui-composer-input"
            placeholder={placeholder || (isDictating ? "Listening... speak now" : "Ask or enter directive (or tap mic to dictate)...")}
            className="flex-1 bg-transparent border-0 px-2 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none resize-none leading-relaxed min-h-[36px] max-h-[96px]"
            rows={1}
            autoFocus={false}
          />

          <div className="flex items-center shrink-0 ml-1.5">
            {isRunning ? (
              <ComposerPrimitive.Cancel asChild>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-9 w-9 p-0 rounded-full border border-[var(--border)] hover:bg-[var(--secondary)] text-[var(--foreground)] transition-all shrink-0 cursor-pointer flex items-center justify-center animate-in zoom-in-95"
                  title="Stop speaking"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                </Button>
              </ComposerPrimitive.Cancel>
            ) : (
              <ComposerPrimitive.Send asChild>
                <Button
                  size="sm"
                  className="h-9 w-9 p-0 rounded-full bg-primary hover:bg-primary/90 text-primary-foreground transition-all shrink-0 cursor-pointer flex items-center justify-center shadow-xs"
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

export const ZezoChatThread: FC<{
  placeholder?: string;
  className?: string;
  systemState?: string;
  onAttachFile?: () => void;
  uploadedFiles?: { name: string; size: string; type: string }[];
  onRemoveFile?: (index: number) => void;
  isDictating?: boolean;
  onToggleDictate?: () => void;
}> = ({
  placeholder,
  className,
  onAttachFile,
  uploadedFiles,
  onRemoveFile,
  isDictating,
  onToggleDictate,
}) => {
  const [memoryPaused, setMemoryPaused] = useState<boolean>(false);

  useEffect(() => {
    api.getMemoryPause().then((res) => {
      if (res && typeof res.paused === "boolean") {
        setMemoryPaused(res.paused);
      }
    }).catch(() => {});

    const handlePauseChanged = (e: Event) => {
      const customEvt = e as CustomEvent<{ paused: boolean }>;
      if (customEvt.detail && typeof customEvt.detail.paused === "boolean") {
        setMemoryPaused(customEvt.detail.paused);
      }
    };
    window.addEventListener("zezo_memory_pause_changed", handlePauseChanged);
    return () => window.removeEventListener("zezo_memory_pause_changed", handlePauseChanged);
  }, []);

  const handleToggleMemoryPause = async () => {
    const nextState = !memoryPaused;
    setMemoryPaused(nextState);
    try {
      await api.setMemoryPause(nextState);
    } catch (err) {
      console.error("[ZezoChatThread] Failed to toggle memory pause:", err);
      setMemoryPaused(!nextState);
    }
  };

  return (
    <ThreadPrimitive.Root className={cn("flex flex-col h-full w-full bg-transparent overflow-hidden relative", className)}>
      {/* Top Left Corner: Incognito Pause Memory Badge Button */}
      <div className="absolute top-2.5 left-4 z-20">
        <button
          type="button"
          onClick={handleToggleMemoryPause}
          className={cn(
            "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono uppercase tracking-wider transition-all cursor-pointer shadow-2xs backdrop-blur-sm border",
            memoryPaused
              ? "bg-amber-500/20 text-amber-400 border-amber-500/40 hover:bg-amber-500/30"
              : "bg-[var(--card)]/80 text-[var(--muted-foreground)] border-[var(--border)]/70 hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"
          )}
          title={memoryPaused ? "Memory paused (Incognito Active) - Click to resume learning" : "Memory active - Click to pause learning (Incognito)"}
        >
          <EyeOff className={cn("w-3 h-3", memoryPaused && "text-amber-400")} />
          <span>{memoryPaused ? "INCOGNITO" : "MEM"}</span>
        </button>
      </div>
      <ThreadPrimitive.Viewport
        data-slot="aui-thread-viewport"
        className="flex-1 overflow-y-auto px-4 pb-4 pt-10 sm:pt-12 space-y-4 focus:outline-none scroll-smooth"
      >
        <ThreadPrimitive.Messages
          components={{
            UserMessage: UserMessage,
            AssistantMessage: AssistantMessage,
          }}
        />
      </ThreadPrimitive.Viewport>

      <ZezoPillComposer
        placeholder={placeholder}
        onAttachFile={onAttachFile}
        uploadedFiles={uploadedFiles}
        onRemoveFile={onRemoveFile}
        isDictating={isDictating}
        onToggleDictate={onToggleDictate}
      />
    </ThreadPrimitive.Root>
  );
};
