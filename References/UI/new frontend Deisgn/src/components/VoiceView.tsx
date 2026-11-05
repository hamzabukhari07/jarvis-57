import React, { useState, useEffect } from 'react';
import { 
  Mic, Volume2, Moon, Square, ChevronDown, Check, Activity 
} from 'lucide-react';
import { Mascot } from 'wobnimo/react';
import { boo } from 'wobnimo/characters/boo';
import type { VoiceInputMode } from '../types';

interface VoiceViewProps {
  onInterrupt: () => void;
}

type TurnSpeaker = 'user' | 'assistant';

interface ConversationTurn {
  speaker: TurnSpeaker;
  text: string;
}

const CONVERSATION_SCRIPT: ConversationTurn[] = [
  {
    speaker: 'user',
    text: 'Can you check the audio ring-buffer status and confirm duplex latency?'
  },
  {
    speaker: 'assistant',
    text: 'I inspected the Core Audio telemetry. Duplex buffer depth is running at 120ms with a 14ms roundtrip, and no dropped frames have occurred.'
  },
  {
    speaker: 'user',
    text: 'Can you show me the active background agents right now?'
  },
  {
    speaker: 'assistant',
    text: 'Currently, three autonomous agents are active: Workspace Indexer, Audio Sentry, and Git Syncer. All background nodes are nominal.'
  },
  {
    speaker: 'user',
    text: 'Optimize memory allocation for the neural model cache.'
  },
  {
    speaker: 'assistant',
    text: 'Neural weights re-quantized to 4-bit precision. Freed 1.4 gigabytes of unified VRAM while retaining full inference accuracy.'
  }
];

// Character spec for Boo with custom expanded bounding sphere to completely prevent motion clipping
const unclippedBoo = {
  ...boo,
  frame: { target: 0.76, radius: 1.15 },
  bound: { y: 0.72, radius: 1.25 }
};

export const VoiceView: React.FC<VoiceViewProps> = ({ onInterrupt }) => {
  const [isMicMuted, setIsMicMuted] = useState(false);
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false);
  const [isSleeping, setIsSleeping] = useState(false);
  const [callSeconds, setCallSeconds] = useState(94); // 01:34
  
  // Voice Input Mode Dropdown state
  const [inputMode, setInputMode] = useState<VoiceInputMode>('ptt');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  // Turn-based live state machine
  const [turnIndex, setTurnIndex] = useState(0);
  const [stage, setStage] = useState<'streaming' | 'settled' | 'fade-out'>('streaming');
  const [streamedWordCount, setStreamedWordCount] = useState(0);

  // Simulated live audio wave reactivity for header indicator
  const [audioFreqs, setAudioFreqs] = useState<number[]>([18, 32, 54, 40, 22]);

  // Overall call timer
  useEffect(() => {
    const timer = setInterval(() => {
      setCallSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Turn data
  const currentTurn = CONVERSATION_SCRIPT[turnIndex % CONVERSATION_SCRIPT.length];
  const isAssistant = currentTurn.speaker === 'assistant';
  const words = currentTurn.text.split(' ');

  // Compute Wobnimo mascot emotional state dynamically based on app activity
  const getMascotState = (): "idle" | "listening" | "thinking" | "speaking" | "sleeping" => {
    if (isSleeping) return "sleeping";
    if (stage === 'fade-out') return "thinking";
    if (isAssistant) {
      return stage === 'streaming' ? "speaking" : "idle";
    } else {
      return stage === 'streaming' ? "listening" : "thinking";
    }
  };

  // Audio wave frequency bars modulation
  useEffect(() => {
    if (isSleeping) {
      setAudioFreqs([6, 6, 6, 6, 6]);
      return;
    }

    const interval = setInterval(() => {
      if (stage === 'streaming') {
        if (isAssistant) {
          // Energetic wave when ZEZO speaks
          setAudioFreqs([
            Math.floor(20 + Math.random() * 55),
            Math.floor(35 + Math.random() * 65),
            Math.floor(50 + Math.random() * 80),
            Math.floor(35 + Math.random() * 65),
            Math.floor(20 + Math.random() * 55)
          ]);
        } else {
          // Warm dynamic wave when User speaks
          setAudioFreqs([
            Math.floor(18 + Math.random() * 45),
            Math.floor(28 + Math.random() * 50),
            Math.floor(40 + Math.random() * 60),
            Math.floor(28 + Math.random() * 50),
            Math.floor(18 + Math.random() * 45)
          ]);
        }
      } else {
        // Idle breathing state
        setAudioFreqs([10, 16, 22, 16, 10]);
      }
    }, 120);

    return () => clearInterval(interval);
  }, [stage, isAssistant, isSleeping]);

  // Unified word-by-word streaming effect for both User and ZEZO
  useEffect(() => {
    if (stage !== 'streaming') return;

    if (streamedWordCount < words.length) {
      // Natural cadence per word (110ms - 180ms)
      const delay = Math.floor(110 + Math.random() * 70);
      const timer = setTimeout(() => {
        setStreamedWordCount(prev => prev + 1);
      }, delay);
      return () => clearTimeout(timer);
    } else {
      // All words streamed, pause and settle before switching turn
      const settlePause = isAssistant ? 2500 : 1800;
      const settleTimer = setTimeout(() => {
        setStage('settled');
        setTimeout(() => {
          setStage('fade-out');
        }, 600);
      }, settlePause);
      return () => clearTimeout(settleTimer);
    }
  }, [stage, streamedWordCount, words.length, isAssistant]);

  // Turn fade-out and switch to next turn
  useEffect(() => {
    if (stage === 'fade-out') {
      const fadeTimer = setTimeout(() => {
        setTurnIndex(prev => (prev + 1) % CONVERSATION_SCRIPT.length);
        setStreamedWordCount(0);
        setStage('streaming');
      }, 500);
      return () => clearTimeout(fadeTimer);
    }
  }, [stage]);

  // Handle manual interrupt
  const handleInterruptClick = () => {
    onInterrupt();
    setStage('fade-out');
    setTimeout(() => {
      // Switch back to user speaking
      setTurnIndex(prev => (prev % 2 === 0 ? prev : (prev + 1) % CONVERSATION_SCRIPT.length));
      setStreamedWordCount(0);
      setStage('streaming');
    }, 300);
  };

  const formatTimer = (sec: number) => {
    const m = String(Math.floor(sec / 60)).padStart(2, '0');
    const s = String(sec % 60).padStart(2, '0');
    return `${m}:${s}`;
  };

  const getModeLabel = () => {
    switch (inputMode) {
      case 'wakeword': return 'Wake Words';
      case 'always': return 'Always Listening';
      default: return 'Push to talk';
    }
  };

  return (
    <div className="voice-mode-container" style={{ display: 'flex' }}>
      
      {/* Top Status Bar with Live Audio Activity */}
      <div className="voice-top-status">
        <div className="voice-status-left">
          <div className="voice-call-state-pill">
            <span className={`state-dot ${isSleeping ? 'sleeping' : isAssistant ? 'speaking' : 'listening'}`} />
            <span>
              {isSleeping 
                ? 'Standby (Sleeping)' 
                : isMicMuted 
                  ? 'Microphone Muted' 
                  : isAssistant 
                    ? 'ZEZO is speaking...' 
                    : 'Listening to your voice...'}
            </span>
          </div>

          {/* Header Mini Equalizer Reactive Wave */}
          {!isSleeping && (
            <div className="header-audio-spectrum" title="Duplex Audio Stream">
              {audioFreqs.map((height, i) => (
                <div 
                  key={i} 
                  className="header-eq-bar" 
                  style={{ height: `${Math.max(4, Math.round(height * 0.22))}px` }} 
                />
              ))}
            </div>
          )}
        </div>

        <div className="voice-status-right">
          <span>Duration: <b className="call-timer">{formatTimer(callSeconds)}</b></span>
        </div>
      </div>

      {/* Center Interactive Stage */}
      <div className="voice-avatar-stage clean-streaming-stage">
        
        {/* Subtle Ambient Light Floor Glow */}
        <div className={`avatar-ambient-halo ${isAssistant ? 'active-speaking' : 'active-listening'}`} />

        {/* Wobnimo "boo" Mascot directly above transcription with expanded unclipped bounds */}
        <div className="wobnimo-mascot-wrapper">
          <Mascot 
            character={unclippedBoo} 
            state={getMascotState()} 
            style={{ width: 170, height: 170 }}
          />
        </div>

        {/* Interactive Streaming Light Transcript Deck */}
        <div className="voice-streaming-deck clean-deck">
          {/* Speaker Badge */}
          <div className="deck-speaker-header">
            {isAssistant ? (
              <span className="deck-speaker-badge zezo-badge">
                ZEZO
              </span>
            ) : (
              <span className="deck-speaker-badge user-badge">
                You
              </span>
            )}
            <span className="deck-status-hint">
              {stage === 'streaming' 
                ? (isAssistant ? 'Streaming response' : 'Transcribing live...') 
                : (stage === 'settled' ? 'Finished speaking' : 'Processing...')}
            </span>
          </div>

          {/* Text Container with Turn Transition Effects on the exact same position */}
          <div className={`deck-text-area ${stage} ${isAssistant ? 'assistant-mode' : 'user-mode'}`}>
            <p className={`streaming-response-paragraph ${isAssistant ? 'assistant-text' : 'user-text'}`}>
              {words.slice(0, streamedWordCount).map((word, idx) => (
                <span 
                  key={idx} 
                  className={`streamed-word ${idx === streamedWordCount - 1 && stage === 'streaming' ? 'latest-word-light' : ''}`}
                >
                  {word}{' '}
                </span>
              ))}
              {stage === 'streaming' && (
                <span className="streaming-cursor-light" />
              )}
            </p>
          </div>
        </div>

      </div>

      {/* Floating Hardware Bench Dock */}
      <div className="voice-floating-bench">
        {/* Custom Input Mode Select Dropdown inside bench-segment */}
        <div className="bench-segment">
          <div className={`voice-input-mode-dropdown-wrapper ${isDropdownOpen ? 'open' : ''}`}>
            <button 
              className="bench-ptt-pill" 
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              title="Select Voice Input Mode"
            >
              <Activity size={13} />
              <span>{getModeLabel()}</span>
              <ChevronDown className="select-caret" size={12} strokeWidth={2.2} />
            </button>

            {isDropdownOpen && (
              <div className="voice-input-mode-menu">
                <div 
                  className={`voice-mode-option-item ${inputMode === 'ptt' ? 'selected' : ''}`}
                  onClick={() => { setInputMode('ptt'); setIsDropdownOpen(false); }}
                >
                  <div className="voice-mode-option-left">
                    <span>Push to talk</span>
                  </div>
                  {inputMode === 'ptt' && <Check size={14} className="check-icon" strokeWidth={2.5} />}
                </div>

                <div 
                  className={`voice-mode-option-item ${inputMode === 'wakeword' ? 'selected' : ''}`}
                  onClick={() => { setInputMode('wakeword'); setIsDropdownOpen(false); }}
                >
                  <div className="voice-mode-option-left">
                    <span>Wake Words</span>
                  </div>
                  {inputMode === 'wakeword' && <Check size={14} className="check-icon" strokeWidth={2.5} />}
                </div>

                <div 
                  className={`voice-mode-option-item ${inputMode === 'always' ? 'selected' : ''}`}
                  onClick={() => { setInputMode('always'); setIsDropdownOpen(false); }}
                >
                  <div className="voice-mode-option-left">
                    <span>Always Listening</span>
                  </div>
                  {inputMode === 'always' && <Check size={14} className="check-icon" strokeWidth={2.5} />}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="bench-divider-vert"></div>

        {/* Mic Mute Toggle */}
        <button 
          className={`bench-btn-round ${isMicMuted ? 'muted' : ''}`}
          onClick={() => setIsMicMuted(!isMicMuted)}
          title="Toggle Mic Mute"
        >
          <Mic size={15} />
        </button>

        {/* Speaker Mute Toggle */}
        <button 
          className={`bench-btn-round ${isSpeakerMuted ? 'muted' : ''}`}
          onClick={() => setIsSpeakerMuted(!isSpeakerMuted)}
          title="Toggle Speaker Mute"
        >
          <Volume2 size={15} />
        </button>

        {/* Standby / Sleep Toggle */}
        <button 
          className={`bench-btn-round ${isSleeping ? 'muted' : ''}`}
          onClick={() => setIsSleeping(!isSleeping)}
          title="Standby / Sleep"
        >
          <Moon size={15} />
        </button>

        <div className="bench-divider-vert"></div>

        {/* Interrupt Button */}
        <button className="bench-interrupt-btn" onClick={handleInterruptClick} title="Interrupt AI Speaking">
          <Square size={11} fill="currentColor" />
          <span>Interrupt</span>
        </button>
      </div>

    </div>
  );
};
