import React, { useState, useRef, useEffect } from 'react';
import { 
  Sun, Moon, PanelLeft, MessageSquare, Mic, Copy, AlertCircle, Check 
} from 'lucide-react';
import type { Session, ChatMessage, ToolCall } from './types';
import { Sidebar } from './components/Sidebar';
import { MessageItem } from './components/MessageItem';
import { ChatComposer } from './components/ChatComposer';
import { VoiceView } from './components/VoiceView';

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'm1',
    sender: 'user',
    senderName: 'You',
    timestamp: '10:14 AM',
    content: 'Can you inspect the audio daemon and verify why the WebSocket duplex stream was dropping frames during the last live session?'
  },
  {
    id: 'm2',
    sender: 'assistant',
    senderName: 'ZEZO Core',
    timestamp: '10:14 AM',
    content: 'I reviewed the live buffer logs from the Core Audio server. The ring buffer threshold was set to 50ms, causing occasional underruns when the neural companion switched to full duplex mode.\n\nThe buffer adjustment has been written to 120ms. You can now switch to Live Voice Mode to test zero-latency real-time voice interaction.',
    tools: [
      {
        id: 't1',
        name: 'fs_edit',
        detail: 'audio_daemon/stream_sink.py:42',
        command: 'PATCH StreamSink.BUFFER_MS = 120 # increased buffer depth to eliminate frame dropping',
        output: 'PATCH APPLIED: 1 insertion(+), 1 deletion(-)',
        status: 'completed'
      }
    ]
  }
];

export const App: React.FC = () => {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [mode, setMode] = useState<'chat' | 'voice'>('chat');
  const [currentSession, setCurrentSession] = useState<Session>({
    id: '1',
    title: 'Debugging Audio Pipeline',
    time: 'Now',
    iconType: 'chat',
    section: 'active'
  });

  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const [isAgentActive, setIsAgentActive] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [copiedFullChat, setCopiedFullChat] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeTurnRef = useRef<{ cancel: () => void } | null>(null);

  // Apply data-theme attribute to both html and body
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
  }, [theme]);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAgentActive]);

  // Global Keyboard shortcuts (Cmd/Ctrl + B, Esc)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        setIsSidebarCollapsed(prev => !prev);
      }
      if (e.key === 'Escape' && isAgentActive) {
        handleStopAgent();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAgentActive]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const handleStopAgent = () => {
    if (activeTurnRef.current) {
      activeTurnRef.current.cancel();
      activeTurnRef.current = null;
    }
    setIsAgentActive(false);
  };

  const handleSendMessage = (text: string, isSimulatedError = false) => {
    handleStopAgent();

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      senderName: 'You',
      timestamp: 'Just now',
      content: text,
    };

    const aiMessageId = (Date.now() + 1).toString();
    const initialAiMessage: ChatMessage = {
      id: aiMessageId,
      sender: 'assistant',
      senderName: 'ZEZO Core',
      timestamp: 'Just now',
      content: '',
      thinking: 'Thinking...',
      tools: [],
    };

    setMessages(prev => [...prev, userMessage, initialAiMessage]);
    setIsAgentActive(true);

    let cancelled = false;
    const timeouts: ReturnType<typeof setTimeout>[] = [];

    activeTurnRef.current = {
      cancel: () => {
        cancelled = true;
        timeouts.forEach(clearTimeout);
        setMessages(prev => prev.map(m => {
          if (m.id === aiMessageId) {
            return {
              ...m,
              thinking: undefined,
              isStreaming: false,
              isInterrupted: true,
              tools: m.tools?.map(t => (t.status === 'running' || t.status === 'queued') ? { ...t, status: 'cancelled' } : t)
            };
          }
          return m;
        }));
      }
    };

    // Step 1: Thinking -> Planning
    timeouts.push(setTimeout(() => {
      if (cancelled) return;
      setMessages(prev => prev.map(m => m.id === aiMessageId ? { ...m, thinking: 'Formulating execution plan & selecting tools...' } : m));
    }, 600));

    if (!isSimulatedError) {
      // Step 2: Tool 1 execution
      timeouts.push(setTimeout(() => {
        if (cancelled) return;
        const tool1: ToolCall = {
          id: 't1',
          name: 'fs_read',
          detail: 'audio_daemon/config.json',
          command: 'cat audio_daemon/config.json | grep -i buffer',
          output: '{\n  "duplex_buffer_ms": 120,\n  "sample_rate": 48000,\n  "active_sink": "CoreAudioDefault"\n}',
          status: 'running'
        };
        setMessages(prev => prev.map(m => m.id === aiMessageId ? { ...m, tools: [tool1] } : m));

        timeouts.push(setTimeout(() => {
          if (cancelled) return;
          // Tool 1 completed, launch Tool 2
          const tool2: ToolCall = {
            id: 't2',
            name: 'net_ping',
            detail: 'ws://127.0.0.1:8080/duplex',
            command: 'wscat -c ws://127.0.0.1:8080/duplex --ping 3',
            output: 'ROUNDTRIP: 14ms | 18ms | 12ms (average: 14.6ms, 0% packet loss)',
            status: 'running'
          };
          setMessages(prev => prev.map(m => m.id === aiMessageId ? {
            ...m,
            tools: [{ ...tool1, status: 'completed' }, tool2]
          } : m));

          // Tool 2 finishes -> Start Streaming Response
          timeouts.push(setTimeout(() => {
            if (cancelled) return;
            setMessages(prev => prev.map(m => m.id === aiMessageId ? {
              ...m,
              thinking: undefined,
              isStreaming: true,
              tools: [{ ...tool1, status: 'completed' }, { ...tool2, status: 'completed' }]
            } : m));

            const fullText = "Telemetry verification completed. Both the audio ring-buffer (120ms) and the duplex WebSocket roundtrip (14.6ms) are fully operating within target parameters.\n\nAll frame drops have ceased. You can safely initiate full real-time speech conversations.";
            const words = fullText.split(' ');
            let wIdx = 0;

            const streamInterval = setInterval(() => {
              if (cancelled) {
                clearInterval(streamInterval);
                return;
              }
              if (wIdx < words.length) {
                const nextWords = words.slice(0, wIdx + 1).join(' ');
                setMessages(prev => prev.map(m => m.id === aiMessageId ? { ...m, content: nextWords } : m));
                wIdx++;
              } else {
                clearInterval(streamInterval);
                setMessages(prev => prev.map(m => m.id === aiMessageId ? { ...m, isStreaming: false } : m));
                setIsAgentActive(false);
              }
            }, 45);

          }, 800));

        }, 700));

      }, 1200));

    } else {
      // Error simulation scenario
      timeouts.push(setTimeout(() => {
        if (cancelled) return;
        const errTool: ToolCall = {
          id: 'err1',
          name: 'remote_exec',
          detail: 'tcp://cluster.zezo.internal:2376',
          command: 'docker -H tcp://cluster.zezo.internal:2376 ps',
          output: 'FATAL: TLS Handshake failed: x509: certificate signed by unknown authority\nError: client certificate unverified',
          status: 'running'
        };
        setMessages(prev => prev.map(m => m.id === aiMessageId ? { ...m, tools: [errTool] } : m));

        timeouts.push(setTimeout(() => {
          if (cancelled) return;
          setMessages(prev => prev.map(m => m.id === aiMessageId ? {
            ...m,
            thinking: undefined,
            tools: [{ ...errTool, status: 'failed' }],
            isError: true,
            errorDetail: {
              toolName: 'remote_exec',
              message: 'The remote Docker daemon refused connection because the local mTLS security certificates are missing or expired in ~/.zezo/certs/client.pem.'
            }
          } : m));
          setIsAgentActive(false);
        }, 800));

      }, 1200));
    }
  };

  const handleCopyFullChat = () => {
    const text = messages.map(m => `${m.senderName} (${m.timestamp}):\n${m.content}`).join('\n\n');
    navigator.clipboard.writeText(text);
    setCopiedFullChat(true);
    setTimeout(() => setCopiedFullChat(false), 1500);
  };

  return (
    <div className={`app-wrapper ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      
      {/* 1. Global Sidebar */}
      <Sidebar 
        currentSession={currentSession}
        onSelectSession={(session) => {
          setCurrentSession(session);
        }}
        onNewChat={() => {
          setCurrentSession({
            id: Date.now().toString(),
            title: 'Untitled Session',
            time: 'Now',
            iconType: 'chat',
            section: 'active'
          });
          setMessages([
            {
              id: 'init',
              sender: 'assistant',
              senderName: 'ZEZO Core',
              timestamp: 'Just now',
              content: 'Hello! I am ZEZO, your autonomous Desktop Operating System companion. Ask a question, inspect code, run terminal commands, or test multiple tool sequences.'
            }
          ]);
        }}
        onOpenSettings={() => setShowSettingsModal(true)}
      />

      {/* 2. Main Stage */}
      <main className="main-stage">
        
        {/* Top Header */}
        <header className="stage-header">
          <div className="header-left">
            <button 
              className="action-icon-btn" 
              onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
              title="Toggle Sidebar (⌘B)"
            >
              <PanelLeft size={16} />
            </button>
            <div className="session-header-title">
              <span className="session-header-crumb">Session /</span>
              <span>{currentSession.title}</span>
            </div>
          </div>

          <div className="header-right">
            {/* Mode Switcher docked close to theme toggle */}
            <div className="mode-segmented-control">
              <button 
                className={`mode-btn ${mode === 'chat' ? 'active' : ''}`}
                onClick={() => setMode('chat')}
              >
                <MessageSquare size={14} />
                <span>Chat Mode</span>
              </button>
              <button 
                className={`mode-btn ${mode === 'voice' ? 'active' : ''}`}
                onClick={() => setMode('voice')}
              >
                <Mic size={14} />
                <span>Live Voice Mode</span>
              </button>
            </div>

            <button 
              className="action-icon-btn" 
              onClick={toggleTheme}
              title="Toggle Light / Dark Mode"
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>
        </header>

        {/* Viewport Canvas */}
        <section className="stage-canvas">
          
          {mode === 'chat' ? (
            <div className="chat-mode-container" style={{ display: 'flex' }}>
              
              {/* Top Stats Strip */}
              <div className="chat-action-strip">
                <div className="strip-stats">
                  <div className="strip-stat-item">
                    <span>Context:</span>
                    <b>14.2k tokens</b>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button 
                    className="strip-btn" 
                    onClick={() => handleSendMessage('Attempting to mount remote Docker cluster without authorization credentials', true)}
                    title="Simulate Error & Recovery Flow"
                  >
                    <AlertCircle size={13} />
                    <span>Simulate Tool Error</span>
                  </button>

                  <button className="strip-btn" onClick={handleCopyFullChat}>
                    {copiedFullChat ? <Check size={13} /> : <Copy size={13} />}
                    <span>{copiedFullChat ? 'Copied!' : 'Copy Full Chat'}</span>
                  </button>
                </div>
              </div>

              {/* Message Feed */}
              <div className="chat-messages-thread">
                {messages.map(msg => (
                  <MessageItem 
                    key={msg.id} 
                    message={msg}
                    onRetry={(prompt) => handleSendMessage(prompt)}
                    onOpenSettings={() => setShowSettingsModal(true)}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Composer Input Dock */}
              <ChatComposer 
                onSendMessage={(txt) => handleSendMessage(txt)}
                onStop={handleStopAgent}
                isAgentActive={isAgentActive}
              />

            </div>
          ) : (
            <VoiceView onInterrupt={handleStopAgent} />
          )}

        </section>

      </main>

      {/* Settings Modal */}
      {showSettingsModal && (
        <div className="settings-modal show" onClick={() => setShowSettingsModal(false)}>
          <div className="settings-modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="settings-modal-header">
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>System Audio & Credential Settings</h3>
              <button className="action-icon-btn" onClick={() => setShowSettingsModal(false)}>✕</button>
            </div>
            <div className="settings-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--ink-2)', display: 'block', marginBottom: '6px' }}>Microphone Device</label>
                <div className="segmented-control" style={{ gridTemplateColumns: '1fr 1fr' }}>
                  <button className="segmented-btn" data-active="true">Default (MacBook Pro Mic)</button>
                  <button className="segmented-btn">USB Studio Interface</button>
                </div>
              </div>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--ink-2)', display: 'block', marginBottom: '6px' }}>Docker Cluster Certificate</label>
                <input 
                  type="text" 
                  value="~/.zezo/certs/client.pem" 
                  readOnly 
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', background: 'var(--well)', border: '1px solid var(--hairline)', fontSize: '12px' }} 
                />
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default App;
