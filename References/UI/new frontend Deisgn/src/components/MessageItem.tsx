import React, { useState } from 'react';
import { Copy, RotateCcw, AlertTriangle, Settings, Check } from 'lucide-react';
import type { ChatMessage } from '../types';
import { ThinkingState } from './ThinkingState';
import { ToolChips } from './ToolChips';

interface MessageItemProps {
  message: ChatMessage;
  onRetry?: (prompt: string) => void;
  onOpenSettings?: () => void;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onRetry,
  onOpenSettings,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const isUser = message.sender === 'user';

  return (
    <div className={`message-row ${isUser ? 'user-message' : 'ai-message'}`}>
      <div className={`message-avatar ${isUser ? 'user-avatar' : 'ai-avatar'}`}>
        {isUser ? 'U' : 'Z'}
      </div>
      <div className="message-body">
        <div className="message-sender-line">
          <span className="message-sender-name">{message.senderName}</span>
          <span className="message-timestamp">{message.timestamp}</span>
        </div>

        <div className="message-content">
          {/* Expandable Agent Thinking Trace (Steps / Reasoning / Coding) */}
          {message.thinking && (
            <ThinkingState 
              variant="Steps" 
              active={message.thinking}
              done="Thought for 4 seconds"
            />
          )}

          {/* Compact Tool Chips with Expandable Details and Hover Diff Tooltips */}
          {message.tools && message.tools.length > 0 && (
            <ToolChips />
          )}

          {/* Message Text Content */}
          {message.content && (
            <div style={{ whiteSpace: 'pre-line' }}>
              <p>{message.content}</p>
              {message.isStreaming && <span className="streaming-cursor"></span>}
            </div>
          )}

          {/* Interrupted Banner */}
          {message.isInterrupted && (
            <div className="interrupted-notice">
              <AlertTriangle size={14} />
              <span>Generation stopped by user</span>
            </div>
          )}

          {/* Error & Recovery Card */}
          {message.isError && message.errorDetail && (
            <div className="error-recovery-card">
              <div className="error-header-row">
                <div className="error-title">
                  <AlertTriangle size={15} />
                  <span>Tool Execution Blocked ({message.errorDetail.toolName})</span>
                </div>
                <span className="tool-status-pill failed">Exit code 1</span>
              </div>
              <div className="error-message-text">
                {message.errorDetail.message}
              </div>
              <div className="error-actions-row">
                {onRetry && (
                  <button 
                    className="recovery-btn retry-primary"
                    onClick={() => onRetry('Fallback to local socket: docker -H unix:///var/run/docker.sock ps')}
                  >
                    <RotateCcw size={13} />
                    <span>Retry with Local Fallback</span>
                  </button>
                )}
                {onOpenSettings && (
                  <button className="recovery-btn" onClick={onOpenSettings}>
                    <Settings size={13} />
                    <span>Inspect Security Credentials</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Message Actions Bar (Copy & Retry) */}
        {!isUser && !message.isStreaming && (
          <div className="message-actions-bar">
            <button className="msg-action-btn copy-msg-btn" onClick={handleCopy} title="Copy response">
              {copied ? <Check size={12} /> : <Copy size={12} />}
              <span>{copied ? 'Copied!' : 'Copy'}</span>
            </button>
            {onRetry && (
              <button 
                className="msg-action-btn retry-msg-btn" 
                onClick={() => onRetry('Can you re-run this operation?')}
                title="Retry response"
              >
                <RotateCcw size={12} />
                <span>Retry</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
