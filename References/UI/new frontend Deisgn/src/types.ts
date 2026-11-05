export interface ToolCall {
  id: string;
  name: string;
  detail: string;
  command: string;
  output: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  senderName: string;
  timestamp: string;
  content: string;
  tools?: ToolCall[];
  thinking?: string;
  isStreaming?: boolean;
  isError?: boolean;
  errorDetail?: {
    toolName: string;
    message: string;
  };
  isInterrupted?: boolean;
}

export interface Session {
  id: string;
  title: string;
  time: string;
  iconType: 'chat' | 'voice' | 'terminal' | 'flow' | 'doc';
  section: 'active' | 'archived';
}

export type VoiceInputMode = 'ptt' | 'wakeword' | 'always';
export type VoiceCallState = 'listening' | 'thinking' | 'speaking' | 'paused' | 'disconnected';

export interface TranscriptTurn {
  id: string;
  speaker: 'user' | 'assistant';
  timestamp: string;
  text: string;
  isInterim?: boolean;
}

