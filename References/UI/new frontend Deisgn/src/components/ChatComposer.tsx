import React, { useRef, useState, useEffect } from 'react';
import { Paperclip, Mic, Send, Square, X, FileText } from 'lucide-react';

interface ChatComposerProps {
  onSendMessage: (text: string) => void;
  onStop: () => void;
  isAgentActive: boolean;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  onSendMessage,
  onStop,
  isAgentActive,
}) => {
  const [text, setText] = useState('');
  const [files, setFiles] = useState<{ id: string; name: string }[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setText('');
    setFiles([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === 'Escape' && isAgentActive) {
      onStop();
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).map(f => ({
        id: Math.random().toString(36).substring(7),
        name: f.name
      }));
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const handleRemoveFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const toggleVoiceDictation = () => {
    setIsRecording(!isRecording);
    if (!isRecording) {
      // Simulate live transcribed speech insertion
      setTimeout(() => {
        setText(prev => prev ? `${prev} Inspect system daemon status` : 'Inspect system daemon status');
        setIsRecording(false);
      }, 2500);
    }
  };

  return (
    <div className={`chat-composer-dock ${isAgentActive ? 'agent-active' : ''}`}>
      <div className="composer-card">
        
        {/* Attached Chips Tray */}
        {files.length > 0 && (
          <div className="attached-chips-tray">
            {files.map(file => (
              <div key={file.id} className="file-chip">
                <FileText size={12} />
                <span>{file.name}</span>
                <span className="file-chip-remove" onClick={() => handleRemoveFile(file.id)}>
                  <X size={12} />
                </span>
              </div>
            ))}
          </div>
        )}

        <textarea
          ref={textareaRef}
          className="composer-textarea"
          rows={1}
          placeholder={
            isRecording 
              ? "Listening to voice dictation..." 
              : isAgentActive 
                ? "ZEZO is working... (Esc or click Stop to interrupt)" 
                : "Ask ZEZO anything or type a prompt... (Shift+Enter for newline)"
          }
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
        />

        <div className="composer-footer">
          <div className="composer-left-tools">
            <input 
              type="file" 
              ref={fileInputRef} 
              multiple 
              hidden 
              onChange={handleFileUpload} 
            />
            <button 
              className="composer-tool-btn" 
              onClick={() => fileInputRef.current?.click()}
              title="Attach files"
            >
              <Paperclip size={16} />
            </button>

            <button 
              className={`composer-tool-btn ${isRecording ? 'recording' : ''}`}
              onClick={toggleVoiceDictation}
              title="Voice Dictation"
            >
              <Mic size={16} />
            </button>
          </div>

          <div className="composer-right-actions">
            {isAgentActive ? (
              <button 
                className="stop-generation-btn" 
                onClick={onStop}
                title="Stop generation (Esc)"
              >
                <Square size={12} fill="currentColor" />
                <span>Stop</span>
              </button>
            ) : (
              <button 
                className="send-message-btn" 
                onClick={handleSend}
                title="Send Message (Enter)"
              >
                <Send size={15} />
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

