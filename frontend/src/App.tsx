import { useState, useEffect, useRef, useCallback } from 'react'
import { useZezoSocket } from './hooks/useZezoSocket'
import type { ZezoTelemetry } from './types/zezo'
import { api } from './lib/api'
import { SettingsModal } from './components/settings/SettingsModal'
import { BackendLogModal } from './components/telemetry/BackendLogModal'
import { TaskManagerModal } from './components/tasks/TaskManagerModal'
import { MobileRemoteModal } from './components/remote/MobileRemoteModal'
import { QiviAvatarVisualizer } from './components/canvas/QiviAvatarVisualizer'
import { AutonomousOfficeScreen } from './components/office/AutonomousOfficeScreen'
import { ClipPeekOverlay } from './components/clipboard/ClipPeekOverlay'

import { Frame, FramePanel, FrameHeader, FrameTitle } from './components/reui/frame'
import { Badge } from './components/reui/badge'
import { ConfirmDialog } from './components/reui/confirm-dialog'
import { Button } from './components/ui/button'
import { Tabs, TabsList, TabsTrigger } from './components/ui/tabs'
import { Progress } from './components/ui/progress'
import { ScrollArea } from './components/ui/scroll-area'
import { Separator } from './components/ui/separator'

// Official Assistant-UI Components & Runtime
import { AssistantRuntimeProvider, useExternalStoreRuntime } from '@assistant-ui/react'
import { ZezoChatThread } from './components/assistant-ui/ZezoChatThread'
import { cn } from './lib/utils'

import {
  Settings,
  Home,
  Grid,
  Users,
  Mic,
  MicOff,
  Square,
  Moon,
  Sun,
  Copy,
  Check,
  Trash2,
  FolderOpen,
  FileUp,
  FileCode,
  X,
  Cpu,
  HardDrive,
  Activity,
  Wifi,
  Sparkles,
  Layers,
  Terminal,
  QrCode,
  Volume2,
  VolumeX,
  Power,
  Loader2,
  CheckCircle2,
  Clock,
  GitBranch,
  AlertCircle,
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
    canvasContent: liveCanvas,
    telemetry: liveTelemetry,
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
    sendPayloadClear,
    sendConfirmationResolve,
    clearLogs,
    cancelTask,
    saveAudioDevices,
    requestRemoteKey,
  } = useZezoSocket()

  const [telemetry, setTelemetry] = useState<ZezoTelemetry>({
    cpu_percent: 0,
    ram_percent: 0,
    gpu_percent: 0,
  })
  const [tasks, setTasks] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'tactical' | 'office' | 'workflow'>('tactical')
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isLogModalOpen, setIsLogModalOpen] = useState(false)
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false)
  const [isMobileRemoteOpen, setIsMobileRemoteOpen] = useState(false)
  const [canvasContent, setCanvasContent] = useState<string>('')
  const [isMicMuted, setIsMicMuted] = useState(false)
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false)
  const [isSleeping, setIsSleeping] = useState(false)
  const [canvasHeight, setCanvasHeight] = useState<number>(170)
  const [isDraggingCanvas, setIsDraggingCanvas] = useState(false)
  const dragStartRef = useRef<{ startY: number; startHeight: number } | null>(null)
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; size: string; type: string; path?: string }>>([])
  const [isDraggingOver, setIsDraggingOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)

  const effectiveSystemState = systemState
  const effectiveAudioLevel = audioLevel || micLevel
  const isAnyModalOpen = isSettingsOpen || isLogModalOpen || isTaskModalOpen || isMobileRemoteOpen

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

  // Sync real-time canvas output from autonomous agent executions
  useEffect(() => {
    if (liveCanvas?.text) {
      setCanvasContent(liveCanvas.text)
    }
  }, [liveCanvas])

  // Sync real-time machine telemetry from live WebSocket broadcast
  useEffect(() => {
    if (isConnected) {
      setTelemetry({
        cpu_percent: liveTelemetry.cpu || 0,
        ram_percent: liveTelemetry.mem || 0,
        gpu_percent: liveTelemetry.gpu || 0,
      })
    }
  }, [liveTelemetry, isConnected])

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

  const [chatMessages, setChatMessages] = useState<ChatTurn[]>([
    {
      id: 'msg-welcome',
      role: 'assistant',
      text: 'ZEZO online.',
      createdAt: new Date(),
    },
  ])

  // Live bidirectional voice transcription listener (User & Zezo)
  useEffect(() => {
    if (!transcriptStream) return

    const speaker = transcriptStream.speaker === 'user' ? 'user' : 'assistant'
    const text = (transcriptStream.text || '').trim()
    const isDone = Boolean(transcriptStream.done)

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

  // Native folder picker that avoids byte upload & freeze
  const handleChooseFolderClick = async () => {
    try {
      const res = await api.pickWorkspaceFolder()
      if (res && res.status === 'success' && res.folder) {
        const item = res.folder
        const newEntry = {
          name: item.name,
          size: typeof item.size === 'number' ? `${(item.size / 1024).toFixed(1)} KB` : (item.size || '0 KB'),
          type: 'FOLDER' as const,
          path: item.path,
        }
        setUploadedFiles((prev) => {
          const existingKeys = new Set(prev.map((f) => (f.path || f.name).toLowerCase()))
          if (existingKeys.has((newEntry.path || newEntry.name).toLowerCase())) return prev
          return [newEntry, ...prev]
        })
        return
      }
      if (res && (res.status === 'canceled' || res.cancelled)) {
        return
      }
    } catch (err) {
      console.warn('Native folder picker fallback to web input:', err)
    }
    folderInputRef.current?.click()
  }

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

  const handleClearAllFiles = () => {
    sendPayloadClear()
    setUploadedFiles([])
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

  const assistantRuntime = useExternalStoreRuntime({
    messages: chatMessages,
    convertMessage,
    onNew: handleNewAssistantMessage,
  })

  // Drag-to-resize canvas height (Buttery-smooth 60-120fps with absolute coordinate deltas)
  useEffect(() => {
    if (!isDraggingCanvas) return

    // Prevent text selection and lock cursor during rapid drag sweeps
    const originalUserSelect = document.body.style.userSelect
    const originalCursor = document.body.style.cursor
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'row-resize'

    const handleMouseMove = (e: MouseEvent) => {
      if (!dragStartRef.current) return
      // As mouse moves up (smaller clientY), canvas height increases
      const deltaY = dragStartRef.current.startY - e.clientY
      const targetHeight = dragStartRef.current.startHeight + deltaY
      setCanvasHeight(Math.min(600, Math.max(120, targetHeight)))
    }

    const handleMouseUp = () => {
      setIsDraggingCanvas(false)
      dragStartRef.current = null
    }

    window.addEventListener('mousemove', handleMouseMove, { passive: true })
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.body.style.userSelect = originalUserSelect
      document.body.style.cursor = originalCursor
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDraggingCanvas])

  // Real-time Clock removed per user request

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

  // Poll Telemetry & Tasks (preserves design preview if backend is not running)
  useEffect(() => {
    const poll = async () => {
      try {
        const status = await api.getSystemStatus()
        if (status && (status.cpu_percent || status.ram_percent)) setTelemetry(status)
      } catch { }
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
    setCanvasContent((prev) => prev + '\n\n// [HALTED] Execution interrupted by user directive.')
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



  return (
    <div className="flex flex-col w-screen h-screen bg-[var(--background)] text-[var(--foreground)] overflow-hidden font-sans select-none antialiased">
      {/* ── 1. ReUI Top Application Shell Bar ── */}
      <header className="h-12 border-b border-[var(--border)] bg-[var(--card)]/90 backdrop-blur-md px-2 sm:px-4 flex items-center justify-between z-40 shrink-0 select-none gap-1 sm:gap-2">
        {/* Left: Section Actions */}
        <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSettingsOpen(true)}
            title="System & Pipeline Settings"
            className="h-8 w-8 p-0 shrink-0"
          >
            <Settings className="w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsLogModalOpen(true)}
            title="Backend Log Console (Ctrl+L)"
            className="h-8 w-8 p-0 shrink-0 hidden sm:inline-flex"
          >
            <Terminal className="w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsTaskModalOpen(true)}
            title="Task Matrix & Registry"
            className="h-8 w-8 p-0 shrink-0 hidden sm:inline-flex"
          >
            <Layers className="w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsMobileRemoteOpen(true)}
            title="Mobile Remote Control & QR Pairing"
            className="h-8 w-8 p-0 shrink-0 hidden sm:inline-flex"
          >
            <QrCode className="w-4 h-4" />
          </Button>

          <Separator orientation="vertical" className="h-4 mx-0.5 sm:mx-1 bg-[var(--border)] hidden sm:block" />

          {/* 100% Official ReUI Tabs Component */}
          <Tabs
            value={activeTab}
            onValueChange={(val) => setActiveTab(val as 'tactical' | 'office' | 'workflow')}
          >
            <TabsList className="h-8 p-0.5 bg-[var(--input)]/80 border border-[var(--border)] shadow-2xs">
              <TabsTrigger
                value="tactical"
                className="h-7 px-2.5 sm:px-3 text-xs font-semibold tracking-wider gap-1 sm:gap-1.5 data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--primary-foreground)]"
                title="Tactical Dashboard & Realtime Telemetry"
              >
                <Home className="w-3.5 h-3.5" />
                <span className="text-[11px] sm:text-xs">HOME</span>
              </TabsTrigger>

              <TabsTrigger
                value="office"
                className="h-7 px-2.5 sm:px-3 text-xs font-semibold tracking-wider gap-1 sm:gap-1.5 data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--primary-foreground)]"
                title="Autonomous Agents & Office Fleet"
              >
                <Users className="w-3.5 h-3.5" />
                <span className="text-[11px] sm:text-xs">AGENTS</span>
              </TabsTrigger>

              <TabsTrigger
                value="workflow"
                className="h-7 px-2.5 sm:px-3 text-xs font-semibold tracking-wider gap-1 sm:gap-1.5 data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--primary-foreground)]"
                title="Workflow Automation & Pipelines"
              >
                <GitBranch className="w-3.5 h-3.5" />
                <span className="text-[11px] sm:text-xs">WORKFLOW</span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>


        {/* Right: Quick Light/Dark Toggle & Real-time Telemetry & Clock */}
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          <div className="flex items-center bg-[var(--input)] border border-[var(--border)] rounded-xl p-0.5">
            <button
              type="button"
              onClick={handleToggleThemeMode}
              className={cn(
                "flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer",
                isLightMode
                  ? "bg-[var(--card)] text-[var(--foreground)] font-semibold"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              )}
              title="Light Mode"
            >
              <Sun className="w-3.5 h-3.5 text-[var(--foreground)]" />
              <span className="hidden sm:inline">Light</span>
            </button>
            <button
              type="button"
              onClick={handleToggleThemeMode}
              className={cn(
                "flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer",
                !isLightMode
                  ? "bg-[var(--card)] text-[var(--foreground)] font-semibold"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              )}
              title="Dark Mode"
            >
              <Moon className="w-3.5 h-3.5 text-[var(--foreground)]" />
              <span className="hidden sm:inline">Dark</span>
            </button>
          </div>
        </div>
      </header>

      {/* ── 2. TACTICAL DASHBOARD VIEW (Desktop 3-Column Layout Preserved Uniformly) ── */}
      {activeTab === 'tactical' && (
        <main className="flex-1 min-h-0 h-[calc(100vh-48px)] max-h-[calc(100vh-48px)] grid grid-cols-[clamp(260px,22vw,285px)_1fr_clamp(300px,26vw,345px)] gap-2 p-2 overflow-hidden bg-[var(--background)]">

          {/* ── LEFT PANEL: Telemetry & Task Queue ── */}
          <aside className="flex flex-col gap-2 min-w-0 h-full min-h-0 overflow-hidden order-1">
            {/* System Frame */}
            <Frame spacing="xs" className="shrink-0">
              <FramePanel className="p-3">
                <FrameHeader className="p-0 pb-2.5">
                  <div className="flex items-center justify-between">
                    <FrameTitle className="text-[11px] font-semibold text-[var(--foreground)]">System</FrameTitle>
                    <Badge variant={isConnected ? "success" : "secondary"} size="xs">
                      {isConnected ? "LIVE" : "DISCONNECTED"}
                    </Badge>
                  </div>
                </FrameHeader>

                <div className="grid grid-cols-2 gap-2 mt-1">
                  {/* CPU */}
                  <div className="p-2.5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/60 border border-[var(--border)] shadow-2xs flex flex-col justify-between">
                    <div className="flex items-center justify-between text-[10px] text-[var(--muted-foreground)] font-mono">
                      <span>CPU LOAD</span>
                      <Cpu className="w-3 h-3 text-[var(--muted-foreground)]" />
                    </div>
                    <div className="text-base font-semibold text-[var(--foreground)] my-1 font-mono truncate">
                      {Math.round(telemetry.cpu_percent)}%
                    </div>
                    <Progress value={telemetry.cpu_percent} />
                  </div>

                  {/* RAM */}
                  <div className="p-2.5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/60 border border-[var(--border)] shadow-2xs flex flex-col justify-between">
                    <div className="flex items-center justify-between text-[10px] text-[var(--muted-foreground)] font-mono">
                      <span>RAM USAGE</span>
                      <HardDrive className="w-3 h-3 text-[var(--muted-foreground)]" />
                    </div>
                    <div className="text-base font-semibold text-[var(--foreground)] my-1 font-mono truncate">
                      {Math.round(telemetry.ram_percent)}%
                    </div>
                    <Progress value={telemetry.ram_percent} />
                  </div>

                  {/* GPU */}
                  <div className="p-2.5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/60 border border-[var(--border)] shadow-2xs flex flex-col justify-between">
                    <div className="flex items-center justify-between text-[10px] text-[var(--muted-foreground)] font-mono">
                      <span>GPU LOAD</span>
                      <Activity className="w-3 h-3 text-[var(--muted-foreground)]" />
                    </div>
                    <div className="text-base font-semibold text-[var(--foreground)] my-1 font-mono truncate">
                      {telemetry.gpu_percent !== undefined ? `${Math.round(telemetry.gpu_percent)}%` : '0%'}
                    </div>
                    <Progress value={telemetry.gpu_percent || 0} />
                  </div>

                  {/* Network */}
                  <div className="p-2.5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/60 border border-[var(--border)] shadow-2xs flex flex-col justify-between">
                    <div className="flex items-center justify-between text-[10px] text-[var(--muted-foreground)] font-mono">
                      <span>NETWORK</span>
                      <Wifi className="w-3 h-3 text-[var(--muted-foreground)]" />
                    </div>
                    <div className="text-base font-semibold text-[var(--foreground)] my-1 font-mono truncate">
                      {!isConnected
                        ? 'OFFLINE'
                        : liveTelemetry.net >= 1.0
                          ? `${liveTelemetry.net.toFixed(1)} MB/s`
                          : liveTelemetry.net > 0.001
                            ? `${Math.round(liveTelemetry.net * 1024)} KB/s`
                            : 'ONLINE'}
                    </div>
                    <Progress
                      value={
                        !isConnected
                          ? 0
                          : liveTelemetry.net > 0
                            ? Math.min(100, Math.max(12, Math.round(liveTelemetry.net * 20)))
                            : 100
                      }
                    />
                  </div>
                </div>
              </FramePanel>
            </Frame>

            {/* Tasks Frame */}
            <Frame spacing="xs" className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <FramePanel className="p-3 flex flex-col h-full min-h-0 overflow-hidden">
                <FrameHeader className="p-0 pb-2 shrink-0">
                  <div className="flex items-center justify-between">
                    <FrameTitle className="text-[11px] font-semibold text-[var(--foreground)]">Tasks</FrameTitle>
                    {(() => {
                      // Filter out child tasks (subtasks) for display in main list
                      const parentTasks = tasks.filter((t) => !t.parent_id)
                      const activeCount = parentTasks.filter((t) => {
                        const s = (t.status || '').toUpperCase()
                        return s === 'RUNNING' || s === 'IN_PROGRESS'
                      }).length
                      return (
                        <Badge
                          variant={activeCount > 0 ? "running" : parentTasks.length > 0 ? "success" : "secondary"}
                          size="xs"
                        >
                          {activeCount > 0 ? `${activeCount} ACTIVE` : parentTasks.length > 0 ? 'ALL DONE' : '0 ACTIVE'}
                        </Badge>
                      )
                    })()}
                  </div>
                </FrameHeader>

                <ScrollArea className="flex-1">
                  {tasks.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center text-[var(--muted-foreground)] py-12">
                      <Grid className="w-8 h-8 text-[var(--muted-foreground)] opacity-30 mb-2" />
                      <div className="text-xs font-semibold text-[var(--foreground)]">No Active Tasks</div>
                      <div className="text-[10px] font-mono text-[var(--muted-foreground)] mt-1 max-w-[210px] leading-relaxed">
                        Tasks dispatched via voice or prompt will appear here.
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2 pr-1.5 min-w-0">
                      {/* Filter out child tasks (subtasks) - they appear nested in TaskManagerModal */}
                      {tasks.filter((t) => !t.parent_id).map((t, idx) => {
                        const status = (t.status || 'QUEUED').toUpperCase()
                        const isRunning = status === 'IN_PROGRESS' || status === 'RUNNING'
                        const isDone = status === 'COMPLETED' || status === 'SUCCESS' || status === 'DONE'
                        const isCancelled = status === 'CANCELLED'
                        const isFailed = status === 'FAILED'

                        const badgeVariant = isRunning
                          ? 'running'
                          : isDone
                            ? 'success'
                            : isCancelled || isFailed
                              ? 'destructive'
                              : 'queued'

                        const displayTitle = t.prompt || t.group_title || t.params?.taskTitle || t.params?.task || t.params?.target || t.message || t.id

                        return (
                          <div
                            key={idx}
                            className="p-2.5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/60 border border-[var(--border)] hover:border-[var(--primary)] transition-all flex flex-col gap-1.5 shadow-2xs min-w-0 w-full overflow-hidden"
                          >
                            {/* Task Description */}
                            <div className="font-medium text-[var(--foreground)] text-xs leading-snug break-all min-w-0">
                              {displayTitle}
                            </div>
                            {t.message && t.message !== displayTitle && (
                              <div className="text-[11px] text-[var(--muted-foreground)] font-mono leading-tight truncate min-w-0">
                                {t.message}
                              </div>
                            )}

                            {/* Status Tag Badge + Progress Details */}
                            <div className="flex items-center justify-between gap-1.5 pt-1 border-t border-[var(--border)]/40 min-w-0">
                              <div className="flex items-center gap-1.5 min-w-0 shrink">
                                <Badge
                                  variant={badgeVariant}
                                  size="xs"
                                  radius="default"
                                  className={`gap-1 font-semibold shrink-0 ${
                                    isDone
                                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                                      : isCancelled || isFailed
                                        ? 'bg-red-500/20 text-red-400 border-red-500/40'
                                        : ''
                                  }`}
                                >
                                  {isRunning && <Loader2 className="w-2.5 h-2.5 animate-spin text-[var(--primary)]" />}
                                  {isDone && <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />}
                                  {(isCancelled || isFailed) && <AlertCircle className="w-2.5 h-2.5 text-red-400" />}
                                  {!isRunning && !isDone && !isCancelled && !isFailed && <Clock className="w-2.5 h-2.5 text-[var(--muted-foreground)]" />}
                                  <span>{isRunning ? 'RUNNING' : status}</span>
                                </Badge>
                                <span className="text-[9px] font-mono text-[var(--muted-foreground)] uppercase truncate">
                                  {t.id}
                                </span>
                              </div>

                              <div className="flex items-center gap-1.5 shrink-0">
                                <span className="text-[10px] font-mono font-semibold text-[var(--foreground)] tabular-nums">
                                  {t.progress}%
                                </span>
                                <div className="w-10 h-1.5 bg-[var(--card)] rounded-full overflow-hidden border border-[var(--border)]/30 shrink-0">
                                  <div
                                    className={`h-full transition-all duration-300 ${
                                      isRunning
                                        ? 'bg-[var(--primary)]'
                                        : isDone
                                          ? 'bg-emerald-500'
                                          : isCancelled || isFailed
                                            ? 'bg-red-500/60'
                                            : 'bg-[var(--muted)]'
                                    }`}
                                    style={{ width: `${t.progress}%` }}
                                  />
                                </div>
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </ScrollArea>
              </FramePanel>
            </Frame>
          </aside>

          {/* ── CENTER PANEL: Hologram Neural Orb + Display Canvas ── */}
          <section className="flex flex-col min-w-0 h-full min-h-0 overflow-hidden order-2">
            {/* Hologram & Fluid Vortex Avatar Frame */}
            <Frame spacing="xs" className="flex-1 min-h-0 mb-0 flex flex-col overflow-hidden">
              <FramePanel className="p-3 flex flex-col justify-end items-center text-center relative overflow-hidden h-full">

                {/* 3D Qivi Particle Companion Avatar */}
                <div
                  className={`absolute inset-0 flex items-center justify-center z-10 ${
                    isAnyModalOpen ? 'invisible opacity-0 pointer-events-none' : 'visible opacity-100'
                  }`}
                  id="vortex-gif"
                >
                  {!isAnyModalOpen && (
                    <QiviAvatarVisualizer
                      systemState={effectiveSystemState}
                      audioLevel={effectiveAudioLevel}
                      isSleeping={isSleeping}
                      isMicMuted={isMicMuted}
                    />
                  )}
                </div>

                {/* Bottom Center Control & Status Cluster (Directly below avatar companion) */}
                <div className="relative z-20 flex flex-col items-center gap-2.5 w-full max-w-md px-2 mb-2">
                  {/* Minimalist Audio & State Equalizer Banner */}
                  <div className="flex items-center gap-3 px-3.5 py-1 rounded-full bg-[var(--card)] border border-[var(--border)] shadow-xs">
                    {/* State Indicator Dot & Name */}
                    <div className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full transition-colors duration-150 ${
                        effectiveSystemState === 'listening' ? 'bg-emerald-500 animate-pulse ring-2 ring-emerald-500/40' :
                        effectiveSystemState === 'thinking' ? 'bg-amber-500 animate-pulse ring-2 ring-amber-500/40' :
                        effectiveSystemState === 'speaking' ? 'bg-[var(--accent)] animate-pulse ring-2 ring-[var(--accent)]/40' :
                        'bg-[var(--muted-foreground)]'
                      }`} />
                      <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--foreground)] font-semibold">
                        {effectiveSystemState}
                      </span>
                    </div>

                    {/* Equalizer Waveform Soundwave Bars (Only shown when speaking, not during listening) */}
                    {effectiveSystemState === 'speaking' && (
                      <div className="flex items-center gap-1 h-3.5 px-1.5 py-0.5 rounded-full bg-[var(--input)] border border-[var(--border)]/60">
                        <div className="w-0.5 bg-emerald-400 rounded-full animate-soundwave-1" />
                        <div className="w-0.5 bg-emerald-500 rounded-full animate-soundwave-2" />
                        <div className="w-0.5 bg-cyan-400 rounded-full animate-soundwave-3" />
                        <div className="w-0.5 bg-[var(--accent)] rounded-full animate-soundwave-4" />
                        <div className="w-0.5 bg-amber-400 rounded-full animate-soundwave-5" />
                        <div className="w-0.5 bg-emerald-400 rounded-full animate-soundwave-6" />
                      </div>
                    )}
                  </div>



                  {/* Avatar Command Buttons (MIC, SPEAKER, STOP, POWER/SLEEP) */}
                  <div className="flex flex-wrap items-center justify-center gap-1.5 sm:gap-2 max-w-full">
                    {/* Mic Mute Toggle */}
                    <Button
                      variant={isMicMuted ? "destructive" : "outline"}
                      size="sm"
                      onClick={handleToggleMic}
                      title={isMicMuted ? "Unmute Microphone" : "Mute Microphone"}
                      className="h-7 px-2 sm:px-2.5 gap-1 text-xs font-medium shrink-0"
                    >
                      {isMicMuted ? <MicOff className="w-3 h-3" /> : <Mic className="w-3 h-3 text-primary" />}
                      <span className="text-[10px] sm:text-[11px]">{isMicMuted ? 'UNMUTE' : 'MUTE'}</span>
                    </Button>

                    {/* Speaker Voice Output Mute (Deafen) Toggle */}
                    <Button
                      variant={isSpeakerMuted ? "destructive" : "outline"}
                      size="sm"
                      onClick={handleToggleSpeaker}
                      title={isSpeakerMuted ? "Unmute Assistant Voice Output" : "Mute Assistant Voice Output (Deafen)"}
                      className="h-7 px-2 sm:px-2.5 gap-1 text-xs font-medium shrink-0"
                    >
                      {isSpeakerMuted ? <VolumeX className="w-3 h-3" /> : <Volume2 className="w-3 h-3 text-primary" />}
                      <span className="text-[10px] sm:text-[11px]">{isSpeakerMuted ? 'MUTED' : 'SPEAKER'}</span>
                    </Button>

                    {/* Emergency Stop */}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleEmergencyStop}
                      title="Emergency Stop (Interrupt Agent Execution)"
                      className="h-7 px-2 sm:px-2.5 gap-1 text-xs font-medium hover:bg-destructive/15 hover:border-destructive/50 hover:text-destructive shrink-0"
                    >
                      <Square className="w-3 h-3 text-destructive" />
                      <span className="text-[10px] sm:text-[11px]">STOP</span>
                    </Button>

                    {/* Power / Sleep Mode Toggle */}
                    <Button
                      variant={isSleeping ? "secondary" : "outline"}
                      size="sm"
                      onClick={handleToggleSleep}
                      title={isSleeping ? "Wake Assistant (Resume Active Mode)" : "Put Assistant to Sleep (Standby Mode)"}
                      className="h-7 px-2 sm:px-2.5 gap-1 text-xs font-medium shrink-0"
                    >
                      <Power className={`w-3.5 h-3.5 ${isSleeping ? 'text-amber-400' : 'text-emerald-500'}`} />
                      <span className="text-[10px] sm:text-[11px]">{isSleeping ? 'ON' : 'OFF'}</span>
                    </Button>
                  </div>
                </div>
              </FramePanel>
            </Frame>

            {/* Sleek Low-Profile Splitter Bar (Desktop Only) */}
            <div
              onMouseDown={(e) => {
                e.preventDefault()
                dragStartRef.current = {
                  startY: e.clientY,
                  startHeight: canvasHeight,
                }
                setIsDraggingCanvas(true)
              }}
              title="Drag to resize Inspector panel / Double click to reset"
              onDoubleClick={() => setCanvasHeight(240)}
              className={`hidden lg:flex h-2 my-0.5 items-center justify-center cursor-row-resize select-none relative z-20 group transition-colors ${isDraggingCanvas ? 'bg-[var(--accent)]/20' : 'hover:bg-[var(--accent)]/10'
                }`}
            >
              <div
                className={`h-1 rounded-full transition-all duration-200 ${isDraggingCanvas
                    ? 'w-16 bg-[var(--accent)] shadow-sm'
                    : 'w-10 bg-[var(--border)] group-hover:w-14 group-hover:bg-[var(--accent)]'
                  }`}
              />
            </div>

            {/* LIVE DISPLAY CANVAS Frame (Dynamic Resizable Height on Desktop, Responsive on Tablet/Mobile) */}
            <Frame
              spacing="xs"
              style={{ height: `${canvasHeight}px` }}
              className={cn(
                "shrink-0 overflow-hidden flex flex-col mt-0.5",
                !isDraggingCanvas && "transition-[height] duration-150 ease-out"
              )}
            >
              <FramePanel className="p-2.5 flex flex-col h-full min-h-0 overflow-hidden">
                <FrameHeader className="p-0 pb-1.5 shrink-0">
                  <div className="flex items-center justify-between">
                    <FrameTitle className="text-[11px] font-semibold text-[var(--foreground)]">Live Output</FrameTitle>
                    <div className="flex items-center gap-1.5">
                      <Button variant="ghost" size="sm" onClick={() => navigator.clipboard.writeText(canvasContent)} className="h-7 text-[11px] gap-1 text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
                        <Copy className="w-3 h-3" />
                        <span>COPY</span>
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setCanvasContent('')} className="h-7 text-[11px] gap-1 text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
                        <Trash2 className="w-3 h-3" />
                        <span>CLEAR</span>
                      </Button>
                    </div>
                  </div>
                </FrameHeader>

                <ScrollArea className="flex-1">
                  {canvasContent ? (
                    <div className="font-mono text-xs text-[var(--foreground)] whitespace-pre-wrap leading-relaxed pr-2">
                      {canvasContent}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-center text-[var(--muted-foreground)] py-8">
                      <Sparkles className="w-8 h-8 text-[var(--accent)] opacity-50 mb-2" />
                      <div className="text-xs font-semibold text-[var(--foreground)]">Ready</div>
                      <div className="text-[10px] font-mono text-[var(--muted-foreground)] mt-1 max-w-sm leading-relaxed">
                        Live execution output streams here.
                      </div>
                    </div>
                  )}
                </ScrollArea>
              </FramePanel>
            </Frame>
          </section>

          {/* ── RIGHT PANEL: Payload Ingestion & Activity Log ── */}
          <aside className="flex flex-col gap-2 min-w-0 h-full min-h-0 overflow-hidden order-3">
            {/* Uploads Frame */}
            <Frame spacing="xs" className="shrink-0">
              <FramePanel className="p-2.5">
                <FrameHeader className="p-0 pb-1.5">
                  <div className="flex items-center justify-between">
                    <FrameTitle className="text-[11px] font-semibold text-[var(--foreground)]">Uploads</FrameTitle>
                    {uploadedFiles.length > 0 && (
                      <button
                        type="button"
                        onClick={handleClearAllFiles}
                        className="text-[10px] text-[var(--muted-foreground)] hover:text-red-400 transition-colors"
                      >
                        Clear ({uploadedFiles.length})
                      </button>
                    )}
                  </div>
                </FrameHeader>

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

                {/* Interactive Drag & Drop Zone */}
                <div
                  onDragOver={(e) => {
                    e.preventDefault()
                    setIsDraggingOver(true)
                  }}
                  onDragLeave={(e) => {
                    e.preventDefault()
                    setIsDraggingOver(false)
                  }}
                  onDrop={(e) => {
                    e.preventDefault()
                    setIsDraggingOver(false)
                    if (e.dataTransfer.files) handleFileUpload(e.dataTransfer.files)
                  }}
                  className={`border-2 border-dashed rounded-[var(--radius,0.5rem)] p-3 text-center transition-all ${isDraggingOver
                      ? 'border-[var(--accent)] bg-[var(--accent)]/10 shadow-sm'
                      : 'border-[var(--border)] bg-[var(--input)] hover:border-[var(--accent)]/50'
                    }`}
                >
                  <div className="flex items-center justify-center gap-2 mb-1.5">
                    <FileUp className={`w-5 h-5 transition-colors ${isDraggingOver ? 'text-[var(--primary)]' : 'text-[var(--primary)]'}`} />
                    <FolderOpen className={`w-5 h-5 transition-colors ${isDraggingOver ? 'text-[var(--primary)]' : 'text-[var(--primary)]'}`} />
                  </div>

                  <div className="text-xs font-medium text-[var(--foreground)]">
                    {isDraggingOver ? 'Drop files or folders here' : 'Drag & drop any files or folders'}
                  </div>
                  <div className="text-[10px] text-[var(--muted-foreground)] font-mono mt-0.5 mb-2.5">
                    Images, PDFs, code, docs, audio, or zip
                  </div>

                  <div className="grid grid-cols-2 gap-1.5 w-full">
                    <Button
                      variant="outline"
                      size="sm"
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="h-7 px-2 text-[11px] font-medium gap-1 whitespace-nowrap bg-[var(--input)] border-[var(--border)] hover:bg-[var(--primary)]/15 text-[var(--foreground)] w-full justify-center"
                    >
                      <FileUp className="w-3.5 h-3.5 text-[var(--primary)] shrink-0" />
                      <span className="truncate">Choose Files</span>
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      type="button"
                      onClick={handleChooseFolderClick}
                      className="h-7 px-2 text-[11px] font-medium gap-1 whitespace-nowrap border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--primary)]/15 bg-[var(--input)] w-full justify-center"
                    >
                      <FolderOpen className="w-3.5 h-3.5 text-[var(--primary)] shrink-0" />
                      <span className="truncate">Choose Folder</span>
                    </Button>
                  </div>
                </div>

                {/* Uploaded Files Chips List */}
                {uploadedFiles.length > 0 && (
                  <div className="mt-2.5 max-h-28 overflow-y-auto space-y-1 pr-1">
                    {uploadedFiles.map((f, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between px-2 py-1 rounded-md bg-[var(--input)] border border-[var(--border)] text-[11px]"
                      >
                        <div className="flex items-center gap-1.5 min-w-0 mr-1">
                          {f.type === 'FOLDER' ? (
                            <FolderOpen className="w-3 h-3 text-[var(--accent)] shrink-0" />
                          ) : (
                            <FileCode className="w-3 h-3 text-[var(--muted-foreground)] shrink-0" />
                          )}
                          <span className="text-[var(--foreground)] truncate">{f.name}</span>
                          <span className="text-[var(--muted-foreground)] font-mono text-[9px] shrink-0">({f.size})</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveFile(i)}
                          className="text-[var(--muted-foreground)] hover:text-red-400 p-0.5 rounded transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </FramePanel>
            </Frame>

            {/* Chat Frame with 100% Official Assistant-UI Library Components */}
            <Frame spacing="xs" className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <FramePanel className="p-2.5 flex flex-col h-full min-h-0 overflow-hidden">
                <FrameHeader className="p-0 pb-1.5 shrink-0">
                  <div className="flex items-center justify-between w-full">
                    <FrameTitle className="text-[11px] font-semibold text-[var(--foreground)]">Chat</FrameTitle>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCopyChat}
                      className="h-6 px-1.5 text-[10px] gap-1 text-[var(--muted-foreground)] hover:text-[var(--foreground)] cursor-pointer"
                      title="Copy full chat transcript"
                    >
                      {isChatCopied ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-emerald-400 font-mono text-[10px]">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span className="text-[10px]">Copy</span>
                        </>
                      )}
                    </Button>
                  </div>
                </FrameHeader>

                {/* 100% Official Assistant-UI Runtime & Thread Primitives */}
                <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
                  <AssistantRuntimeProvider runtime={assistantRuntime}>
                    <ZezoChatThread className="h-full min-h-0" systemState={effectiveSystemState} />
                  </AssistantRuntimeProvider>
                </div>
              </FramePanel>
            </Frame>
          </aside>

        </main>
      )}

      {/* ── SCRANTON OFFICE SCREEN ── */}
      {activeTab === 'office' && (
        <main className="flex-1 w-full h-[calc(100vh-48px)] overflow-hidden bg-[var(--background)]">
          <AutonomousOfficeScreen backendLogs={liveLogs} />
        </main>
      )}

      {/* ── WORKFLOW AUTOMATION PIPELINES (COMING SOON) ── */}
      {activeTab === 'workflow' && (
        <main className="flex-1 flex items-center justify-center p-6 bg-[var(--background)]">
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
        onClose={() => setIsTaskModalOpen(false)}
        onCancelTask={cancelTask}
        tasks={tasks}
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
