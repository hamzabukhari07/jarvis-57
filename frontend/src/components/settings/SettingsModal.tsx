import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Badge } from '../reui/badge'
import { Card } from '../reui/card'
import { Switch } from '../ui/switch'
import { ScrollArea } from '../ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import {
  ArrowLeft,
  Search,
  Sliders,
  AudioWaveform,
  Key,
  Bot,
  Palette,
  Atom,
  Info,
  CheckCircle,
  Check,
  Sparkles,
  Moon,
  Compass,
  Zap,
  Eye,
  EyeOff,
  Copy,
  Volume2,
  Mic,
  Radio,
  Keyboard,
  Plus,
  Trash2,
  Loader2,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import type { AudioDeviceState } from '../../hooks/useZezoSocket'
import { QiviAvatarVisualizer } from '../canvas/QiviAvatarVisualizer'
import type { QiviShape } from 'qivi-react'
import { SkillsSettingsTab } from './SkillsSettingsTab'
import { MemoryGraphCanvas, type GraphNode, type GraphLink } from '../memory/MemoryGraphCanvas'
import { MemoryInspectorDrawer } from '../memory/MemoryInspectorDrawer'
import { NewMemoryModal } from '../memory/NewMemoryModal'
import { ConfirmDialog } from '../reui/confirm-dialog'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  audioDevices?: AudioDeviceState
  onSaveAudioDevices?: (inputDev: string, outputDev: string) => void
  onWakeToggle?: (enable: boolean) => void
  onPttToggle?: (enable: boolean) => void
}

export type InteractionMode = 'always_listening' | 'wake_word' | 'push_to_talk'

type SectionId =
  | 'general'
  | 'audio'
  | 'providers'
  | 'persona'
  | 'appearance'
  | 'memory'
  | 'skills'
  | 'about'

export interface ThemeSystem {
  id: string
  name: string
  tagline: string
  badge: string
  icon: any
  previewBg: string
  previewCard: string
  previewBorder: string
  previewAccent: string
  textColor: string
  defaultAccent: string
  description: string
  swatches: string[]
}

export const THEME_SYSTEMS: ThemeSystem[] = [
  {
    id: 'copper',
    name: 'Terracotta',
    tagline: 'Warm Clay & Minimal Anthropic OKLCH',
    badge: 'CLAUDE',
    icon: Moon,
    previewBg: '#3d3735',
    previewCard: '#453e3b',
    previewBorder: 'rgba(234, 88, 12, 0.35)',
    previewAccent: '#ea580c',
    textColor: '#fef3c7',
    defaultAccent: '#ea580c',
    description: 'Warm baked clay with radiant copper amber accents and high-contrast typography.',
    swatches: ['#3d3735', '#453e3b', '#ea580c', '#d97706', '#fef3c7'],
  },
  {
    id: 'emerald',
    name: 'Neo Mint',
    tagline: 'Pitch Obsidian & Electric Cyber Mint OKLCH',
    badge: 'MINT',
    icon: Sparkles,
    previewBg: '#080e0a',
    previewCard: '#131e17',
    previewBorder: 'rgba(52, 211, 153, 0.35)',
    previewAccent: '#34d399',
    textColor: '#ecfdf5',
    defaultAccent: '#34d399',
    description: 'Pitch obsidian surface with electric cyber emerald and neo-mint highlights.',
    swatches: ['#080e0a', '#131e17', '#34d399', '#059669', '#ecfdf5'],
  },
  {
    id: 'arctic-teal',
    name: 'Arctic Teal',
    tagline: 'Deep Slate Obsidian & Luminous Teal OKLCH',
    badge: 'ARCTIC',
    icon: Compass,
    previewBg: '#131922',
    previewCard: '#1e2836',
    previewBorder: 'rgba(45, 212, 191, 0.35)',
    previewAccent: '#2dd4bf',
    textColor: '#f0fdfa',
    defaultAccent: '#2dd4bf',
    description: 'Deep slate obsidian paired with luminous oceanic teal and seafoam accents.',
    swatches: ['#131922', '#1e2836', '#2dd4bf', '#0d9488', '#f0fdfa'],
  },
  {
    id: 'cobalt',
    name: 'Cobalt',
    tagline: 'Pure Obsidian & Radiant Electric Cobalt OKLCH',
    badge: 'COBALT',
    icon: Zap,
    previewBg: '#0b1120',
    previewCard: '#172033',
    previewBorder: 'rgba(59, 130, 246, 0.35)',
    previewAccent: '#3b82f6',
    textColor: '#eff6ff',
    defaultAccent: '#3b82f6',
    description: 'Pure obsidian dark mode with electric azure cobalt and crisp radiant blue.',
    swatches: ['#0b1120', '#172033', '#3b82f6', '#2563eb', '#eff6ff'],
  },
  {
    id: 'indigo',
    name: 'Amethyst',
    tagline: 'Deep Charcoal & Radiant Amethyst Violet OKLCH',
    badge: 'VIOLET',
    icon: Bot,
    previewBg: '#1e1929',
    previewCard: '#2d243d',
    previewBorder: 'rgba(139, 92, 246, 0.35)',
    previewAccent: '#8b5cf6',
    textColor: '#faf5ff',
    defaultAccent: '#8b5cf6',
    description: 'Deep charcoal surface with vibrant electric amethyst and violet accents.',
    swatches: ['#1e1929', '#2d243d', '#8b5cf6', '#6366f1', '#faf5ff'],
  },
]

const AVATAR_CHARACTERS = [
  {
    id: 'qivi',
    name: 'Qivi',
    archetype: 'Core Companion',
    desc: 'Adaptive, friendly and balanced presence',
    shape: 'blob' as QiviShape,
    theme: 'match_theme',
    color: '#38bdf8',
  },
  {
    id: 'female',
    name: 'Nova',
    archetype: 'Spark Intellect',
    desc: 'Expressive energy with electric lavender aura',
    shape: 'blob' as QiviShape,
    theme: 'lavender',
    color: '#c084fc',
  },
  {
    id: 'male',
    name: 'Sol',
    archetype: 'Diplomat Focus',
    desc: 'Calm, composed demeanor with crisp arctic tone',
    shape: 'blob' as QiviShape,
    theme: 'arctic',
    color: '#67e8f9',
  },
  {
    id: 'ember',
    name: 'Ember',
    archetype: 'Chaos Catalyst',
    desc: 'Dynamic star silhouette with radiant solar amber aura',
    shape: 'star' as QiviShape,
    theme: 'amber',
    color: '#f59e0b',
  },
  {
    id: 'sage',
    name: 'Sage',
    archetype: 'Deep Analyst',
    desc: 'Structured wisdom with high-contrast cyber emerald aura',
    shape: 'blob' as QiviShape,
    theme: 'mint',
    color: '#34d399',
  },
  {
    id: 'atlas',
    name: 'Atlas',
    archetype: 'Guardian Shield',
    desc: 'Protective shield geometry with midnight navy pulse',
    shape: 'shield' as QiviShape,
    theme: 'midnight',
    color: '#818cf8',
  },
]

const AVATAR_SHAPES = [
  { id: 'blob', label: 'Organic Blob', desc: 'Natural fluid morphing sphere' },
  { id: 'shield', label: 'Guardian Shield', desc: 'Tactical defensive geometry' },
  { id: 'star', label: 'Radiant Star', desc: 'Multi-point high dynamism burst' },
  { id: 'hex', label: 'Cyber Hex', desc: 'Structured tactical matrix' },
  { id: 'heart', label: 'Pulse Heart', desc: 'Harmonic empathetic silhouette' },
]

const AVATAR_THEMES = [
  { id: 'default', label: 'Original Crystal', desc: 'Canonical pure obsidian & white crystal', color: '#f4f4f5' },
  { id: 'mint', label: 'Cyber Mint', desc: 'Vibrant electric emerald aura', color: '#34d399' },
  { id: 'arctic', label: 'Arctic Teal', desc: 'Crisp ice blue & oceanic teal matrix', color: '#2dd4bf' },
  { id: 'lavender', label: 'Electric Lavender', desc: 'Radiant violet & amethyst nebula', color: '#c084fc' },
  { id: 'amber', label: 'Solar Amber', desc: 'Molten gold & terracotta warmth', color: '#f59e0b' },
  { id: 'midnight', label: 'Midnight Navy', desc: 'Deep cosmic indigo & cyan glow', color: '#818cf8' },
  { id: 'sunset', label: 'Sunset Coral', desc: 'Warm dusk coral & solar gold', color: '#fb7185' },
  { id: 'match_theme', label: 'Match UI Accent', desc: 'Adapts dynamically to current OS theme', color: 'var(--primary)' },
]

const ApiKeyInputRow: React.FC<{
  label: string
  desc: string
  placeholder: string
  value: string
  onChange: (val: string) => void
}> = ({ label, desc, placeholder, value, onChange }) => {
  const [show, setShow] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    if (!value) return
    navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 hover:bg-muted/30 transition-colors gap-2">
      <div className="min-w-0 flex-1">
        <div className="text-xs font-semibold text-foreground">{label}</div>
        <div className="text-[11px] text-muted-foreground mt-0.5">{desc}</div>
      </div>
      <div className="relative w-full sm:w-72 flex items-center shrink-0">
        <Input
          type={show ? 'text' : 'password'}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="h-8 pr-16 bg-input/60 border-border text-foreground text-xs font-mono"
        />
        <div className="absolute right-1 flex items-center gap-0.5">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShow(!show)}
            title={show ? 'Hide API Key' : 'Show API Key'}
            className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            {show ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={!value}
            onClick={handleCopy}
            title={copied ? 'Copied!' : 'Copy API Key'}
            className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </Button>
        </div>
      </div>
    </div>
  )
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  audioDevices,
  onSaveAudioDevices,
  onWakeToggle,
  onPttToggle,
}) => {
  // Navigation & Search
  const [activeSection, setActiveSection] = useState<SectionId>('general')
  const [searchQuery, setSearchQuery] = useState('')

  // ── 1. Controls & Toggles ──
  const [autostart, setAutostart] = useState(false)
  const [morningBrief, setMorningBrief] = useState(true)
  const [wakeWord, setWakeWord] = useState(false)
  const [assistantName, setAssistantName] = useState('Zezo')
  const [availableAssistantNames, setAvailableAssistantNames] = useState<string[]>(['Zezo', 'Nova', 'Jarvis'])
  const [pushToTalk, setPushToTalk] = useState(false)
  const [interactionMode, setInteractionMode] = useState<InteractionMode>('always_listening')
  const [activeTheme, setActiveTheme] = useState<string>(() => {
    return localStorage.getItem('zezo_theme') || 'copper'
  })
  const [activeAccent, setActiveAccent] = useState(() => {
    return localStorage.getItem('zezo_accent') || '#ea580c'
  })

  // ── 2. Audio & Endpoints ──
  const [thinkingEnabled, setThinkingEnabled] = useState(false)
  const [proactiveAudioEnabled, setProactiveAudioEnabled] = useState(false)
  const [preferredCreationAgent, setPreferredCreationAgent] = useState('opencode')
  const [preferredEditAgent, setPreferredEditAgent] = useState('kilo')
  const [opencodeModel, setOpencodeModel] = useState('opencode/fledge-alpha-free')
  const [kiloModel, setKiloModel] = useState('kilo/free-refactor')
  const [antigravityModel, setAntigravityModel] = useState('gemini-3.7-flash-medium')
  const [memoryToast, setMemoryToast] = useState<string | null>(null)
  const [isWipingMemory, setIsWipingMemory] = useState(false)
  const [isWipeConfirmOpen, setIsWipeConfirmOpen] = useState(false)
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([])
  const [graphLinks, setGraphLinks] = useState<GraphLink[]>([])
  const [selectedGraphNode, setSelectedGraphNode] = useState<GraphNode | null>(null)
  const [isGraphLoading, setIsGraphLoading] = useState(false)
  const [isNewMemoryModalOpen, setIsNewMemoryModalOpen] = useState(false)
  const [isPlayingVoice, setIsPlayingVoice] = useState(false)
  const [selectedInputDev, setSelectedInputDev] = useState('')
  const [selectedOutputDev, setSelectedOutputDev] = useState('')
  const [internalAudioDevices, setInternalAudioDevices] = useState<AudioDeviceState | null>(null)
  const [isPlayingAudioTest, setIsPlayingAudioTest] = useState(false)
  const [isTestingMic, setIsTestingMic] = useState(false)
  const [micTestLevel, setMicTestLevel] = useState(0)
  const micMediaStreamRef = useRef<MediaStream | null>(null)
  const micAudioContextRef = useRef<AudioContext | null>(null)
  const micAnimFrameRef = useRef<number | null>(null)

  // Speaker harmonic chime test
  const handleTestSpeaker = () => {
    if (isPlayingAudioTest) return
    setIsPlayingAudioTest(true)
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
      const ctx = new AudioCtx()
      const now = ctx.currentTime

      const osc1 = ctx.createOscillator()
      const osc2 = ctx.createOscillator()
      const gain = ctx.createGain()

      osc1.type = 'sine'
      osc2.type = 'triangle'
      osc1.frequency.setValueAtTime(587.33, now) // D5
      osc1.frequency.exponentialRampToValueAtTime(880.00, now + 0.12) // A5
      osc2.frequency.setValueAtTime(880.00, now)

      gain.gain.setValueAtTime(0.001, now)
      gain.gain.linearRampToValueAtTime(0.25, now + 0.05)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.9)

      osc1.connect(gain)
      osc2.connect(gain)
      gain.connect(ctx.destination)

      osc1.start(now)
      osc2.start(now)
      osc1.stop(now + 0.95)
      osc2.stop(now + 0.95)

      setTimeout(() => {
        setIsPlayingAudioTest(false)
        try { ctx.close() } catch {}
      }, 1000)
    } catch {
      setIsPlayingAudioTest(false)
    }
  }

  // Interactive Microphone Volume Level Test
  const handleToggleMicTest = async () => {
    if (isTestingMic) {
      if (micAnimFrameRef.current) cancelAnimationFrame(micAnimFrameRef.current)
      if (micMediaStreamRef.current) {
        micMediaStreamRef.current.getTracks().forEach((t) => t.stop())
        micMediaStreamRef.current = null
      }
      if (micAudioContextRef.current) {
        try { micAudioContextRef.current.close() } catch {}
        micAudioContextRef.current = null
      }
      setIsTestingMic(false)
      setMicTestLevel(0)
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      micMediaStreamRef.current = stream
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
      const ctx = new AudioCtx()
      micAudioContextRef.current = ctx
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)

      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      setIsTestingMic(true)

      const updateMeter = () => {
        analyser.getByteFrequencyData(dataArray)
        let sum = 0
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i]
        }
        const avg = sum / dataArray.length
        const normalized = Math.min(100, Math.round((avg / 128) * 100))
        setMicTestLevel(normalized)
        micAnimFrameRef.current = requestAnimationFrame(updateMeter)
      }
      updateMeter()
    } catch (err) {
      console.warn('Browser getUserMedia failed, using backend hardware test endpoint:', err)
      // Hardware Backend Fallback via sounddevice
      setIsTestingMic(true)
      setMicTestLevel(15)
      try {
        const res = await fetch('/api/audio/test_mic')
        if (res.ok) {
          const data = await res.json()
          setMicTestLevel(Math.max(25, data.level || 0))
          setTimeout(() => {
            setMicTestLevel(Math.max(10, (data.level || 0) + 15))
          }, 300)
          setTimeout(() => {
            setIsTestingMic(false)
            setMicTestLevel(0)
          }, 2000)
        } else {
          setIsTestingMic(false)
          setMicTestLevel(0)
        }
      } catch (backendErr) {
        console.error('Backend mic test failed:', backendErr)
        setIsTestingMic(false)
        setMicTestLevel(0)
      }
    }
  }

  // Cleanup mic resources on unmount
  useEffect(() => {
    return () => {
      if (micAnimFrameRef.current) cancelAnimationFrame(micAnimFrameRef.current)
      if (micMediaStreamRef.current) {
        micMediaStreamRef.current.getTracks().forEach((t) => t.stop())
      }
      if (micAudioContextRef.current) {
        try { micAudioContextRef.current.close() } catch {}
      }
    }
  }, [])

  // ── 3. API Keys ──
  const [geminiKey, setGeminiKey] = useState('')
  const [groqKey, setGroqKey] = useState('')
  const [elevenLabsKey, setElevenLabsKey] = useState('')
  const [tavilyKey, setTavilyKey] = useState('')

  // ── 4. Assistant Persona & Avatar ──
  const [voiceName, setVoiceName] = useState('Charon')
  const [responseLanguage, setResponseLanguage] = useState('auto')
  const [avatarPreset, setAvatarPreset] = useState<string>(() => localStorage.getItem('zezo_avatar_preset') || 'qivi')
  const [avatarShape, setAvatarShape] = useState<QiviShape>(() => (localStorage.getItem('zezo_avatar_shape') as QiviShape) || 'blob')
  const [avatarTheme, setAvatarTheme] = useState<string>(() => localStorage.getItem('zezo_avatar_theme') || 'match_theme')
  const [avatarQuality, setAvatarQuality] = useState<'auto' | 'high' | 'medium' | 'low'>(
    () => (localStorage.getItem('zezo_avatar_quality') as any) || 'high'
  )
  const [avatarLighting, setAvatarLighting] = useState<number>(() => {
    const val = localStorage.getItem('zezo_avatar_lighting')
    return val ? parseFloat(val) : 0.85
  })


  const isLoadedRef = useRef(false)
  const hydratedRef = useRef(false)

  const handlePreviewVoice = (vName: string) => {
    try {
      setIsPlayingVoice(true)
      const audio = new Audio(`/api/preview_voice?voice=${encodeURIComponent(vName.toLowerCase())}&t=${Date.now()}`)
      audio.onended = () => setIsPlayingVoice(false)
      audio.onerror = () => {
        setIsPlayingVoice(false)
      }
      audio.play().catch(() => {
        setIsPlayingVoice(false)
      })
    } catch {
      setIsPlayingVoice(false)
    }
  }

  const handleExecuteWipeMemory = async () => {
    try {
      setIsWipingMemory(true)
      const res = await api.wipeAllMemory()
      setSelectedGraphNode(null)
      await loadMemoryGraph()
      setIsWipeConfirmOpen(false)
      setMemoryToast(res.message || 'All memory successfully wiped ✓')
      setTimeout(() => setMemoryToast(null), 3000)
    } catch (e: any) {
      console.error('Failed to wipe all memory:', e)
      setMemoryToast(e.message || 'Failed to wipe memory')
      setTimeout(() => setMemoryToast(null), 3000)
    } finally {
      setIsWipingMemory(false)
    }
  }

  const loadMemoryGraph = useCallback(async () => {
    setIsGraphLoading(true)
    try {
      const res = await api.getMemoryGraph()
      if (res && res.nodes) {
        setGraphNodes(res.nodes)
        setGraphLinks(res.links || [])
      }
    } catch (err) {
      console.warn('Could not load memory graph:', err)
    } finally {
      setIsGraphLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen && activeSection === 'memory') {
      loadMemoryGraph()
    }
  }, [isOpen, activeSection, loadMemoryGraph])

  const handleSelectConnectedNode = (nodeIdentifier: string) => {
    const target = graphNodes.find(
      (n) =>
        n.id.toLowerCase() === nodeIdentifier.toLowerCase() ||
        n.label.toLowerCase() === nodeIdentifier.toLowerCase() ||
        n.file.toLowerCase() === nodeIdentifier.toLowerCase()
    )
    if (target) {
      setSelectedGraphNode(target)
    }
  }


  const handleToggle = (key: string, value: boolean, setter: (v: boolean) => void) => {
    setter(value)
    api.saveConfig({ [key]: value }).catch((err) => console.warn(`Failed to immediately save ${key}:`, err))
  }

  const handleInteractionModeSelect = (mode: InteractionMode) => {
    setInteractionMode(mode)
    const isWake = mode === 'wake_word'
    const isPtt = mode === 'push_to_talk'
    setWakeWord(isWake)
    setPushToTalk(isPtt)
    if (onWakeToggle) {
      try {
        onWakeToggle(isWake)
      } catch (err) {
        console.warn('Failed to dispatch onWakeToggle:', err)
      }
    }
    if (onPttToggle) {
      try {
        onPttToggle(isPtt)
      } catch (err) {
        console.warn('Failed to dispatch onPttToggle:', err)
      }
    }
    api.saveConfig({
      wake_word_enabled: isWake,
      push_to_talk_enabled: isPtt,
    }).catch((err) => console.warn('Failed to immediately save interaction mode:', err))
  }

  const handleThemeSelect = (themeId: string) => {
    const isCurrentLight = activeTheme.endsWith('-light') || activeTheme === 'light'
    const targetTheme = isCurrentLight ? `${themeId}-light` : themeId
    const selectedSystem = THEME_SYSTEMS.find((t) => t.id === themeId)
    const nextAccent = selectedSystem?.defaultAccent || '#ea580c'

    setActiveTheme(targetTheme)
    setActiveAccent(nextAccent)
    localStorage.setItem('zezo_theme', targetTheme)
    localStorage.setItem('zezo_accent', nextAccent)
    document.documentElement.setAttribute('data-theme', targetTheme)
    document.documentElement.style.removeProperty('--accent')
    window.dispatchEvent(new CustomEvent('zezo_theme_changed', { detail: { theme: targetTheme } }))
    window.dispatchEvent(new CustomEvent('zezo_accent_changed', { detail: { accent: nextAccent } }))
    api.saveConfig({ theme: targetTheme, accent: nextAccent }).catch((err) => console.warn('Failed to immediately save theme:', err))
  }

  // Load initial settings when modal opens
  useEffect(() => {
    if (isOpen) {
      const load = async () => {
        try {
          const cfg = await api.getConfig()
          if (cfg) {
            if (cfg.theme) {
              setActiveTheme(cfg.theme)
              localStorage.setItem('zezo_theme', cfg.theme)
              document.documentElement.setAttribute('data-theme', cfg.theme)
            }
            if (cfg.accent) {
              setActiveAccent(cfg.accent)
              localStorage.setItem('zezo_accent', cfg.accent)
            }
            if (cfg.gemini_key || cfg.gemini_api_key_masked) setGeminiKey(cfg.gemini_key || cfg.gemini_api_key_masked)
            if (cfg.groq_key || cfg.groq_api_key_masked) setGroqKey(cfg.groq_key || cfg.groq_api_key_masked)
            if (cfg.elevenlabs_key || cfg.elevenlabs_api_key_masked) setElevenLabsKey(cfg.elevenlabs_key || cfg.elevenlabs_api_key_masked)
            if (cfg.tavily_key || cfg.tavily_api_key_masked) setTavilyKey(cfg.tavily_key || cfg.tavily_api_key_masked)
            if (cfg.voice_name) setVoiceName(cfg.voice_name)
            if (cfg.response_language) {
              const langMap: Record<string, string> = {
                en: 'English',
                ur: 'Urdu',
                hi: 'Hindi',
                es: 'Spanish',
                fr: 'French',
                de: 'German',
                ar: 'Arabic',
                tr: 'Turkish',
              }
              setResponseLanguage(langMap[cfg.response_language] || cfg.response_language)
            }
            if (cfg.autostart_enabled !== undefined) setAutostart(Boolean(cfg.autostart_enabled))
            else if (cfg.autostart !== undefined) setAutostart(Boolean(cfg.autostart))

            if (cfg.morning_brief_enabled !== undefined) setMorningBrief(Boolean(cfg.morning_brief_enabled))
            else if (cfg.morning_brief !== undefined) setMorningBrief(Boolean(cfg.morning_brief))

            const isWake = cfg.wake_word_enabled !== undefined ? Boolean(cfg.wake_word_enabled) : Boolean(cfg.wake_word)
            const isPtt = cfg.push_to_talk_enabled !== undefined ? Boolean(cfg.push_to_talk_enabled) : Boolean(cfg.push_to_talk)
            setWakeWord(isWake)
            setPushToTalk(isPtt)
            if (isPtt) {
              setInteractionMode('push_to_talk')
            } else if (isWake) {
              setInteractionMode('wake_word')
            } else {
              setInteractionMode('always_listening')
            }

            if (cfg.assistant_name) setAssistantName(String(cfg.assistant_name))
            if (Array.isArray(cfg.available_assistant_names) && cfg.available_assistant_names.length)
              setAvailableAssistantNames(cfg.available_assistant_names.map(String))

            if (cfg.thinking_enabled !== undefined) setThinkingEnabled(Boolean(cfg.thinking_enabled))
            if (cfg.proactive_audio_enabled !== undefined) setProactiveAudioEnabled(Boolean(cfg.proactive_audio_enabled))
            if (cfg.preferred_creation_agent) setPreferredCreationAgent(cfg.preferred_creation_agent)
            if (cfg.preferred_edit_agent) setPreferredEditAgent(cfg.preferred_edit_agent)
            if (cfg.opencode_model) setOpencodeModel(cfg.opencode_model)
            if (cfg.kilo_model) setKiloModel(cfg.kilo_model)
            if (cfg.antigravity_model) setAntigravityModel(cfg.antigravity_model)

            // Avatar settings persistence
            if (cfg.avatar_preset) {
              setAvatarPreset(cfg.avatar_preset)
              localStorage.setItem('zezo_avatar_preset', cfg.avatar_preset)
            }
            if (cfg.avatar_shape) {
              setAvatarShape(cfg.avatar_shape)
              localStorage.setItem('zezo_avatar_shape', cfg.avatar_shape)
            }
            if (cfg.avatar_theme) {
              setAvatarTheme(cfg.avatar_theme)
              localStorage.setItem('zezo_avatar_theme', cfg.avatar_theme)
            }
            if (cfg.avatar_quality) {
              setAvatarQuality(cfg.avatar_quality)
              localStorage.setItem('zezo_avatar_quality', cfg.avatar_quality)
            }
            if (cfg.avatar_lighting !== undefined) {
              const lgt = parseFloat(cfg.avatar_lighting) || 0.85
              setAvatarLighting(lgt)
              localStorage.setItem('zezo_avatar_lighting', lgt.toString())
            }
          }
          hydratedRef.current = true
        } catch { } finally {
          isLoadedRef.current = true
        }
      }
      load()
      loadMemoryGraph()

      if (audioDevices) {
        if (audioDevices.current_input) setSelectedInputDev(audioDevices.current_input)
        if (audioDevices.current_output) setSelectedOutputDev(audioDevices.current_output)
      }

      const loadAudioEndpoints = async () => {
        try {
          const res = await api.getAudioDevices()
          if (res) {
            const rawIn = res.inputs || res.input_devices || []
            const rawOut = res.outputs || res.output_devices || []
            setInternalAudioDevices({
              inputs: rawIn.map((x: any) => (typeof x === 'string' ? { name: x } : x)),
              outputs: rawOut.map((x: any) => (typeof x === 'string' ? { name: x } : x)),
              current_input: res.current_input || res.input_device || '',
              current_output: res.current_output || res.output_device || '',
            })
            if (!selectedInputDev && (res.current_input || res.input_device)) {
              setSelectedInputDev(res.current_input || res.input_device)
            }
            if (!selectedOutputDev && (res.current_output || res.output_device)) {
              setSelectedOutputDev(res.current_output || res.output_device)
            }
          }
        } catch {}
      }
      loadAudioEndpoints()
    } else {
      isLoadedRef.current = false
    }
  }, [isOpen, audioDevices, loadMemoryGraph])

  // ── Debounced Real-time Auto-Save Engine ──
  useEffect(() => {
    if (!isLoadedRef.current) return

    const flushSettings = async () => {
      try {
        // 1. Instant local persistence & live event dispatch
        localStorage.setItem('zezo_theme', activeTheme)
        localStorage.setItem('zezo_accent', activeAccent)
        localStorage.setItem('zezo_avatar_preset', avatarPreset)
        localStorage.setItem('zezo_avatar_shape', avatarShape)
        localStorage.setItem('zezo_avatar_theme', avatarTheme)
        localStorage.setItem('zezo_avatar_quality', avatarQuality)
        localStorage.setItem('zezo_avatar_lighting', avatarLighting.toString())

        document.documentElement.setAttribute('data-theme', activeTheme)
        document.documentElement.style.removeProperty('--accent')

        window.dispatchEvent(new CustomEvent('zezo_theme_changed', { detail: { theme: activeTheme } }))
        window.dispatchEvent(new CustomEvent('zezo_accent_changed', { detail: { accent: activeAccent } }))
        window.dispatchEvent(
          new CustomEvent('zezo_avatar_settings_changed', {
            detail: {
              preset: avatarPreset,
              shape: avatarShape,
              theme: avatarTheme,
              quality: avatarQuality,
              lighting: avatarLighting,
            },
          })
        )

        // 2. Async backend API synchronization
        try {
          await api.saveConfig({
            theme: activeTheme,
            accent: activeAccent,
            avatar_preset: avatarPreset,
            avatar_shape: avatarShape,
            avatar_theme: avatarTheme,
            avatar_quality: avatarQuality,
            avatar_lighting: avatarLighting,
            gemini_key: geminiKey,
            groq_key: groqKey,
            elevenlabs_key: elevenLabsKey,
            tavily_key: tavilyKey,
            autostart_enabled: autostart,
            morning_brief_enabled: morningBrief,
            wake_word_enabled: wakeWord,
            push_to_talk_enabled: pushToTalk,
            thinking_enabled: thinkingEnabled,
            proactive_audio_enabled: proactiveAudioEnabled,
            preferred_creation_agent: preferredCreationAgent,
            preferred_edit_agent: preferredEditAgent,
            opencode_model: opencodeModel,
            kilo_model: kiloModel,
            antigravity_model: antigravityModel,
            assistant_name: assistantName,
            voice_name: voiceName,
            response_language: responseLanguage,
          })
        } catch (e) {
          console.warn('API saveConfig offline fallback:', e)
        }

        try {
          await api.saveAssistantSettings({
            assistant_name: assistantName,
            voice_name: voiceName,
            response_language: responseLanguage,
            avatar_preset: avatarPreset,
            avatar_shape: avatarShape,
            avatar_theme: avatarTheme,
          })
        } catch (e) {
          console.warn('API saveAssistantSettings offline fallback:', e)
        }
      } catch (e) {
        console.warn('Auto-save error:', e)
      }
    }

    // Skip the first run(s) until the initial config load has hydrated state,
    // otherwise the cleanup flush races the load and re-posts stale values.
    if (!hydratedRef.current) return

    const timer = setTimeout(flushSettings, 300)

    return () => {
      clearTimeout(timer)
      // Flush immediately on unmount or dependency update so changes never get discarded
      flushSettings()
    }
  }, [
    activeTheme,
    activeAccent,
    avatarPreset,
    avatarShape,
    avatarTheme,
    avatarQuality,
    avatarLighting,
    autostart,
    morningBrief,
    wakeWord,
    assistantName,
    pushToTalk,
    thinkingEnabled,
    proactiveAudioEnabled,
    preferredCreationAgent,
    preferredEditAgent,
    opencodeModel,
    kiloModel,
    antigravityModel,
    geminiKey,
    groqKey,
    elevenLabsKey,
    tavilyKey,
    voiceName,
    responseLanguage,
    selectedInputDev,
    selectedOutputDev,
  ])

  const navItems = [
    {
      group: 'CORE',
      items: [
        { id: 'general' as SectionId, label: 'General & Controls', icon: Sliders },
        { id: 'audio' as SectionId, label: 'Audio Settings', icon: AudioWaveform },
        { id: 'providers' as SectionId, label: 'Providers & Keys', icon: Key },
        { id: 'persona' as SectionId, label: 'Assistant Persona', icon: Bot },
      ],
    },
    {
      group: 'INTERFACE & RUNTIME',
      items: [
        { id: 'appearance' as SectionId, label: 'Appearance & Accents', icon: Palette },
        { id: 'memory' as SectionId, label: 'Memory & Intelligence', icon: Atom },
        { id: 'skills' as SectionId, label: 'Skills', icon: Sparkles },
      ],
    },
    {
      group: 'SYSTEM',
      items: [
        { id: 'about' as SectionId, label: 'About ZEZO', icon: Info },
      ],
    },
  ]

  // Filtered categories based on search
  const filteredNavGroups = useMemo(() => {
    if (!searchQuery.trim()) return navItems
    const q = searchQuery.toLowerCase()
    return navItems
      .map((g) => ({
        ...g,
        items: g.items.filter((item) => item.label.toLowerCase().includes(q)),
      }))
      .filter((g) => g.items.length > 0)
  }, [searchQuery])

  // Handle Escape key to return to desktop workspace
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      role="region"
      aria-label="ZEZO OS Settings"
      className="fixed inset-0 z-50 w-screen h-screen bg-[#0a0a0a] text-foreground flex flex-row overflow-hidden"
    >
      {/* ── LEFT SIDEBAR (Navigation Rail) ── */}
      <aside className="w-64 border-r border-border/80 bg-card flex flex-col shrink-0">
          {/* Top Bar for Back Button (Aligned with right main header) */}
          <div className="h-12 border-b border-border zezo-theme-header px-3 flex items-center shrink-0">
            <button
              type="button"
              onClick={onClose}
              className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground px-2.5 py-1.5 rounded-lg hover:bg-muted/50 transition-colors font-medium"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to app</span>
            </button>
          </div>

          <div className="p-3 flex-1 flex flex-col min-h-0">
            {/* Search Box */}
            <div className="relative mb-3">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground pointer-events-none" />
              <Input
                placeholder="Search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 pl-8 text-xs zezo-theme-input rounded-lg placeholder:text-muted-foreground"
              />
            </div>

            {/* Navigation Links */}
            <ScrollArea className="flex-1 pr-1.5">
              <div className="space-y-4 px-1 py-1">
                {filteredNavGroups.map((group) => (
                  <div key={group.group}>
                    <div className="text-[10px] font-mono font-semibold tracking-wider text-muted-foreground/70 px-2.5 mb-1">
                      {group.group}
                    </div>
                    <div className="space-y-0.5">
                      {group.items.map((item) => {
                        const Icon = item.icon
                        const isActive = activeSection === item.id
                        return (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => {
                              setActiveSection(item.id)
                              setSearchQuery('')
                            }}
                            className={`w-full flex items-center gap-2 px-2.5 py-1.5 text-xs rounded-md transition-colors text-left ${isActive
                                ? 'bg-primary/15 text-foreground font-semibold shadow-xs ring-1 ring-primary/35'
                                : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                              }`}
                          >
                            <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                            <span className="truncate">{item.label}</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </aside>

        {/* ── RIGHT MAIN CONTENT AREA ── */}
        <main className="flex-1 flex flex-col min-w-0 zezo-theme-main bg-background h-full overflow-hidden">
          {activeSection === 'memory' ? (
            <div className="flex-1 flex flex-col w-full h-full min-h-0 p-4 md:p-6 gap-3 overflow-hidden">
              <div className="flex items-center justify-between shrink-0">
                <div>
                  <h2 className="text-xl font-bold text-foreground tracking-tight">Memory & Intelligence</h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Explore connected knowledge nodes, Markdown vault notes, and SQLite FTS5 persistence.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {memoryToast && (
                    <span className="text-xs font-mono text-primary bg-primary/10 border border-primary/30 px-2.5 py-1 rounded-md animate-in fade-in">
                      {memoryToast}
                    </span>
                  )}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsWipeConfirmOpen(true)}
                    disabled={isWipingMemory}
                    className="h-8 text-xs font-mono px-3 gap-1.5 text-red-400 border-red-500/30 hover:bg-red-500/10 shadow-sm"
                    title="Permanently wipe all conversation memory, notes, and database history"
                  >
                    {isWipingMemory ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                    <span>Clear All Memory</span>
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => setIsNewMemoryModalOpen(true)}
                    className="h-8 text-xs font-mono px-3 gap-1.5 shadow-sm"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Memory Node</span>
                  </Button>
                </div>
              </div>

              {/* ── 1. Obsidian-Style Knowledge Graph & Inspector Drawer (Takes all remaining width & height!) ── */}
              <div className="flex-1 w-full min-h-0 relative flex flex-col lg:flex-row gap-4 items-stretch overflow-hidden">
                <div className="flex-1 min-w-0 h-full relative">
                  <MemoryGraphCanvas
                    nodes={graphNodes}
                    links={graphLinks}
                    selectedNodeId={selectedGraphNode?.id || null}
                    onSelectNode={(node) => setSelectedGraphNode(node)}
                    onRefresh={loadMemoryGraph}
                    isLoading={isGraphLoading}
                  />
                </div>

                {/* Slide-Out Inspector Drawer */}
                {selectedGraphNode && (
                  <div className="w-full lg:w-96 shrink-0 h-full rounded-2xl overflow-hidden border border-border shadow-xl">
                    <MemoryInspectorDrawer
                      node={selectedGraphNode}
                      onClose={() => setSelectedGraphNode(null)}
                      onNodeUpdated={() => {
                        loadMemoryGraph()
                      }}
                      onSelectConnectedNode={handleSelectConnectedNode}
                    />
                  </div>
                )}
              </div>

              {/* New Memory Modal */}
              <NewMemoryModal
                isOpen={isNewMemoryModalOpen}
                onClose={() => setIsNewMemoryModalOpen(false)}
                onCreated={() => {
                  loadMemoryGraph()
                  setMemoryToast('New memory node created in vault ✓')
                  setTimeout(() => setMemoryToast(null), 3000)
                }}
              />

              {/* ReUI Confirmation Dialog for Total Memory Wipe */}
              <ConfirmDialog
                open={isWipeConfirmOpen}
                onOpenChange={setIsWipeConfirmOpen}
                title="Clear All Memory & Intelligence"
                description="Are you sure you want to permanently wipe all memory?"
                warningText="This action is irreversible. All conversation notes (conv_*.md), extracted topics, SQLite turns, rules, and facts will be permanently deleted, and your knowledge vault will be reset to a clean slate."
                confirmText="Wipe Everything"
                cancelText="Cancel"
                variant="destructive"
                isLoading={isWipingMemory}
                onConfirm={handleExecuteWipeMemory}
              />
            </div>
          ) : (
            <ScrollArea className="flex-1">
              <div className="p-6 md:p-10 max-w-5xl w-full min-w-0 space-y-6 pb-16">
                {/* ──────────────── 1. GENERAL & CONTROLS ──────────────── */}
                {activeSection === 'general' && (
                <>
                  <div>
                    <h2 className="text-xl font-bold text-foreground tracking-tight">General & Quick Controls</h2>
                    <p className="text-xs text-muted-foreground mt-1">
                      Customize interaction modes, wake word detection, and system auto-start.
                    </p>
                  </div>

                  {/* Section: Interaction Mode */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">Interaction Mode</h3>
                      <span className="text-[11px] text-muted-foreground">Select how ZEZO listens & responds</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                      {/* 1. Always Listening */}
                      <Card
                        onClick={() => handleInteractionModeSelect('always_listening')}
                        className={`p-3 cursor-pointer transition-all duration-150 flex flex-col justify-between gap-2.5 group select-none ${
                          interactionMode === 'always_listening'
                            ? 'border-primary bg-primary/[0.06] ring-1 ring-primary/40 shadow-xs'
                            : 'hover:border-primary/40 hover:bg-muted/40 shadow-2xs'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 group-hover:scale-105 transition-transform">
                              <Radio className="w-3.5 h-3.5" />
                            </div>
                            <span className="text-xs font-semibold text-foreground truncate">
                              Always Listening
                            </span>
                          </div>
                          {interactionMode === 'always_listening' ? (
                            <Badge variant="default" size="xs" className="shrink-0 gap-1 font-medium bg-primary/15 text-primary border-primary/40">
                              <Check className="w-2.5 h-2.5" />
                              ACTIVE
                            </Badge>
                          ) : (
                            <Badge variant="outline" size="xs" className="shrink-0 text-muted-foreground group-hover:text-foreground transition-colors">
                              OPEN MIC
                            </Badge>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                          Continuous open mic. Assistant hears you naturally whenever you speak.
                        </p>
                      </Card>

                      {/* 2. Wake Word */}
                      <Card
                        onClick={() => handleInteractionModeSelect('wake_word')}
                        className={`p-3 cursor-pointer transition-all duration-150 flex flex-col justify-between gap-2.5 group select-none ${
                          interactionMode === 'wake_word'
                            ? 'border-primary bg-primary/[0.06] ring-1 ring-primary/40 shadow-xs'
                            : 'hover:border-primary/40 hover:bg-muted/40 shadow-2xs'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 group-hover:scale-105 transition-transform">
                              <Sparkles className="w-3.5 h-3.5" />
                            </div>
                            <span className="text-xs font-semibold text-foreground truncate">
                              Wake Word
                            </span>
                          </div>
                          {interactionMode === 'wake_word' ? (
                            <Badge variant="default" size="xs" className="shrink-0 gap-1 font-medium bg-primary/15 text-primary border-primary/40">
                              <Check className="w-2.5 h-2.5" />
                              ACTIVE
                            </Badge>
                          ) : (
                            <Badge variant="outline" size="xs" className="shrink-0 text-muted-foreground group-hover:text-foreground transition-colors">
                              HANDS-FREE
                            </Badge>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                          Say "{`Hey ${assistantName}`}" to wake. Sleeps automatically after 15s.
                        </p>
                      </Card>

                      {/* 3. Push-To-Talk */}
                      <Card
                        onClick={() => handleInteractionModeSelect('push_to_talk')}
                        className={`p-3 cursor-pointer transition-all duration-150 flex flex-col justify-between gap-2.5 group select-none ${
                          interactionMode === 'push_to_talk'
                            ? 'border-primary bg-primary/[0.06] ring-1 ring-primary/40 shadow-xs'
                            : 'hover:border-primary/40 hover:bg-muted/40 shadow-2xs'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 border border-amber-500/30 bg-amber-500/10 text-amber-400 group-hover:scale-105 transition-transform">
                              <Keyboard className="w-3.5 h-3.5" />
                            </div>
                            <span className="text-xs font-semibold text-foreground truncate">
                              Push-To-Talk
                            </span>
                          </div>
                          {interactionMode === 'push_to_talk' ? (
                            <Badge variant="default" size="xs" className="shrink-0 gap-1 font-medium bg-primary/15 text-primary border-primary/40">
                              <Check className="w-2.5 h-2.5" />
                              ACTIVE
                            </Badge>
                          ) : (
                            <Badge variant="outline" size="xs" className="shrink-0 text-muted-foreground group-hover:text-foreground transition-colors">
                              CTRL+ALT
                            </Badge>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">
                          Hold <kbd className="px-1 py-0.5 rounded bg-muted/70 text-[10px] font-mono text-foreground/80 border border-border">Ctrl+Alt</kbd> to dictate live; release for instant answer.
                        </p>
                      </Card>
                    </div>
                  </div>

                  {/* Section: Quick Controls */}
                  <div className="space-y-2 mt-4">
                    <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">Quick Controls</h3>
                    <div className="rounded-xl bg-card border border-border overflow-hidden divide-y divide-border shadow-xs">

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Morning Briefing</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Speak weather and calendar briefing at startup</div>
                        </div>
                        <Switch
                          checked={morningBrief}
                          onCheckedChange={(val) => handleToggle('morning_brief_enabled', val, setMorningBrief)}
                        />
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Auto-Start on Boot</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Launch ZEZO background daemon on Windows startup</div>
                        </div>
                        <Switch
                          checked={autostart}
                          onCheckedChange={(val) => handleToggle('autostart_enabled', val, setAutostart)}
                        />
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Extended Reasoning & Thinking</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Enable step-by-step chain-of-thought rationale before generating responses</div>
                        </div>
                        <Switch
                          checked={thinkingEnabled}
                          onCheckedChange={(val) => handleToggle('thinking_enabled', val, setThinkingEnabled)}
                        />
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Proactive Audio Suggestions</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Allow assistant to proactively provide vocal hints and status updates</div>
                        </div>
                        <Switch
                          checked={proactiveAudioEnabled}
                          onCheckedChange={(val) => handleToggle('proactive_audio_enabled', val, setProactiveAudioEnabled)}
                        />
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* ──────────────── 2. AUDIO & SPEECH ──────────────── */}
              {activeSection === 'audio' && (() => {
                const effectiveAudioDevices = audioDevices?.inputs?.length ? audioDevices : internalAudioDevices
                const inputList = effectiveAudioDevices?.inputs || []
                const outputList = effectiveAudioDevices?.outputs || []

                return (
                  <>
                    <div>
                      <h2 className="text-xl font-bold text-foreground tracking-tight">Audio Settings</h2>
                      <p className="text-xs text-muted-foreground mt-1">
                        Configure physical hardware microphones, speakers, and live endpoint testing.
                      </p>
                    </div>

                    {/* Section: Physical Hardware Endpoints */}
                    <div className="space-y-2">
                      <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">Physical Hardware Endpoints</h3>
                      <div className="rounded-xl bg-card border border-border overflow-hidden divide-y divide-border shadow-xs">
                        {/* Microphone Input Endpoint */}
                        <div className="p-3.5 hover:bg-muted/30 transition-colors space-y-2.5">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div>
                              <div className="text-xs font-semibold text-foreground">Microphone Input Endpoint</div>
                              <div className="text-[11px] text-muted-foreground mt-0.5">Capture user speech from hardware device</div>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="w-56 sm:w-64">
                                <Select
                                  value={selectedInputDev || '__default__'}
                                  onValueChange={(val) => {
                                    const nextVal = val === '__default__' ? '' : val
                                    setSelectedInputDev(nextVal)
                                    if (onSaveAudioDevices && nextVal !== selectedInputDev) {
                                      onSaveAudioDevices(nextVal, selectedOutputDev)
                                    }
                                  }}
                                >
                                  <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs">
                                    <SelectValue placeholder="System Default Microphone" />
                                  </SelectTrigger>
                                  <SelectContent className="bg-popover border-border text-popover-foreground text-xs max-h-56">
                                    <SelectItem value="__default__">System Default Microphone</SelectItem>
                                    {inputList.map((d) => (
                                      <SelectItem key={d.name} value={d.name}>
                                        {d.name}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={handleToggleMicTest}
                                className={cn(
                                  "h-8 px-2.5 text-xs gap-1.5 shrink-0",
                                  isTestingMic && "border-primary text-primary bg-primary/10"
                                )}
                              >
                                <Mic className={cn("w-3.5 h-3.5", isTestingMic && "animate-pulse")} />
                                <span>{isTestingMic ? 'Stop Test' : 'Test Mic'}</span>
                              </Button>
                            </div>
                          </div>

                          {/* Live Interactive Mic Test Meter */}
                          {isTestingMic && (
                            <div className="p-2.5 rounded-lg bg-muted/40 border border-border/80 flex items-center gap-3">
                              <span className="text-[11px] font-mono text-muted-foreground shrink-0">Speak now:</span>
                              <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden relative">
                                <div
                                  className="h-full bg-primary transition-all duration-75 rounded-full"
                                  style={{ width: `${micTestLevel}%` }}
                                />
                              </div>
                              <span className="text-[10px] font-mono text-primary font-semibold w-8 text-right">
                                {micTestLevel}%
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Speaker Output Endpoint */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 hover:bg-muted/30 transition-colors gap-2">
                          <div>
                            <div className="text-xs font-semibold text-foreground">Speaker Output Endpoint</div>
                            <div className="text-[11px] text-muted-foreground mt-0.5">Render assistant audio to audio device</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-56 sm:w-64">
                              <Select
                                value={selectedOutputDev || '__default__'}
                                onValueChange={(val) => {
                                  const nextVal = val === '__default__' ? '' : val
                                  setSelectedOutputDev(nextVal)
                                  if (onSaveAudioDevices && nextVal !== selectedOutputDev) {
                                    onSaveAudioDevices(selectedInputDev, nextVal)
                                  }
                                }}
                              >
                                <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs">
                                  <SelectValue placeholder="System Default Speakers" />
                                </SelectTrigger>
                                <SelectContent className="bg-popover border-border text-popover-foreground text-xs max-h-56">
                                  <SelectItem value="__default__">System Default Speakers</SelectItem>
                                  {outputList.map((d) => (
                                    <SelectItem key={d.name} value={d.name}>
                                      {d.name}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              disabled={isPlayingAudioTest}
                              onClick={handleTestSpeaker}
                              className="h-8 px-2.5 text-xs gap-1.5 shrink-0"
                            >
                              <Volume2 className={cn("w-3.5 h-3.5", isPlayingAudioTest && "text-primary animate-pulse")} />
                              <span>{isPlayingAudioTest ? 'Playing...' : 'Test Audio'}</span>
                            </Button>
                          </div>
                        </div>

                        {/* Self-Echo & Mic Bleed Filter */}
                        <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                          <div>
                            <div className="text-xs font-semibold text-foreground">Self-Echo & Mic Bleed Filter</div>
                            <div className="text-[11px] text-muted-foreground mt-0.5">Filter assistant audio output from being picked up by mic</div>
                          </div>
                          <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10 text-[10px] font-mono">
                            ACTIVE
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </>
                )
              })()}

              {/* ──────────────── 3. PROVIDERS & KEYS ──────────────── */}
              {activeSection === 'providers' && (
                <>
                  <div>
                    <h2 className="text-xl font-bold text-foreground tracking-tight">Providers & API Credentials</h2>
                    <p className="text-xs text-muted-foreground mt-1">
                      Configure multi-provider LLM credentials, fast tool routers, and live search.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">Cloud Providers</h3>
                    <div className="rounded-xl bg-card border border-border overflow-hidden divide-y divide-border shadow-xs">
                      {[
                        {
                          label: 'Google Gemini API Key',
                          desc: 'Used for bidirectional live voice WebSockets & synthesis',
                          placeholder: 'AIzaSy...',
                          value: geminiKey,
                          onChange: setGeminiKey,
                        },
                        {
                          label: 'Groq API Key',
                          desc: 'Sub-100ms background tool calling & router execution',
                          placeholder: 'gsk_...',
                          value: groqKey,
                          onChange: setGroqKey,
                        },
                        {
                          label: 'ElevenLabs API Key',
                          desc: 'High-fidelity voice synthesis engine',
                          placeholder: 'sk_...',
                          value: elevenLabsKey,
                          onChange: setElevenLabsKey,
                        },
                        {
                          label: 'Tavily Web Search Key',
                          desc: 'Live web intelligence and scraping integration',
                          placeholder: 'tvly-...',
                          value: tavilyKey,
                          onChange: setTavilyKey,
                        },
                      ].map((item) => (
                        <ApiKeyInputRow
                          key={item.label}
                          label={item.label}
                          desc={item.desc}
                          placeholder={item.placeholder}
                          value={item.value}
                          onChange={item.onChange}
                        />
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* ──────────────── 4. ASSISTANT PERSONA & AVATAR ──────────────── */}
              {activeSection === 'persona' && (
                <>
                  <div>
                    <h2 className="text-xl font-bold text-foreground tracking-tight">Assistant Persona & Hologram</h2>
                    <p className="text-xs text-muted-foreground mt-1">
                      Customize identity naming, vocal timbre, holographic companion archetype, and particle physics.
                    </p>
                  </div>

                  {/* 1. Vocal & Identity Profile */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">Identity & Profile</h3>
                    <div className="rounded-xl bg-card border border-border overflow-hidden divide-y divide-border shadow-xs">
                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Assistant Name</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Sets the identity and its wake phrase — say "{`Hey ${assistantName}`}" to wake it</div>
                        </div>
                        <div className="w-64 flex items-center gap-1.5">
                          <Select value={assistantName} onValueChange={setAssistantName}>
                            <SelectTrigger className="h-8 flex-1 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Select name" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              {availableAssistantNames.map((n) => (
                                <SelectItem key={n} value={n}>{n}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Live Voice Profile</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Gemini Live speech timbre used during voice conversations</div>
                        </div>
                        <div className="w-64 flex items-center gap-1.5">
                          <Select value={voiceName} onValueChange={setVoiceName}>
                            <SelectTrigger className="h-8 flex-1 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Select voice" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              <SelectItem value="Charon">Charon (Technical & Confident)</SelectItem>
                              <SelectItem value="Puck">Puck (Expressive & Energetic)</SelectItem>
                              <SelectItem value="Kore">Kore (Warm & Reassuring)</SelectItem>
                              <SelectItem value="Fenrir">Fenrir (Authoritative Executive)</SelectItem>
                              <SelectItem value="Aoede">Aoede (Clear & Adaptive)</SelectItem>
                            </SelectContent>
                          </Select>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={isPlayingVoice}
                            onClick={() => handlePreviewVoice(voiceName)}
                            className="h-8 px-2 font-mono text-[10px] shrink-0 gap-1 text-[var(--primary)] border-[var(--primary)]/30 hover:bg-[var(--primary)]/10"
                            title="Preview Voice Sample"
                          >
                            <Volume2 className="w-3.5 h-3.5" />
                            <span>{isPlayingVoice ? 'Playing...' : 'Test'}</span>
                          </Button>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Response Language Mode</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Matches language used in spoken and written answers</div>
                        </div>
                        <div className="w-64">
                          <Select value={responseLanguage} onValueChange={setResponseLanguage}>
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Select language" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              <SelectItem value="auto">Auto-Detect (Matches Speech)</SelectItem>
                              <SelectItem value="English">English (Strict)</SelectItem>
                              <SelectItem value="Urdu">Urdu / Roman Urdu</SelectItem>
                              <SelectItem value="Hindi">Hindi</SelectItem>
                              <SelectItem value="Spanish">Spanish</SelectItem>
                              <SelectItem value="French">French</SelectItem>
                              <SelectItem value="German">German</SelectItem>
                              <SelectItem value="Arabic">Arabic</SelectItem>
                              <SelectItem value="Turkish">Turkish</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 2. Holographic Companion Avatar Customization */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">
                        Holographic Avatar & Character Presets
                      </h3>
                    </div>

                    {/* Live Preview Card + Character Quick Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
                      {/* Left: Mini Live Interactive Preview Box */}
                      <div className="md:col-span-4 rounded-xl bg-card border border-border p-3.5 flex flex-col items-center justify-between relative overflow-hidden group">
                        <div className="w-full flex items-center justify-between z-10">
                          <span className="text-[11px] font-semibold text-foreground/90 tracking-wider uppercase">Live Preview</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-muted text-muted-foreground border border-border">
                            {avatarPreset.toUpperCase()}
                          </span>
                        </div>

                        <div className="my-2 w-32 h-32 relative flex items-center justify-center pointer-events-none">
                          <QiviAvatarVisualizer
                            size={140}
                            characterPreset={avatarPreset}
                            shape={avatarShape}
                            themeName={avatarTheme}
                            quality="high"
                            lighting={avatarLighting}
                            interactive={false}
                          />
                        </div>

                        <div className="w-full text-center z-10 pt-1 border-t border-border">
                          <div className="text-xs font-bold text-foreground capitalize">
                            {AVATAR_CHARACTERS.find((c) => c.id === avatarPreset)?.name || 'Custom Archetype'}
                          </div>
                          <div className="text-[10px] text-muted-foreground truncate mt-0.5">
                            {AVATAR_CHARACTERS.find((c) => c.id === avatarPreset)?.archetype || 'Custom Geometry'}
                          </div>
                        </div>
                      </div>

                      {/* Right: 6 Character Preset Cards */}
                      <div className="md:col-span-8 grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {AVATAR_CHARACTERS.map((char) => {
                          const isSelected = avatarPreset === char.id
                          return (
                            <button
                              key={char.id}
                              type="button"
                              onClick={() => {
                                setAvatarPreset(char.id)
                                setAvatarShape(char.shape)
                                setAvatarTheme(char.theme)
                              }}
                              className={`p-2.5 rounded-xl text-left border transition-all flex flex-col justify-between relative overflow-hidden ${isSelected
                                  ? 'bg-primary/15 border-primary/50 ring-1 ring-primary/40 shadow-xs'
                                  : 'bg-muted/40 border-border/80 hover:border-border hover:bg-muted/70'
                                }`}
                            >
                              <div className="flex items-center justify-between w-full mb-1">
                                <div className="flex items-center gap-1.5">
                                  <span
                                    className="w-2.5 h-2.5 rounded-full ring-2 ring-background"
                                    style={{ backgroundColor: char.color }}
                                  />
                                  <span className="text-xs font-bold text-foreground">{char.name}</span>
                                </div>
                                {isSelected && <CheckCircle className="w-3.5 h-3.5 text-primary" />}
                              </div>
                              <p className="text-[10px] text-muted-foreground leading-tight line-clamp-2 mt-1">
                                {char.desc}
                              </p>
                              <div className="mt-2 text-[9px] font-mono text-muted-foreground uppercase flex items-center justify-between">
                                <span>{char.shape}</span>
                                <span>{char.archetype.split(' ')[0]}</span>
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    </div>

                    {/* Avatar Color & Aura Swatch Grid */}
                    <div className="rounded-xl bg-card border border-border p-3.5 shadow-xs space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Avatar Aura & Color Palette</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Customize the glowing particle cloud aura and eyes</div>
                        </div>
                        <span className="text-[10px] font-mono font-semibold text-foreground px-2 py-0.5 rounded-md bg-muted border border-border uppercase">
                          {AVATAR_THEMES.find((t) => t.id === avatarTheme)?.label || 'Custom'}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {AVATAR_THEMES.map((themeOption) => {
                          const isSelected = avatarTheme === themeOption.id
                          return (
                            <button
                              key={themeOption.id}
                              type="button"
                              onClick={() => {
                                setAvatarTheme(themeOption.id)
                                setAvatarPreset('custom')
                              }}
                              className={`p-2 rounded-xl text-left border transition-all flex items-center gap-2.5 ${isSelected
                                  ? 'bg-primary/15 border-primary/60 ring-1 ring-primary/40 shadow-xs'
                                  : 'bg-muted/40 border-border hover:border-primary/30 hover:bg-muted/70'
                                }`}
                            >
                              <span
                                className="w-3.5 h-3.5 rounded-full ring-2 ring-background shrink-0 shadow-xs"
                                style={{
                                  backgroundColor: themeOption.color.startsWith('var') ? undefined : themeOption.color,
                                  background: themeOption.color.startsWith('var') ? 'var(--primary)' : undefined,
                                  boxShadow: isSelected ? `0 0 10px ${themeOption.color}` : undefined,
                                }}
                              />
                              <div className="min-w-0">
                                <div className="text-xs font-semibold text-foreground truncate">{themeOption.label}</div>
                                <div className="text-[9px] text-muted-foreground truncate">{themeOption.desc.split('&')[0]}</div>
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    </div>

                    {/* Fine-Tuning Controls Container */}
                    <div className="rounded-xl bg-card border border-border overflow-hidden divide-y divide-border shadow-xs">
                      {/* Shape Silhouette Selector */}
                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Silhouette Geometry</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">3D particle mesh boundary and morph silhouette</div>
                        </div>
                        <div className="w-64">
                          <Select
                            value={avatarShape}
                            onValueChange={(val: QiviShape) => {
                              setAvatarShape(val)
                              setAvatarPreset('custom')
                            }}
                          >
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Select Shape" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              {AVATAR_SHAPES.map((s) => (
                                <SelectItem key={s.id} value={s.id}>
                                  {s.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>



                      {/* Quality / Particle Density */}
                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Particle Density & Quality</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Adjust WebGL point cloud density and render tier</div>
                        </div>
                        <div className="w-64">
                          <Select
                            value={avatarQuality}
                            onValueChange={(val: any) => setAvatarQuality(val)}
                          >
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Select Quality" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              <SelectItem value="high">High Density (~2,000 Particles / 60 FPS)</SelectItem>
                              <SelectItem value="medium">Balanced (~1,000 Particles)</SelectItem>
                              <SelectItem value="low">Power-Saving (~500 Particles)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      {/* Lighting & Glow Intensity */}
                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Aura Shader Lighting</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Shader diffuse and specular ambient brightness</div>
                        </div>
                        <div className="w-64 flex items-center gap-2">
                          <input
                            type="range"
                            min="0.3"
                            max="1.3"
                            step="0.05"
                            value={avatarLighting}
                            onChange={(e) => setAvatarLighting(parseFloat(e.target.value))}
                            className="w-full accent-primary h-1.5 bg-input rounded-lg cursor-pointer"
                          />
                          <span className="text-[11px] font-mono text-foreground/80 w-10 text-right">
                            {avatarLighting.toFixed(2)}x
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* ──────────────── 5. APPEARANCE & ACCENTS ──────────────── */}
              {activeSection === 'appearance' && (
                <>
                  <div>
                    <h2 className="text-xl font-bold text-foreground tracking-tight">Appearance & Themes</h2>
                    <p className="text-xs text-muted-foreground mt-1">
                      Choose and customize visual theme styling and accent highlights.
                    </p>
                  </div>

                  {/* Section 1: Themes */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">
                        Themes
                      </h3>
                      <span className="text-[11px] font-mono text-muted-foreground">
                        Active:{' '}
                        <strong className="text-foreground">
                          {THEME_SYSTEMS.find((t) => activeTheme === t.id || activeTheme === `${t.id}-light`)?.name || activeTheme}
                        </strong>
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                      {THEME_SYSTEMS.map((theme) => {
                        const IconComponent = theme.icon
                        const isSelected = activeTheme === theme.id || activeTheme === `${theme.id}-light`

                        return (
                          <Card
                            key={theme.id}
                            onClick={() => handleThemeSelect(theme.id)}
                            className={`p-3 cursor-pointer transition-all duration-150 flex flex-col justify-between gap-2.5 group select-none ${
                              isSelected
                                ? 'border-primary bg-primary/[0.06] ring-1 ring-primary/40 shadow-xs'
                                : 'hover:border-primary/40 hover:bg-muted/40 shadow-2xs'
                            }`}
                          >
                            {/* Top: Icon + Short Name & Status Badge */}
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2 min-w-0">
                                <div
                                  className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 border transition-transform duration-150 group-hover:scale-105"
                                  style={{
                                    backgroundColor: `${theme.previewAccent}15`,
                                    borderColor: `${theme.previewAccent}35`,
                                    color: theme.previewAccent,
                                  }}
                                >
                                  <IconComponent className="w-3.5 h-3.5" />
                                </div>
                                <span className="text-xs font-semibold text-foreground truncate">
                                  {theme.name}
                                </span>
                              </div>

                              {isSelected ? (
                                <Badge variant="default" size="xs" className="shrink-0 gap-1 font-medium bg-primary/15 text-primary border-primary/40">
                                  <Check className="w-2.5 h-2.5" />
                                  ACTIVE
                                </Badge>
                              ) : (
                                <Badge variant="outline" size="xs" className="shrink-0 text-muted-foreground group-hover:text-foreground group-hover:border-primary/40 transition-colors">
                                  APPLY
                                </Badge>
                              )}
                            </div>

                            {/* Bottom: Palette Swatches Bar */}
                            <div className="h-5 w-full rounded-md overflow-hidden flex border border-border/60 shadow-2xs">
                              {theme.swatches.map((color, sIdx) => (
                                <div
                                  key={sIdx}
                                  className="flex-1 h-full transition-opacity hover:opacity-85"
                                  style={{ backgroundColor: color }}
                                  title={color}
                                />
                              ))}
                            </div>
                          </Card>
                        )
                      })}
                    </div>
                  </div>
                </>
              )}



              {/* ──────────────── 7. SKILLS & AUTONOMOUS CAPABILITIES ──────────────── */}
              {activeSection === 'skills' && (
                <SkillsSettingsTab />
              )}

              {/* ──────────────── 8. ABOUT ──────────────── */}
              {activeSection === 'about' && (
                <>
                  <div>
                    <h2 className="text-xl font-bold text-foreground tracking-tight">About ZEZO</h2>
                    <p className="text-xs text-muted-foreground mt-1">
                      Version information and system update status.
                    </p>
                  </div>

                  <div className="rounded-xl bg-card border border-border p-5 space-y-4 shadow-xs">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <div className="text-base font-bold text-foreground">ZEZO</div>
                        <div className="text-xs text-muted-foreground">
                          Created by <span className="font-semibold text-foreground">Hamza Bukhari</span>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10 font-mono text-xs px-2.5 py-1">
                        v2.4.0 • Up to date
                      </Badge>
                    </div>

                    <div className="pt-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span>System is running on the latest version</span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {}}
                        className="h-7 text-xs px-2.5 text-foreground hover:bg-muted"
                      >
                        Check for Updates
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </ScrollArea>
        )}

        </main>
    </div>
  )
}
