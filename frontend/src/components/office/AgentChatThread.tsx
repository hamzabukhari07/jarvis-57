import { type FC } from "react";
import {
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  ActionBarPrimitive,
  useAuiState,
} from "@assistant-ui/react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import { ThinkingTool } from "@/components/assistant-ui/elements/thinking-indicator";
import {
  Message as PKMessage,
  MessageContent as PKMessageContent,
} from "@/components/prompt-kit/message";
import {
  ArrowUp,
  Square,
  Copy,
  Paperclip,
  X,
  FileCode,
  FolderOpen,
} from "@/lib/zezo-icons";
import { Button } from "../ui/button";
import { cn } from "@/lib/utils";
import { Blobatar } from "blobatar/react";
import type { AgentOfficeMember } from "./AutonomousOfficeScreen";

function formatMessageTime(date?: Date | string | number): string {
  if (!date) return "";
  const d = typeof date === "string" || typeof date === "number" ? new Date(date) : date;
  if (!(d instanceof Date) || isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
}

/* ── 1. User Message (Hamza's Directive to Agent) ── */
export const AgentUserMessage: FC = () => {
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

/* ── 2. Agent Assistant Message (Agent Response with its own Blobatar & Persona) ── */
export const AgentAssistantMessage: FC<{ agent: AgentOfficeMember }> = ({ agent }) => {
  const createdAt = useAuiState((s) => s.message.createdAt);
  const isRunning = useAuiState((s) => s.message.status?.type === "running");
  const hasContent = useAuiState((s) => {
    const parts = s.message.parts;
    if (!parts || parts.length === 0) return false;
    return parts.some((p: any) =>
      p.type === "text" && Boolean(p.text && p.text.trim().length > 0)
    );
  });
  const timeStr = formatMessageTime(createdAt);

  return (
    <MessagePrimitive.Root
      data-slot="aui-assistant-message"
      className="w-full max-w-3xl py-1 mx-auto group"
    >
      <PKMessage className="justify-start items-start gap-2.5 py-1">
        {/* Agent's Own Dedicated Blobatar Avatar */}
        <div
          className="shrink-0 w-8 h-8 rounded-full border border-[var(--border)] bg-[var(--background)] overflow-hidden flex items-center justify-center p-0.5 shadow-2xs"
          title={`${agent.name} (${agent.role})`}
        >
          <Blobatar name={agent.name} size={28} className="h-full w-full object-contain" />
        </div>

        {/* Agent Dialogue & Code Execution Payload */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-xs font-semibold text-[var(--foreground)]">{agent.name}</span>
            <span className="text-[10px] text-[var(--muted-foreground)] font-mono">({agent.role})</span>
          </div>

          <PKMessageContent markdown className="flex-1 min-w-0 bg-transparent p-0 text-xs text-[var(--foreground)] leading-relaxed space-y-1.5">
            {/* Thinking / Loading indicator when assistant message is running but no text has arrived yet */}
            {isRunning && !hasContent && (
              <div className="flex items-center py-1 text-xs text-[var(--muted-foreground)]">
                <ThinkingTool state="thinking" />
              </div>
            )}

            <div className="space-y-1.5">
              <MessagePrimitive.Parts
                components={{
                  Text: TextPart,
                }}
              />
            </div>
          </PKMessageContent>

          <div className="flex items-center gap-2 mt-1">
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
                  title="Copy reply"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </ActionBarPrimitive.Copy>
            </ActionBarPrimitive.Root>
          </div>
        </div>
      </PKMessage>
    </MessagePrimitive.Root>
  );
};

/* ── 3. Agent Chat Composer ── */
export const AgentChatComposer: FC<{
  placeholder?: string;
  onAttachFile?: () => void;
  uploadedFiles?: { name: string; size: string; type: string }[];
  onRemoveFile?: (index: number) => void;
}> = ({
  placeholder,
  onAttachFile,
  uploadedFiles = [],
  onRemoveFile,
}) => {
  const isRunning = useAuiState((s) => s.thread.isRunning);

  return (
    <div className="w-full shrink-0 px-4 pb-4 pt-1 bg-gradient-to-t from-[var(--background)] via-[var(--background)]/90 to-transparent">
      <div className="max-w-3xl mx-auto flex flex-col gap-2">
        {/* Uploaded Files Strip */}
        {uploadedFiles.length > 0 && (
          <div className="flex items-center gap-2 overflow-x-auto py-1 px-1">
            {uploadedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--card)] border border-[var(--border)] text-[11px] text-[var(--foreground)] shadow-2xs"
              >
                {file.type === "FOLDER" ? (
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

          <ComposerPrimitive.Input
            data-slot="aui-composer-input"
            placeholder={placeholder || "Assign task or send directive to agent..."}
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
                  title="Stop agent run"
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

/* ── 4. Main Agent Chat Thread Component ── */
export const AgentChatThread: FC<{
  agent: AgentOfficeMember;
  placeholder?: string;
  className?: string;
  onAttachFile?: () => void;
  uploadedFiles?: { name: string; size: string; type: string }[];
  onRemoveFile?: (index: number) => void;
}> = ({
  agent,
  placeholder,
  className,
  onAttachFile,
  uploadedFiles,
  onRemoveFile,
}) => {
  return (
    <ThreadPrimitive.Root className={cn("flex flex-col h-full w-full bg-transparent overflow-hidden relative", className)}>
      <ThreadPrimitive.Viewport
        data-slot="aui-thread-viewport"
        className="flex-1 overflow-y-auto px-4 pb-4 pt-6 space-y-4 focus:outline-none scroll-smooth"
      >
        <ThreadPrimitive.Messages
          components={{
            UserMessage: AgentUserMessage,
            AssistantMessage: () => <AgentAssistantMessage agent={agent} />,
          }}
        />
      </ThreadPrimitive.Viewport>

      <AgentChatComposer
        placeholder={placeholder}
        onAttachFile={onAttachFile}
        uploadedFiles={uploadedFiles}
        onRemoveFile={onRemoveFile}
      />
    </ThreadPrimitive.Root>
  );
};

