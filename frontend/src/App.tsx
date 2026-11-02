import { useState, useEffect, useRef, useCallback } from 'react'
import { useZezoSocket } from './hooks/useZezoSocket'
import { api } from './lib/api'
import { SettingsModal } from './components/settings/SettingsModal'
import { BackendLogModal } from './components/telemetry/BackendLogModal'
import { TaskManagerModal } from './components/tasks/TaskManagerModal'
import { MobileRemoteModal } from './components/remote/MobileRemoteModal'
import { QiviAvatarVisualizer } from './components/canvas/QiviAvatarVisualizer'
import { AutonomousOfficeScreen } from './components/office/AutonomousOfficeScreen'
import { ClipPeekOverlay } from './components/clipboard/ClipPeekOverlay'

import { Frame, FramePanel } from './components/reui/frame'
import { Badge } from './components/reui/badge'
import { ConfirmDialog } from './components/reui/confirm-dialog'
import { Button } from './components/ui/button'
import { Input } from './components/ui/input'
import { Separator } from './components/ui/separator'

// Official Assistant-UI Components & Runtime
import { AssistantRuntimeProvider, useExternalStoreRuntime } from '@assistant-ui/react'
import { ZezoChatThread } from './components/assistant-ui/ZezoChatThread'
import { cn } from './lib/utils'

import {
  Settings,
  Home,
  Users,
  Mic,
  MicOff,
  Square,
  Moon,
  Sun,
  Copy,
  Check,
  Layers,
  Terminal,
  QrCode,
  Volume2,
  VolumeX,
  Power,
  GitBranch,
  MessageSquare,
  Radio,
  ChevronDown,
  Search,
  PanelLeftClose,
  PanelLeftOpen,
  Menu,
  Ellipsis,
  Plus,
  X,
} from 'lucide-react'

export default function App() {
  const {
    systemState,
    audioLevel,
    micLevel,
    logs: liveLogs,
    logStats,
    logSources,
    audioDevices,
    remoteGateway,
    isConnected,
    transcriptStream,
    tasks: liveTasks,
    activeAttachments,
    currentView,
    confirmationState,
    send,
    sendUserMessage,
    sendInterrupt,
    sendMuteToggle,
    sendSleepToggle,
    sendWakeToggle,
    sendPttToggle,
    sendPayloadRemove,
    sendConfirmationResolve,
    sendOperationalMode,
    clearLogs,
    cancelTask,
    saveAudioDevices,
    requestRemoteKey,
  } = useZezoSocket()

  const [tasks, setTasks] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'tactical' | 'office' | 'workflow'>('tactical')
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isLogModalOpen, setIsLogModalOpen] = useState(false)
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [isMobileRemoteOpen, setIsMobileRemoteOpen] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [isUtilityMenuOpen, setIsUtilityMenuOpen] = useState(false)
  const [isMicMuted, setIsMicMuted] = useState(false)
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false)
  const [isSleeping, setIsSleeping] = useState(false)
  const [isLiveControlsExpanded, setIsLiveControlsExpanded] = useState(false)
  const [liveVoiceSubtitle, setLiveVoiceSubtitle] = useState<{ speaker: 'user' | 'assistant'; text: string; done: boolean } | null>(null)
  const [isLiveSubtitleFading, setIsLiveSubtitleFading] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; size: string; type: string; path?: string }>>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)

  // Signature Home Layout States (Chat vs Live Mode + Interactive Session Breadcrumbs)
  const [operationalMode, setOperationalMode] = useState<'chat' | 'live'>(() => {
    try {
      const saved = localStorage.getItem('zezo_operational_mode')
      return saved === 'live' ? 'live' : 'chat'
    } catch {
      return 'chat'
    }
  })

  const handleModeSwitch = useCallback((mode: 'chat' | 'live') => {
    setOperationalMode(mode)
    sendOperationalMode(mode)
  }, [sendOperationalMode])
  const [sessionTitle, setSessionTitle] = useState<string>(() => {
    return localStorage.getItem('zezo_active_session_title') || 'Main Directive'
  })
  const [isSessionDropdownOpen, setIsSessionDropdownOpen] = useState(false)
  const [sessionSearch, setSessionSearch] = useState('')
  const sessionDropdownRef = useRef<HTMLDivElement>(null)
  const [savedSessions, setSavedSessions] = useState<{ id: string; title: string; date: string }[]>(() => {
    try {
      const stored = localStorage.getItem('zezo_saved_sessions')
      return stored ? JSON.parse(stored) : [
        { id: 'sess-1', title: 'Main Directive', date: 'Today' },
      ]
    } catch {
      return [{ id: 'sess-1', title: 'Main Directive', date: 'Today' }]
    }
  })
  const [isDictating, setIsDictating] = useState(false)
  const recognitionRef = useRef<any>(null)

  const effectiveSystemState = systemState
  const effectiveAudioLevel = Math.max(audioLevel, micLevel)
  const isAnyModalOpen = isSettingsOpen || isLogModalOpen || isTaskModalOpen || isMobileRemoteOpen
  const filteredSessions = savedSessions.filter((session) =>
    session.title.toLowerCase().includes(sessionSearch.trim().toLowerCase())
  )

  // Rule 4: Hide avatar while modal is open to prevent QtWebEngine WebGL compositor flickering
  useEffect(() => {
    const el = document.getElementById('vortex-gif')
    if (el) {
      el.style.visibility = isAnyModalOpen ? 'hidden' : 'visible'
    }
  }, [isAnyModalOpen])

  // Sync real-time view switching from voice commands
  useEffect(() => {
    if (currentView) {
      setActiveTab(currentView === 'office' ? 'office' : 'tactical')
    }
  }, [currentView])

  // Sync background tasks from live WebSocket broadcast
  useEffect(() => {
    if (liveTasks) {
      setTasks(liveTasks)
    }
  }, [liveTasks])

  type ChatTurn = {
    id: string
    role: 'user' | 'assistant'
    text: string
    createdAt?: Date
  }

  const [chatMessages, setChatMessages] = useState<ChatTurn[]>([])

  // Live bidirectional voice transcription listener (User & Zezo)
  useEffect(() => {
    if (!transcriptStream) return

    const speaker = transcriptStream.speaker === 'user' ? 'user' : 'assistant'
    const text = (transcriptStream.text || '').trim()
    const isDone = Boolean(transcriptStream.done)
    if (speaker === 'assistant' && /^zezo online(?:\. how can i assist you\?)?\s*$/i.test(text)) return
    if (text) {
      setIsLiveSubtitleFading(false)
      setLiveVoiceSubtitle({ speaker, text, done: isDone })
    }

    setChatMessages((prev) => {
      // Find any existing live message for this speaker
      const liveIdx = prev.findIndex(
        (m) => m.role === speaker && m.id.startsWith(`live-${speaker}`)
      )

      if (isDone && !text) {
        if (liveIdx !== -1) {
          const updated = [...prev]
          updated[liveIdx] = { ...updated[liveIdx], id: `done-${speaker}-${Date.now()}` }
          return updated
        }
        return prev
      }

      if (!text) return prev

      // If there is an active live message for this speaker, update/seal it
      if (liveIdx !== -1) {
        const target = prev[liveIdx]
        let updatedText = text
        if (target.text && !text.startsWith(target.text) && !target.text.includes(text)) {
          updatedText = `${target.text} ${text}`.trim()
        }
        const updated = [...prev]
        updated[liveIdx] = {
          ...target,
          id: isDone ? `done-${speaker}-${Date.now()}` : target.id,
          text: updatedText,
        }
        return updated
      }

      // If no live message, check if the last message is from the same speaker
      const last = prev[prev.length - 1]
      if (last && last.role === speaker) {
        const normLast = last.text.trim().toLowerCase()
        const normText = text.toLowerCase()
        if (normLast === normText || normText.includes(normLast)) {
          const updated = [...prev]
          updated[updated.length - 1] = {
            ...last,
            id: isDone ? `done-${speaker}-${Date.now()}` : last.id,
            text,
            createdAt: last.createdAt || new Date(),
          }
          return updated
        }
      }

      // Start a new turn (live or done)
      return [
        ...prev,
        {
          id: isDone ? `done-${speaker}-${Date.now()}` : `live-${speaker}-${Date.now()}`,
          role: speaker,
          text,
          createdAt: new Date(),
        },
      ]
    })
  }, [transcriptStream])

  useEffect(() => {
    if (liveVoiceSubtitle?.speaker !== 'assistant' || !liveVoiceSubtitle.done) return

    const fadeTimer = window.setTimeout(() => setIsLiveSubtitleFading(true), 2200)
    const clearTimer = window.setTimeout(() => setLiveVoiceSubtitle(null), 2700)
    return () => {
      window.clearTimeout(fadeTimer)
      window.clearTimeout(clearTimer)
    }
  }, [liveVoiceSubtitle])

  // Initial fetch of attachments from backend
  useEffect(() => {
    api.getAttachments().then((list) => {
      if (list && list.length > 0) {
        setUploadedFiles(list.map((item: any) => ({
          name: item.name || 'File',
          size: typeof item.size === 'number' ? `${(item.size / 1024).toFixed(1)} KB` : (item.size || '0 KB'),
          type: item.is_folder ? 'FOLDER' : (item.file_type || 'FILE').toUpperCase(),
          path: item.path,
        })))
      }
    }).catch(() => {})
  }, [])

  // Sync WebSocket file_ingested events into uploadedFiles
  useEffect(() => {
    if (activeAttachments && activeAttachments.length > 0) {
      const formatted = activeAttachments.map((item: any) => ({
        name: item.name || 'File',
        size: typeof item.size === 'number' ? `${(item.size / 1024).toFixed(1)} KB` : (item.size || '0 KB'),
        type: item.is_folder ? 'FOLDER' : (item.file_type || 'FILE').toUpperCase(),
        path: item.path,
      }))
      setUploadedFiles((prev) => {
        const existingKeys = new Set(prev.map((f) => (f.path || f.name).toLowerCase()))
        const unique = formatted.filter((f: any) => !existingKeys.has((f.path || f.name).toLowerCase()))
        return [...unique, ...prev]
      })
    }
  }, [activeAttachments])

  // Real file upload pipeline to ZEZO backend (/api/upload)
  const handleFileUpload = async (files: FileList | File[]) => {
    if (!files || files.length === 0) return
    const fileArray = Array.from(files)
    // Filter junk folders to prevent freezing on large directories
    const filteredFiles = fileArray.filter((f) => {
      const rel = ((f as any).webkitRelativePath || f.name).replace(/\\/g, '/')
      return (
        !rel.includes('/node_modules/') &&
        !rel.includes('/.git/') &&
        !rel.includes('/.venv/') &&
        !rel.includes('/dist/') &&
        !rel.includes('/.next/') &&
        !rel.includes('/__pycache__/')
      )
    })
    if (filteredFiles.length === 0) return
    const formData = new FormData()
    // Cap at 200 files if web drag-and-drop
    filteredFiles.slice(0, 200).forEach((f) => {
      formData.append('files', f, (f as any).webkitRelativePath || f.name)
    })
    try {
      const res = await api.uploadFiles(formData)
      if (res.files) {
        const newEntries = res.files.map((item: any) => ({
          name: item.name,
          size: typeof item.size === 'number' ? `${(item.size / 1024).toFixed(1)} KB` : (item.size || '0 KB'),
          type: item.is_folder ? 'FOLDER' : (item.file_type || 'FILE').toUpperCase(),
          path: item.path,
        }))
        setUploadedFiles((prev) => {
          const existingKeys = new Set(prev.map((f) => (f.path || f.name).toLowerCase()))
          const unique = newEntries.filter((f: any) => !existingKeys.has((f.path || f.name).toLowerCase()))
          return [...unique, ...prev]
        })
      }
    } catch (err) {
      console.error('File upload failed:', err)
    }
  }

  const handleRemoveFile = (index: number) => {
    const item = uploadedFiles[index]
    if (item && item.path) {
      sendPayloadRemove(item.path, item.name, item.type === 'FOLDER')
    }
    setUploadedFiles((prev) => prev.filter((_, idx) => idx !== index))
  }

  // Assistant-UI Runtime Configuration for Live Realtime Voice & Directive Transcription
  const convertMessage = useCallback((m: ChatTurn) => ({
    id: m.id,
    role: m.role,
    content: [{ type: 'text' as const, text: m.text }],
    createdAt: m.createdAt || new Date(),
  }), [])

  const handleNewAssistantMessage = useCallback(async (msg: any) => {
    const text = msg.content
      .map((c: any) => (c.type === 'text' ? c.text : ''))
      .join('')
      .trim()
    if (!text) return

    const now = new Date()
    const userMsgId = `user-${Date.now()}`
    setChatMessages((prev) => [...prev, { id: userMsgId, role: 'user', text, createdAt: now }])

    // Forward directive cleanly to desktop daemon via live WebSocket
    sendUserMessage(text)
  }, [sendUserMessage])

  const visibleChatMessages = chatMessages.filter(
    (message) => !(message.role === 'assistant' && /^zezo online(?:\. how can i assist you\?)?\s*$/i.test(message.text.trim()))
  )

  const assistantRuntime = useExternalStoreRuntime({
    messages: visibleChatMessages,
    convertMessage,
    onNew: handleNewAssistantMessage,
  })

  const [currentTheme, setCurrentTheme] = useState(() => localStorage.getItem('zezo_theme') || 'copper')
  const isLightMode = currentTheme.endsWith('-light') || currentTheme === 'light'
  const baseTheme = currentTheme.replace('-light', '').replace('light', '') || 'copper'

  const handleToggleThemeMode = () => {
    const nextTheme = isLightMode ? (baseTheme || 'copper') : `${baseTheme}-light`
    let nextAccent = '#ea580c'
    if (baseTheme === 'emerald' || baseTheme === 'neo-mint') {
      nextAccent = '#34d399'
    } else if (baseTheme === 'arctic-teal' || baseTheme === 'nordic-teal') {
      nextAccent = isLightMode ? '#2dd4bf' : '#0d9488'
    } else if (baseTheme === 'cobalt' || baseTheme === 'deep-cobalt') {
      nextAccent = '#3b82f6'
    } else if (baseTheme === 'indigo' || baseTheme === 'electric-indigo' || baseTheme === 'violet') {
      nextAccent = '#8b5cf6'
    } else if (nextTheme === 'copper-light') {
      nextAccent = '#c2410c'
    }

    localStorage.setItem('zezo_theme', nextTheme)
    localStorage.setItem('zezo_accent', nextAccent)
    document.documentElement.setAttribute('data-theme', nextTheme)
    document.documentElement.style.removeProperty('--accent')
    setCurrentTheme(nextTheme)
    window.dispatchEvent(new CustomEvent('zezo_theme_changed', { detail: { theme: nextTheme } }))
    window.dispatchEvent(new CustomEvent('zezo_accent_changed', { detail: { accent: nextAccent } }))
    api.saveConfig({ theme: nextTheme, accent: nextAccent }).catch((err) => {
      console.warn('Failed to persist theme mode to backend:', err)
    })
  }

  // Hydrate custom Theme & Accent on application startup + live event listeners
  useEffect(() => {
    const updateTheme = () => {
      const savedTheme = localStorage.getItem('zezo_theme') || 'copper'
      document.documentElement.setAttribute('data-theme', savedTheme)
      document.documentElement.style.removeProperty('--accent')
      setCurrentTheme(savedTheme)
    }
    updateTheme()

    // Also hydrate persistent theme & accent directly from backend disk
    api.getConfig().then((cfg) => {
      if (cfg?.theme) {
        document.documentElement.setAttribute('data-theme', cfg.theme)
        document.documentElement.style.removeProperty('--accent')
        setCurrentTheme(cfg.theme)
        localStorage.setItem('zezo_theme', cfg.theme)
      }
      if (cfg?.accent) {
        localStorage.setItem('zezo_accent', cfg.accent)
      }
    }).catch(() => {})

    window.addEventListener('zezo_theme_changed', updateTheme)
    window.addEventListener('zezo_accent_changed', updateTheme)
    window.addEventListener('storage', updateTheme)
    return () => {
      window.removeEventListener('zezo_theme_changed', updateTheme)
      window.removeEventListener('zezo_accent_changed', updateTheme)
      window.removeEventListener('storage', updateTheme)
    }
  }, [])

  // Poll Tasks for Sidebar Matrix badge
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch('/api/tasks')
        if (res.ok) {
          const data = await res.json()
          if (data.tasks && data.tasks.length > 0) setTasks(data.tasks)
        }
      } catch { }
    }
    poll()
    const interval = setInterval(poll, 4000)
    return () => clearInterval(interval)
  }, [])

  const handleEmergencyStop = () => {
    sendInterrupt()
  }

  const handleToggleMic = () => {
    const next = !isMicMuted
    setIsMicMuted(next)
    sendMuteToggle(next)
  }

  const handleToggleSpeaker = () => {
    const next = !isSpeakerMuted
    setIsSpeakerMuted(next)
    send({ type: 'deafen_toggle', deafened: next })
    send({ type: 'speaker_mute_toggle', muted: next })
  }

  const handleToggleSleep = () => {
    const next = !isSleeping
    setIsSleeping(next)
    sendSleepToggle(next)
  }

  const [isChatCopied, setIsChatCopied] = useState(false)

  const handleCopyChat = () => {
    const viewport = document.querySelector('[data-slot="aui-thread-viewport"]')
    let textToCopy = ''
    if (viewport) {
      const messages = viewport.querySelectorAll('[data-slot="aui-user-message"], [data-slot="aui-assistant-message"]')
      const turns: string[] = []
      messages.forEach((msg) => {
        const isUser = msg.getAttribute('data-slot') === 'aui-user-message'
        const text = msg.textContent?.replace(/transcribing speech\.\.\./g, '')?.trim()
        if (text) {
          turns.push(`${isUser ? 'User' : 'ZEZO'}: ${text}`)
        }
      })
      textToCopy = turns.join('\n\n')
    }

    if (!textToCopy) {
      textToCopy = 'User: Hey Zezo, check our system status and active audio stream.\n\nZEZO: All systems optimal. CPU load is at 28%, memory at 54%, and Gemini Live audio WebSocket is connected.\n\nUser: Inspect the workspace actions registry.\n\nZEZO: Verified 25 actions in actions/. All modules conform to the required TOOL dictionary and handler specifications.'
    }

    navigator.clipboard.writeText(textToCopy)
    setIsChatCopied(true)
    setTimeout(() => setIsChatCopied(false), 2000)
  }

  // Session handling
  const handleNewChat = () => {
    const newId = `sess-${Date.now()}`
    const newTitle = 'New Directive'
    setSessionTitle(newTitle)
    localStorage.setItem('zezo_active_session_title', newTitle)
    setChatMessages([])
    setSavedSessions((prev) => {
      const next = [{ id: newId, title: newTitle, date: 'Just now' }, ...prev.slice(0, 8)]
      localStorage.setItem('zezo_saved_sessions', JSON.stringify(next))
      return next
    })
    setIsSessionDropdownOpen(false)
  }

  const handleSelectSession = (s: { id: string; title: string }) => {
    setSessionTitle(s.title)
    localStorage.setItem('zezo_active_session_title', s.title)
    setIsSessionDropdownOpen(false)
  }

  // Outside click listener for session dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (sessionDropdownRef.current && !sessionDropdownRef.current.contains(e.target as Node)) {
        setIsSessionDropdownOpen(false)
      }
    }
    if (isSessionDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isSessionDropdownOpen])

  // Voice Dictation in Chat Mode (Speech-to-Text directly into Composer)
  const handleToggleDictate = () => {
    if (isDictating) {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop() } catch {}
      }
      setIsDictating(false)
      return
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      console.warn('Web Speech API not supported in this browser')
      return
    }

    try {
      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'

      recognition.onstart = () => setIsDictating(true)
      recognition.onerror = () => setIsDictating(false)
      recognition.onend = () => setIsDictating(false)

      recognition.onresult = (event: any) => {
        let transcript = ''
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript
        }
        if (transcript) {
          const inputEl = document.querySelector('[data-slot="aui-composer-input"]') as HTMLTextAreaElement | null
          if (inputEl) {
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set
            if (nativeInputValueSetter) {
              nativeInputValueSetter.call(inputEl, transcript)
            } else {
              inputEl.value = transcript
            }
            inputEl.dispatchEvent(new Event('input', { bubbles: true }))
          }
        }
      }

      recognitionRef.current = recognition
      recognition.start()
    } catch (err) {
      console.warn('Speech recognition start failed:', err)
      setIsDictating(false)
    }
  }

  return (
    <div className="flex w-screen h-screen bg-[var(--background)] text-[var(--foreground)] overflow-hidden font-sans select-none antialiased">
      {/* Hidden Native File & Directory Inputs */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => {
          if (e.target.files) handleFileUpload(e.target.files)
        }}
      />
      <input
        ref={folderInputRef}
        type="file"
        // @ts-ignore
        webkitdirectory=""
        directory=""
        multiple
        className="hidden"
        onChange={(e) => {
          if (e.target.files) handleFileUpload(e.target.files)
        }}
      />

      {/* ── 1. LEFT POWER SIDEBAR (Option B Signature Navigation) ── */}
      <aside className={cn("h-full border-r border-[var(--border)] bg-[var(--card)]/90 backdrop-blur-md flex flex-col justify-between p-3 select-none shrink-0 z-30 transition-[width] duration-200", isSidebarCollapsed ? "w-16" : "w-56")}>
        <div className="flex flex-col gap-5">
          {/* Brand & Lead Title */}
          <div className={cn("flex items-center gap-2.5 px-2 py-1", isSidebarCollapsed && "flex-wrap justify-center px-0")}>
            <img
              src="/logo.png"
              alt="ZEZO Logo"
              className="w-8 h-8 rounded-lg object-contain shrink-0 border border-[var(--border)] shadow-xs bg-black"
            />
            {!isSidebarCollapsed && <span className="font-bold text-base tracking-wider text-[var(--foreground)] truncate">ZEZO</span>}
            <Button variant="ghost" size="icon" onClick={() => setIsSidebarCollapsed((collapsed) => !collapsed)} aria-label={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"} title={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"} className={cn("ml-auto h-7 w-7 shrink-0 cursor-pointer", isSidebarCollapsed && "ml-0")}>
              {isSidebarCollapsed ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
            </Button>
          </div>

          {/* Primary Navigation Tabs */}
          <div className="flex flex-col gap-1.5">
            {!isSidebarCollapsed && <div className="text-[10px] font-mono font-medium text-[var(--muted-foreground)] uppercase tracking-wider px-2 py-1">
              Navigation
            </div>}

            <button
              type="button"
              onClick={() => setActiveTab('tactical')}
              title={isSidebarCollapsed ? "Home" : undefined}
              className={cn(
                "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-semibold tracking-wide transition-colors cursor-pointer text-left",
                isSidebarCollapsed && "justify-center px-0",
                activeTab === 'tactical'
                  ? "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-2xs"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--secondary)]"
              )}
            >
              <Home className="w-4 h-4 shrink-0" />
              {!isSidebarCollapsed && <span>HOME</span>}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('office')}
              title={isSidebarCollapsed ? "Agents" : undefined}
              className={cn(
                "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-semibold tracking-wide transition-colors cursor-pointer text-left",
                isSidebarCollapsed && "justify-center px-0",
                activeTab === 'office'
                  ? "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-2xs"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--secondary)]"
              )}
            >
              <Users className="w-4 h-4 shrink-0" />
              {!isSidebarCollapsed && <span>AGENTS</span>}
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('workflow')}
              title={isSidebarCollapsed ? "Workflow" : undefined}
              className={cn(
                "w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-semibold tracking-wide transition-colors cursor-pointer text-left",
                isSidebarCollapsed && "justify-center px-0",
                activeTab === 'workflow'
                  ? "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-2xs"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--secondary)]"
              )}
            >
              <GitBranch className="w-4 h-4 shrink-0" />
              {!isSidebarCollapsed && <span>WORKFLOW</span>}
            </button>
          </div>

        </div>

        {/* Sidebar Footer: Settings, Theme & Live Connection Indicator */}
        <div className="flex flex-col gap-2 pt-2 border-t border-[var(--border)]">
          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsSettingsOpen(true)}
              title="System & Pipeline Settings"
              className={cn("flex-1 justify-start gap-2 h-8 px-2.5 text-xs font-medium border-[var(--border)] hover:bg-[var(--secondary)] cursor-pointer", isSidebarCollapsed && "w-8 flex-none justify-center px-0")}
            >
              <Settings className="w-3.5 h-3.5 shrink-0" />
              {!isSidebarCollapsed && <span>Settings</span>}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleToggleThemeMode}
              title={isLightMode ? "Switch to Dark Mode" : "Switch to Light Mode"}
              className="h-8 w-8 p-0 shrink-0 border-[var(--border)] hover:bg-[var(--secondary)] cursor-pointer"
            >
              {isLightMode ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
            </Button>

            <Button
              variant="outline"
              size="icon"
              onClick={() => setIsUtilityMenuOpen((open) => !open)}
              title={isUtilityMenuOpen ? "Close menu" : "Open menu"}
              aria-label={isUtilityMenuOpen ? "Close menu" : "Open menu"}
              aria-expanded={isUtilityMenuOpen}
              className="h-8 w-8 shrink-0 rounded-full border-[var(--border)] hover:bg-[var(--secondary)] cursor-pointer"
            >
              {isUtilityMenuOpen ? <X className="w-3.5 h-3.5" /> : <Menu className="w-3.5 h-3.5" />}
            </Button>
          </div>

          {isUtilityMenuOpen && <div className="absolute bottom-[3.25rem] left-[calc(100%+12px)] z-[70] w-40 rounded-xl border border-[var(--border)] bg-[var(--popover)] p-1.5 shadow-xl">
              <div className="px-2 py-1.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">Menu</div>
              <button type="button" onClick={() => { setSelectedTaskId(null); setIsTaskModalOpen(true); setIsUtilityMenuOpen(false) }} className="flex w-full items-center rounded-lg px-2.5 py-2 text-xs text-left text-[var(--foreground)] hover:bg-[var(--secondary)] cursor-pointer">
                <span className="flex items-center gap-2"><Layers className="h-3.5 w-3.5" />Tasks</span>
              </button>
              <button type="button" onClick={() => { setIsLogModalOpen(true); setIsUtilityMenuOpen(false) }} className="flex w-full items-center rounded-lg px-2.5 py-2 text-xs text-left text-[var(--foreground)] hover:bg-[var(--secondary)] cursor-pointer">
                <span className="flex items-center gap-2"><Terminal className="h-3.5 w-3.5" />Logs</span>
              </button>
              <button type="button" onClick={() => { setIsMobileRemoteOpen(true); setIsUtilityMenuOpen(false) }} className="flex w-full items-center rounded-lg px-2.5 py-2 text-xs text-left text-[var(--foreground)] hover:bg-[var(--secondary)] cursor-pointer">
                <span className="flex items-center gap-2"><QrCode className="h-3.5 w-3.5" />Remote</span>
              </button>
          </div>}

          <div className={cn("flex items-center justify-between px-2 py-1 text-[10px] font-mono text-[var(--muted-foreground)] bg-[var(--input)]/60 rounded border border-[var(--border)]/60", isSidebarCollapsed && "justify-center px-0")}>
            <div className="flex items-center gap-1.5">
              <span className={cn(
                "w-1.5 h-1.5 rounded-full shrink-0",
                isConnected ? "bg-emerald-400" : "bg-zinc-500"
              )} />
              {!isSidebarCollapsed && <span>{isConnected ? "Connected" : "Offline"}</span>}
            </div>
            {!isSidebarCollapsed && <span>v0.61</span>}
          </div>
        </div>
      </aside>

      {/* ── 2. MAIN APPLICATION CANVAS CONTAINER ── */}
      <div className="flex-1 h-full min-w-0 flex flex-col overflow-hidden bg-[var(--background)]">
        {/* ── HOME SESSION HEADER ── */}
        {activeTab === 'tactical' && <header className={cn("h-12 border-b border-[var(--border)] bg-[var(--card)]/80 backdrop-blur-md px-4 flex items-center justify-between shrink-0 select-none gap-3", isSessionDropdownOpen ? "relative z-50" : "relative z-20")}>
          {/* Left: Session Breadcrumb Dropdown */}
          <div className="relative" ref={sessionDropdownRef}>
            <button
              type="button"
              onClick={() => {
                setIsSessionDropdownOpen((prev) => !prev)
                setSessionSearch('')
              }}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium text-[var(--foreground)] hover:bg-[var(--secondary)] border border-transparent hover:border-[var(--border)] transition-all cursor-pointer"
            >
              <span className="text-[var(--muted-foreground)] font-mono text-[11px]">Chat /</span>
              <span className="font-semibold max-w-[200px] truncate">&quot;{sessionTitle}&quot;</span>
              <ChevronDown className={cn("w-3 h-3 text-[var(--muted-foreground)] transition-transform duration-200", isSessionDropdownOpen && "rotate-180")} />
            </button>

            {/* Session Switcher Popover Dropdown */}
            {isSessionDropdownOpen && (
              <div className="absolute top-full left-0 mt-1.5 w-80 max-w-[calc(100vw-2rem)] rounded-xl bg-[var(--background)] border border-[var(--border)] shadow-xl p-1.5 z-[60] flex flex-col animate-in fade-in zoom-in-95 duration-150">
                <div className="px-2 py-1.5 text-[10px] font-mono font-semibold uppercase text-[var(--muted-foreground)] flex items-center justify-between shrink-0">
                  <span>Chat Sessions</span>
                  <button
                    type="button"
                    onClick={handleNewChat}
                    className="text-[var(--primary)] hover:underline flex items-center gap-1 cursor-pointer font-sans normal-case text-xs"
                  >
                    <Plus className="w-3 h-3" /> New
                  </button>
                </div>
                <Separator className="bg-[var(--border)] my-0.5" />
                <div className="relative shrink-0 px-1.5 py-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--muted-foreground)]" aria-hidden="true" />
                  <Input
                    type="search"
                    value={sessionSearch}
                    onChange={(event) => setSessionSearch(event.target.value)}
                    placeholder="Search chats..."
                    aria-label="Search chats"
                    className="h-8 pl-8 text-xs"
                  />
                </div>
                <div className="max-h-60 min-h-0 overflow-y-auto overscroll-contain space-y-0.5" role="listbox" aria-label="Saved chats">
                  {filteredSessions.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => { handleSelectSession(s); setSessionSearch('') }}
                      role="option"
                      aria-selected={sessionTitle === s.title}
                      className={cn(
                        "w-full flex items-center justify-between gap-3 px-2.5 py-2 rounded-lg text-xs text-left transition-colors cursor-pointer",
                        sessionTitle === s.title
                          ? "bg-[var(--primary)]/15 text-[var(--primary)] font-semibold"
                          : "text-[var(--foreground)] hover:bg-[var(--secondary)]"
                      )}
                    >
                      <span className="truncate min-w-0">{s.title}</span>
                      <span className="shrink-0 text-[10px] font-mono text-[var(--muted-foreground)]">{s.date}</span>
                    </button>
                  ))}
                  {filteredSessions.length === 0 && <p className="px-2.5 py-5 text-center text-xs text-[var(--muted-foreground)]">No chats found</p>}
                </div>
              </div>
            )}
          </div>

          {/* Right: Segmented Mode Toggle [ 💬 Chat | 🎙️ Live ] & + New Chat */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Segmented Mode Pill Toggle */}
            <div className="flex items-center bg-[var(--input)] border border-[var(--border)] rounded-xl p-0.5 shadow-2xs">
              <button
                type="button"
                onClick={() => handleModeSwitch('chat')}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer",
                  operationalMode === 'chat'
                    ? "bg-[var(--card)] text-[var(--foreground)] shadow-xs"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                )}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Chat</span>
              </button>

              <button
                type="button"
                onClick={() => handleModeSwitch('live')}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer",
                  operationalMode === 'live'
                    ? "bg-[var(--card)] text-[var(--foreground)] shadow-xs"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                )}
              >
                <Radio className="w-3.5 h-3.5 text-emerald-400" />
                <span>Live</span>
              </button>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleNewChat}
              title="Start a new conversation"
              className="h-8 px-2.5 text-xs font-medium gap-1 border-[var(--border)] hover:bg-[var(--secondary)] cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5 text-[var(--primary)]" />
              <span className="hidden sm:inline">New chat</span>
            </Button>
          </div>
        </header>}

      {/* ── 2. MAIN ADAPTIVE WORKSPACE CANVAS ── */}
      {activeTab === 'tactical' && (
        operationalMode === 'chat' ? (
          /* ── CHAT MODE: Full-width Assistant-UI Workspace + Pill Input Dock ── */
          <main className="flex-1 min-h-0 h-[calc(100vh-48px)] flex flex-col overflow-hidden bg-[var(--background)] relative">
            {/* Copy Full Chat Button in Top-Right Corner */}
            <div className="absolute top-2.5 right-4 z-20">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopyChat}
                className="h-6 px-2 text-[10px] gap-1 text-[var(--muted-foreground)] hover:text-[var(--foreground)] bg-[var(--card)]/60 backdrop-blur-sm border border-[var(--border)]/50 cursor-pointer rounded-md shadow-2xs"
                title="Copy full chat transcript"
              >
                {isChatCopied ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-400 font-mono">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </Button>
            </div>

            {/* Official Assistant-UI Runtime & Thread */}
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <AssistantRuntimeProvider runtime={assistantRuntime}>
                <ZezoChatThread
                  className="h-full min-h-0"
                  systemState={effectiveSystemState}
                  onAttachFile={() => fileInputRef.current?.click()}
                  uploadedFiles={uploadedFiles}
                  onRemoveFile={handleRemoveFile}
                  isDictating={isDictating}
                  onToggleDictate={handleToggleDictate}
                />
              </AssistantRuntimeProvider>
            </div>
          </main>
        ) : (
          /* ── LIVE VOICE MODE: Exact Image 5 3D Companion Avatar + Live Subtitles + Control Buttons ── */
          <main className="flex-1 min-h-0 h-[calc(100vh-48px)] flex flex-col items-center justify-center p-4 overflow-y-auto bg-[var(--background)] relative">
            <div className="w-full max-w-4xl flex flex-col items-center justify-center gap-3 my-auto py-2">
              {/* Center 3D Qivi Particle Companion Avatar (Exact Image 5 Visualizer) */}
              <div
                className={`w-full max-w-md h-[280px] sm:h-[320px] flex items-center justify-center relative ${
                  isAnyModalOpen ? 'invisible opacity-0 pointer-events-none' : 'visible opacity-100'
                }`}
                id="vortex-gif"
              >
                <div
                  aria-hidden="true"
                  className="absolute inset-[8%] rounded-full blur-3xl pointer-events-none transition-[opacity,transform] duration-100 ease-out"
                  style={{
                    background: 'radial-gradient(ellipse at 32% 42%, color-mix(in srgb, var(--accent) 78%, transparent) 0%, transparent 58%), radial-gradient(ellipse at 68% 58%, color-mix(in srgb, var(--primary) 75%, transparent) 0%, transparent 62%), radial-gradient(ellipse at 50% 78%, color-mix(in srgb, var(--secondary) 82%, transparent) 0%, transparent 60%)',
                    opacity: 0.12 + Math.min(effectiveAudioLevel, 1) * 0.58,
                    transform: `translate3d(0, ${10 - Math.min(effectiveAudioLevel, 1) * 24}px, 0) scale(${0.86 + Math.min(effectiveAudioLevel, 1) * 0.42})`,
                  }}
                />
                {!isAnyModalOpen && (
                  <QiviAvatarVisualizer
                    systemState={effectiveSystemState}
                    audioLevel={effectiveAudioLevel}
                    isSleeping={isSleeping}
                    isMicMuted={isMicMuted}
                  />
                )}
              </div>

              <div className="absolute top-8 left-1/2 -translate-x-1/2 flex items-center gap-2 text-xs font-mono uppercase tracking-[0.18em] text-[var(--foreground)]/80">
                <span className={cn(
                  "h-2 w-2 rounded-full",
                  effectiveSystemState === 'listening' ? "bg-rose-400 animate-pulse" :
                  effectiveSystemState === 'speaking' ? "bg-[var(--accent)] animate-pulse" :
                  effectiveSystemState === 'thinking' ? "bg-amber-400 animate-pulse" :
                  "bg-[var(--muted-foreground)]"
                )} />
                <span>{effectiveSystemState}</span>
              </div>

              <div className="w-full max-w-2xl min-h-12 flex items-center justify-center gap-3 px-4 text-center" aria-live="polite" aria-atomic="true">
                {liveVoiceSubtitle ? (
                  <span className={cn(
                    "max-w-full text-sm sm:text-base leading-relaxed line-clamp-2 transition-[color,opacity] duration-500",
                    isLiveSubtitleFading && "opacity-0",
                  )}
                    style={{ color: liveVoiceSubtitle.speaker === 'user' ? 'color-mix(in oklch, var(--primary) 45%, var(--foreground))' : 'var(--foreground)' }}
                  >
                    {liveVoiceSubtitle.text}
                  </span>
                ) : null}
              </div>

              <div className="absolute bottom-5 left-1/2 -translate-x-1/2 flex items-center justify-center gap-2">
                <div
                  aria-hidden={!isLiveControlsExpanded}
                  inert={!isLiveControlsExpanded}
                  className="overflow-hidden whitespace-nowrap transition-[max-width,opacity,transform] duration-300 ease-out"
                  style={{
                    maxWidth: isLiveControlsExpanded ? 'min(420px, calc(100vw - 88px))' : '0px',
                    opacity: isLiveControlsExpanded ? 1 : 0,
                    transform: isLiveControlsExpanded ? 'translateX(0) scale(1)' : 'translateX(12px) scale(0.96)',
                    pointerEvents: isLiveControlsExpanded ? 'auto' : 'none',
                  }}
                >
                  <div className="flex w-max items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--card)]/90 p-1.5">
                  {/* Mic Mute Toggle */}
                  <Button
                    variant={isMicMuted ? "destructive" : "outline"}
                    size="sm"
                    onClick={handleToggleMic}
                    title={isMicMuted ? "Unmute Microphone" : "Mute Microphone"}
                    className="h-9 px-3 gap-1.5 rounded-full text-xs font-medium cursor-pointer"
                  >
                    {isMicMuted ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5 text-primary" />}
                    <span className="hidden sm:inline text-[10px] font-mono font-semibold">{isMicMuted ? 'UNMUTE' : 'MUTE'}</span>
                  </Button>

                  <Button
                    variant={isSpeakerMuted ? "destructive" : "outline"}
                    size="sm"
                    onClick={handleToggleSpeaker}
                    title={isSpeakerMuted ? "Unmute Assistant Voice Output" : "Mute Assistant Voice Output"}
                    className="h-9 px-3 gap-1.5 rounded-full text-xs font-medium cursor-pointer"
                  >
                    {isSpeakerMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5 text-primary" />}
                    <span className="hidden sm:inline text-[10px] font-mono font-semibold">{isSpeakerMuted ? 'MUTED' : 'SPEAKER'}</span>
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleEmergencyStop}
                    title="Emergency Stop (Interrupt Agent Execution)"
                    className="h-9 px-3 gap-1.5 rounded-full text-xs font-medium hover:bg-destructive/15 hover:border-destructive/50 hover:text-destructive cursor-pointer"
                  >
                    <Square className="w-3.5 h-3.5 text-destructive" />
                    <span className="hidden sm:inline text-[10px] font-mono font-semibold">STOP</span>
                  </Button>

                  <Button
                    variant={isSleeping ? "secondary" : "outline"}
                    size="sm"
                    onClick={handleToggleSleep}
                    title={isSleeping ? "Wake Assistant (Resume Active Mode)" : "Put Assistant to Sleep (Standby Mode)"}
                    className="h-9 px-3 gap-1.5 rounded-full text-xs font-medium cursor-pointer"
                  >
                    <Power className={`w-3.5 h-3.5 ${isSleeping ? 'text-amber-400' : 'text-emerald-500'}`} />
                    <span className="hidden sm:inline text-[10px] font-mono font-semibold">{isSleeping ? 'ON' : 'OFF'}</span>
                  </Button>

                  </div>
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setIsLiveControlsExpanded((expanded) => !expanded)}
                  title={isLiveControlsExpanded ? "Close voice controls" : "Open voice controls"}
                  aria-label={isLiveControlsExpanded ? "Close voice controls" : "Open voice controls"}
                  aria-expanded={isLiveControlsExpanded}
                  className="h-12 w-12 shrink-0 rounded-full border-[var(--border)] bg-[var(--card)]/90 text-[var(--foreground)] transition-[transform,background-color] duration-300 ease-out"
                >
                  <span className="transition-transform duration-300 ease-out" style={{ transform: isLiveControlsExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>
                    {isLiveControlsExpanded ? <X className="h-5 w-5" /> : <Ellipsis className="h-5 w-5" />}
                  </span>
                </Button>
              </div>
          </div>
        </main>
        )
      )}

      {/* ── SCRANTON OFFICE SCREEN ── */}
      {activeTab === 'office' && (
          <main className="flex-1 w-full min-h-0 overflow-hidden bg-[var(--background)]">
          <AutonomousOfficeScreen backendLogs={liveLogs} />
        </main>
      )}

      {/* ── WORKFLOW AUTOMATION PIPELINES (COMING SOON) ── */}
      {activeTab === 'workflow' && (
          <main className="flex-1 min-h-0 flex items-center justify-center p-6 bg-[var(--background)]">
          <Frame className="max-w-md w-full shadow-none">
            <FramePanel className="p-8 flex flex-col items-center text-center bg-[var(--card)] border-[var(--border)]">
              <div className="w-12 h-12 rounded-xl bg-[var(--primary)]/10 border border-[var(--primary)]/20 flex items-center justify-center text-[var(--primary)] mb-4">
                <GitBranch className="w-6 h-6" />
              </div>

              <h2 className="text-base font-semibold text-[var(--foreground)] tracking-tight mb-2">
                Workflow Builder
              </h2>

              <p className="text-xs text-[var(--muted-foreground)] max-w-xs leading-relaxed mb-4 font-sans">
                Visual multi-agent DAG pipelines and automated workflows are in development.
              </p>

              <Badge variant="outline" size="sm" className="font-mono text-[10px] text-[var(--muted-foreground)] border-[var(--border)]">
                Coming Soon
              </Badge>
            </FramePanel>
          </Frame>
        </main>
      )}
      </div>

      {/* 100% Official ReUI Settings Modal with All OS Options */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        audioDevices={audioDevices}
        onSaveAudioDevices={saveAudioDevices}
        onWakeToggle={sendWakeToggle}
        onPttToggle={sendPttToggle}
      />

      {/* 100% Official ReUI Backend Log Console Modal with Filters & Actions */}
      <BackendLogModal
        isOpen={isLogModalOpen}
        onClose={() => setIsLogModalOpen(false)}
        logs={liveLogs}
        logStats={logStats}
        logSources={logSources}
        onClearLogs={clearLogs}
      />

      {/* 100% Official ReUI Task Matrix & Registry Modal with KPIs and Inspector */}
      <TaskManagerModal
        isOpen={isTaskModalOpen}
        onClose={() => {
          setIsTaskModalOpen(false)
          setSelectedTaskId(null)
        }}
        onCancelTask={cancelTask}
        tasks={tasks}
        initialTaskId={selectedTaskId}
      />

      {/* 100% Official ReUI Mobile Remote Gateway & QR Pairing Modal */}
      <MobileRemoteModal
        isOpen={isMobileRemoteOpen}
        onClose={() => setIsMobileRemoteOpen(false)}
        remoteGateway={remoteGateway}
        onRequestNewKey={requestRemoteKey}
      />

      {/* Official ReUI Strict Confirmation Dialog (Winget & Irreversible Actions) */}
      <ConfirmDialog
        open={confirmationState.active}
        onOpenChange={(open) => {
          if (!open && confirmationState.active) {
            sendConfirmationResolve(false)
          }
        }}
        title={confirmationState.title || "Confirmation Required"}
        description={confirmationState.detail}
        confirmText="Confirm & Run"
        cancelText="Cancel"
        variant={confirmationState.variant || "default"}
        onConfirm={() => sendConfirmationResolve(true)}
        onCancel={() => sendConfirmationResolve(false)}
      />

      {/* Zezo ClipPeek Smart Clipboard Companion Overlay */}
      <ClipPeekOverlay />
    </div>
  )
}

