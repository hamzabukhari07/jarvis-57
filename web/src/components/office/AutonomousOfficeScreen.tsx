import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import {
  MessageSquare,
  Edit3,
  Folder,
  FolderOpen,
  ChevronDown,
  ChevronUp,
  Copy,
  Trash2,
  X,
  Sliders,
  Check,
  Plus,
  Kanban,
  CheckCircle2,
  Clock,
  AlertCircle,
  Terminal,
  Cpu,
  Shield,
  Zap,
  Sparkles,
  Wrench,
  Boxes,
  Radio,
  ShieldCheck,
  GitBranch,
  LayoutGrid,
  FileText,
  Save,
  User,
  Database,
  Volume2,
  VolumeX,
  Search,
  Play,
  Pause,
} from 'lucide-react'
import { Switch } from '../ui/switch'
import { Frame, FramePanel, FrameHeader, FrameTitle } from '../reui/frame'
import { Card, CardContent } from '../reui/card'
import { Badge } from '../reui/badge'
import { Button } from '../ui/button'
import { ScrollArea } from '../ui/scroll-area'
import { ConfirmDialog } from '../reui/confirm-dialog'
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from '../ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import { Blobatar } from 'blobatar/react'
import 'blobatar/motion.css'
import { AgentDirectChatView } from './AgentDirectChatView'
import { cn } from '@/lib/utils'
import { api } from '../../lib/api'
import type { LogEntry } from '../../hooks/useZezoSocket'

export interface AutonomousOfficeScreenProps {
  backendLogs?: LogEntry[]
}

export interface AgentOfficeMember {
  id: string
  name: string
  role: string
  badge: string
  badgeVariant: 'default' | 'secondary' | 'outline' | 'success' | 'destructive' | 'running' | 'completed' | 'queued'
  color: string
  hairColor: string
  shirtColor: string
  tieColor?: string
  status: 'WORKING' | 'IN_MEETING' | 'WALKING' | 'COFFEE_BREAK' | 'IDLE'
  currentTask: string
  deskPct: { x: number; y: number }
  currentPct: { x: number; y: number }
  targetPct: { x: number; y: number }
  speechBubble?: string
  isTyping?: boolean
  tools: string[]
  logs: string[]
  personality: string
  engine: string
  model: string
  workspace: string
  safetyTier: string
  specialty: string
}

export const WORKSTATION_SLOTS = [
  { id: 'desk-michael', x: 4.1, y: 22.8, defaultAgentId: 'MICHAEL' },
  { id: 'desk-ali', x: 56.7, y: 27.5, defaultAgentId: 'ALI' },
  { id: 'desk-haider', x: 65.8, y: 27.5, defaultAgentId: 'HAIDER' },
  { id: 'desk-ahmad', x: 2.1, y: 52.5, defaultAgentId: 'AHMAD' },
  { id: 'desk-dwight', x: 14.2, y: 52.5, defaultAgentId: 'DWIGHT' },
  { id: 'desk-pam', x: 38.5, y: 52.5, defaultAgentId: 'PAM' },
  { id: 'desk-kelly', x: 50.6, y: 52.5, defaultAgentId: 'KELLY' },
  { id: 'desk-quantum', x: 62.7, y: 52.5, defaultAgentId: 'QUANTUM' },
  { id: 'desk-devdynamo', x: 2.1, y: 79.2, defaultAgentId: 'DEVDYNAMO' },
  { id: 'desk-dataeinstein', x: 26.3, y: 79.2, defaultAgentId: 'DATAEINSTEIN' },
  { id: 'desk-annex-1', x: 79.1, y: 16.0 },
  { id: 'desk-annex-2', x: 88.2, y: 16.0 },
  { id: 'desk-r1-3', x: 26.3, y: 52.5 },
  { id: 'desk-r2-2', x: 14.2, y: 79.2 },
  { id: 'desk-r2-4', x: 38.5, y: 79.2 },
  { id: 'desk-r2-5', x: 50.6, y: 79.2 },
  { id: 'desk-r2-6', x: 62.7, y: 79.2 },
  { id: 'desk-r2-7', x: 74.8, y: 79.2 },
]

export function mapRawAgentToOfficeMember(
  raw: any,
  index: number,
  prevAgent?: AgentOfficeMember
): AgentOfficeMember {
  const slot = WORKSTATION_SLOTS[index % WORKSTATION_SLOTS.length]
  const deskPct = {
    x: Number((slot.x + 3.9).toFixed(1)),
    y: Number((slot.y + 8.8).toFixed(1)),
  }

  const id = String(raw.id || `agent-${index + 1}`)
  const name = String(raw.name || id)
  const role = String(raw.role || 'Autonomous Specialist')
  const statusStr = String(raw.status || 'idle').toLowerCase()
  const isWorking = statusStr === 'working' || raw.isBusy === true

  const status: AgentOfficeMember['status'] = isWorking
    ? 'WORKING'
    : prevAgent?.status === 'IN_MEETING' ||
      prevAgent?.status === 'COFFEE_BREAK' ||
      prevAgent?.status === 'WALKING'
    ? prevAgent.status
    : 'IDLE'

  const currentPct = prevAgent?.currentPct || deskPct
  const targetPct = prevAgent?.targetPct || deskPct

  const taskTitle = raw.task_title || raw.current_task_title || ''
  const speechBubble = isWorking
    ? taskTitle
      ? taskTitle.slice(0, 36)
      : 'Executing autonomous task...'
    : prevAgent?.speechBubble

  const logs: string[] =
    Array.isArray(raw.logs) && raw.logs.length > 0
      ? raw.logs
      : Array.isArray(raw.recent_logs) && raw.recent_logs.length > 0
      ? raw.recent_logs
      : [
          `[READY] Agent '${name}' online in autonomous fleet`,
          `[ENGINE] ${raw.default_tool || 'opencode_run'} | Model: ${raw.model_id || 'default'}`,
          `[STATUS] Standby on office deck`,
        ]

  return {
    id,
    name,
    role,
    badge: id.toUpperCase().slice(0, 8),
    badgeVariant: isWorking ? 'running' : 'default',
    color: raw.color || '#3b82f6',
    hairColor: '#2b2926',
    shirtColor: raw.color || '#3b82f6',
    status,
    currentTask: taskTitle || raw.specialty || 'Standby for instructions',
    deskPct,
    currentPct,
    targetPct,
    speechBubble,
    isTyping: isWorking,
    tools:
      Array.isArray(raw.allowed_tools) && raw.allowed_tools.length > 0
        ? raw.allowed_tools
        : raw.default_tool
        ? [raw.default_tool]
        : ['opencode_run'],
    logs,
    personality: raw.prompt_prefix || `You are ${name}, ${role}.`,
    engine: raw.default_tool || prevAgent?.engine || 'opencode_run',
    model: raw.model_id || prevAgent?.model || 'gemini-2.5-flash',
    workspace: raw.active_worktree || raw.worktree || 'repo_active',
    safetyTier: raw.risk_tier || 'L1_MUTATION',
    specialty: raw.specialty || `${raw.default_tool || prevAgent?.engine || 'opencode_run'}, ${role}`,
  }
}

const INITIAL_AGENTS: AgentOfficeMember[] = [
  {
    id: 'MICHAEL',
    name: 'Michael',
    role: 'Lead Software Architect & Tech Lead',
    badge: 'LEAD',
    badgeVariant: 'default',
    color: '#a855f7',
    hairColor: '#2b2926',
    shirtColor: '#a855f7',
    status: 'IDLE',
    currentTask: 'High-level architecture design, code review, and structural planning',
    deskPct: { x: 8.0, y: 31.6 },
    currentPct: { x: 8.0, y: 31.6 },
    targetPct: { x: 8.0, y: 31.6 },
    speechBubble: 'Autonomous fleet standing by.',
    isTyping: false,
    tools: ['opencode_run', 'web_search', 'file_processor', 'extract_design_system'],
    logs: [
      '[READY] Agent Michael online in autonomous fleet',
      '[ENGINE] opencode_run | Model: opencode/fledge-alpha-free',
      '[STATUS] Standby on office deck',
    ],
    personality: 'You are Michael, Lead Software Architect & Tech Lead of the Autonomous Coding Fleet.',
    engine: 'opencode_run',
    model: 'opencode/fledge-alpha-free',
    workspace: 'repo_active',
    safetyTier: 'L1_MUTATION',
    specialty: 'High-level architecture design, code review, and structural planning',
  },
  {
    id: 'ALI',
    name: 'Verve',
    role: 'Frontend & UI Design Specialist',
    badge: 'FRONTEND',
    badgeVariant: 'default',
    color: '#ec4899',
    hairColor: '#2b2926',
    shirtColor: '#ec4899',
    status: 'IDLE',
    currentTask: 'Responsive web apps, Tailwind/CSS layouts, animations, and studio-grade interfaces',
    deskPct: { x: 60.6, y: 36.3 },
    currentPct: { x: 60.6, y: 36.3 },
    targetPct: { x: 60.6, y: 36.3 },
    speechBubble: undefined,
    isTyping: false,
    tools: ['antigravity_run', 'extract_design_system', 'file_processor', 'browser_control'],
    logs: [
      '[READY] Agent Verve online in autonomous fleet',
      '[ENGINE] antigravity_run | Model: gemini-3.7-flash-medium',
      '[STATUS] Standby on office deck',
    ],
    personality: 'You are Ali, Senior Frontend and UI Architecture Specialist. Build pixel-perfect, modern, accessible, and responsive user interfaces.',
    engine: 'antigravity_run',
    model: 'gemini-3.7-flash-medium',
    workspace: 'repo_active',
    safetyTier: 'L1_MUTATION',
    specialty: 'Responsive web apps, Tailwind/CSS layouts, animations, and studio-grade interfaces',
  },
  {
    id: 'HAIDER',
    name: 'Flux',
    role: 'Frontend Specialist & Overflow Developer',
    badge: 'FRONTEND',
    badgeVariant: 'default',
    color: '#f43f5e',
    hairColor: '#2b2926',
    shirtColor: '#f43f5e',
    status: 'IDLE',
    currentTask: 'Modern web applications, component architecture, and fast UI synthesis',
    deskPct: { x: 69.7, y: 36.3 },
    currentPct: { x: 69.7, y: 36.3 },
    targetPct: { x: 69.7, y: 36.3 },
    speechBubble: undefined,
    isTyping: false,
    tools: ['antigravity_run', 'extract_design_system', 'file_processor'],
    logs: [
      '[READY] Agent Flux online in autonomous fleet',
      '[ENGINE] antigravity_run | Model: gemini-3.8-flash-low',
      '[STATUS] Standby on office deck',
    ],
    personality: 'You are Haider, Frontend Specialist and UI Developer. Clean responsive aesthetic user interfaces.',
    engine: 'antigravity_run',
    model: 'gemini-3.8-flash-low',
    workspace: 'repo_active',
    safetyTier: 'L1_MUTATION',
    specialty: 'Modern web applications, component architecture, responsive styling',
  },
  {
    id: 'AHMAD',
    name: 'Nexus',
    role: 'Full-Stack & Backend Specialist',
    badge: 'BACKEND',
    badgeVariant: 'default',
    color: '#06b6d4',
    hairColor: '#2b2926',
    shirtColor: '#06b6d4',
    status: 'IDLE',
    currentTask: 'FastAPI, PostgreSQL, microservices, complex business logic, and database schemas',
    deskPct: { x: 6.0, y: 61.3 },
    currentPct: { x: 6.0, y: 61.3 },
    targetPct: { x: 6.0, y: 61.3 },
    speechBubble: undefined,
    isTyping: false,
    tools: ['opencode_run', 'file_processor', 'file_controller'],
    logs: [
      '[READY] Agent Nexus online in autonomous fleet',
      '[ENGINE] opencode_run | Model: opencode/nemotron-3-ultra-free',
      '[STATUS] Standby on office deck',
    ],
    personality: 'You are Ahmad, Senior Python Backend Specialist. Build scalable backend architectures and bulletproof models.',
    engine: 'opencode_run',
    model: 'opencode/nemotron-3-ultra-free',
    workspace: 'repo_active',
    safetyTier: 'L2_DESTRUCTIVE',
    specialty: 'FastAPI, PostgreSQL, microservices, complex business logic, and database schemas',
  },
  {
    id: 'DWIGHT',
    name: 'Dwight',
    role: 'Senior Refactoring & QA Specialist',
    badge: 'QA_SEC',
    badgeVariant: 'default',
    color: '#eab308',
    hairColor: '#2b2926',
    shirtColor: '#eab308',
    status: 'IDLE',
    currentTask: 'Multi-file refactoring, test suites, edge-case audit, and clean architecture',
    deskPct: { x: 18.1, y: 61.3 },
    currentPct: { x: 18.1, y: 61.3 },
    targetPct: { x: 18.1, y: 61.3 },
    speechBubble: undefined,
    isTyping: false,
    tools: ['kilo_run', 'file_processor', 'file_controller'],
    logs: [
      '[READY] Agent Dwight online in autonomous fleet',
      '[ENGINE] kilo_run | Model: kilo/stepfun/step-3.7-flash:free',
      '[STATUS] Standby on office deck',
    ],
    personality: 'You are Dwight Schrute, Senior Refactoring & QA Specialist. Ensure codebases are robust and cleanly tested.',
    engine: 'kilo_run',
    model: 'kilo/stepfun/step-3.7-flash:free',
    workspace: 'repo_active',
    safetyTier: 'L1_MUTATION',
    specialty: 'Multi-file refactoring, test suites, edge-case audit, and clean architecture',
  },
  {
    id: 'PAM',
    name: 'Pam Beesly',
    role: 'Design System & Token Architect',
    badge: 'TOKENS',
    badgeVariant: 'default',
    color: '#a855f7',
    hairColor: '#2b2926',
    shirtColor: '#a855f7',
    status: 'IDLE',
    currentTask: 'Design token extraction, visual branding, and HUD metrics rendering',
    deskPct: { x: 42.4, y: 61.3 },
    currentPct: { x: 42.4, y: 61.3 },
    targetPct: { x: 42.4, y: 61.3 },
    speechBubble: undefined,
    isTyping: false,
    tools: ['extract_design_system', 'file_processor', 'file_controller'],
    logs: [
      '[READY] Agent Pam online in autonomous fleet',
      '[ENGINE] extract_design_system | Model: gemini-2.5-flash',
      '[STATUS] Standby on office deck',
    ],
    personality: 'You are Pam Beesly, Design System Architect. Ensure UI components are pixel-perfect and accessible.',
    engine: 'extract_design_system',
    model: 'gemini-2.5-flash',
    workspace: 'repo_active',
    safetyTier: 'L0_READ_ONLY',
    specialty: 'Design token extraction, visual branding, and HUD metrics rendering',
  },
  {
    id: 'KELLY',
    name: 'Kelly Kapoor',
    role: 'Social & Deep Web Researcher',
    badge: 'RESEARCH',
    badgeVariant: 'default',
    color: '#e11d48',
    hairColor: '#2b2926',
    shirtColor: '#e11d48',
    status: 'IDLE',
    currentTask: 'YouTube, Reddit, social trends, and deep content research',
    deskPct: { x: 54.5, y: 61.3 },
    currentPct: { x: 54.5, y: 61.3 },
    targetPct: { x: 54.5, y: 61.3 },
    speechBubble: undefined,
    isTyping: false,
    tools: ['agent_reach', 'web_search', 'web_reader', 'youtube_video'],
    logs: [
      '[READY] Agent Kelly online in autonomous fleet',
      '[ENGINE] agent_reach | Model: gemini-2.5-flash',
      '[STATUS] Standby on office deck',
    ],
    personality: 'You are Kelly Kapoor, Research & Social Intelligence Specialist. Find trends and deep research.',
    engine: 'agent_reach',
    model: 'gemini-2.5-flash',
    workspace: 'repo_active',
    safetyTier: 'L0_READ_ONLY',
    specialty: 'YouTube, Reddit, social trends, and deep content research',
  },
  {
    id: 'QUANTUM',
    name: 'Quantum',
    role: 'Detailed Web Researcher',
    badge: 'SCRAPER',
    badgeVariant: 'default',
    color: '#3b82f6',
    hairColor: '#2b2926',
    shirtColor: '#3b82f6',
    status: 'IDLE',
    currentTask: 'Deep web research and analysis',
    deskPct: { x: 66.6, y: 61.3 },
    currentPct: { x: 66.6, y: 61.3 },
    targetPct: { x: 66.6, y: 61.3 },
    speechBubble: undefined,
    isTyping: false,
    tools: ['web_search', 'agent_reach', 'web_reader'],
    logs: [
      '[READY] Agent Quantum online in autonomous fleet',
      '[ENGINE] kilo_run | Model: kilo/kilo-auto/free',
      '[STATUS] Standby on office deck',
    ],
    personality: 'You are Quantum, an autonomous fleet specialist focusing on deep web research and analysis.',
    engine: 'kilo_run',
    model: 'kilo/kilo-auto/free',
    workspace: 'repo_active',
    safetyTier: 'L1_MUTATION',
    specialty: 'Deep web research and analysis',
  },
  {
    id: 'DEVDYNAMO',
    name: 'DevDynamo',
    role: 'Full-Stack Developer & Autonomous Engineer',
    badge: 'DEV',
    badgeVariant: 'default',
    color: '#3b82f6',
    hairColor: '#2b2926',
    shirtColor: '#3b82f6',
    status: 'IDLE',
    currentTask: 'Full-stack development, modern web engineering, and autonomous task execution',
    deskPct: { x: 6.0, y: 88.0 },
    currentPct: { x: 6.0, y: 88.0 },
    targetPct: { x: 6.0, y: 88.0 },
    speechBubble: undefined,
    isTyping: false,
    tools: ['agent_reach', 'web_search', 'web_read_page', 'file_processor'],
    logs: [
      '[READY] Agent DevDynamo online in autonomous fleet',
      '[ENGINE] opencode_run | Model: default',
      '[STATUS] Standby on office deck',
    ],
    personality: 'You are DevDynamo, an autonomous fleet specialist focusing on Full-stack development.',
    engine: 'opencode_run',
    model: 'opencode/fledge-alpha-free',
    workspace: 'repo_active',
    safetyTier: 'L1_MUTATION',
    specialty: 'Full-stack development, modern web engineering, and autonomous task execution',
  },
  {
    id: 'DATAEINSTEIN',
    name: 'InsightAI',
    role: 'Data Scientist & AI Specialist',
    badge: 'AI_DATA',
    badgeVariant: 'default',
    color: '#3b82f6',
    hairColor: '#2b2926',
    shirtColor: '#3b82f6',
    status: 'IDLE',
    currentTask: 'Machine Learning, Data Analysis, Predictive Modeling',
    deskPct: { x: 30.2, y: 88.0 },
    currentPct: { x: 30.2, y: 88.0 },
    targetPct: { x: 30.2, y: 88.0 },
    speechBubble: undefined,
    isTyping: false,
    tools: ['opencode_run', 'file_processor', 'file_controller'],
    logs: [
      '[READY] Agent InsightAI online in autonomous fleet',
      '[ENGINE] antigravity_run | Model: gemini-3.8-flash-low',
      '[STATUS] Standby on office deck',
    ],
    personality: 'You are Dataeinstein, an autonomous fleet specialist focusing on Machine Learning and Data Analysis.',
    engine: 'antigravity_run',
    model: 'gemini-3.8-flash-low',
    workspace: 'repo_active',
    safetyTier: 'L1_MUTATION',
    specialty: 'Machine Learning, Data Analysis, Predictive Modeling',
  },
]
// Web Audio Foley Synthesizer (Retro Micro-Foley)
let globalAudioCtx: AudioContext | null = null

function playOfficeFoley(type: 'click' | 'keystroke' | 'alert' | 'coffee' | 'success', enabled: boolean = true) {
  if (!enabled || typeof window === 'undefined') return
  try {
    if (!globalAudioCtx) {
      const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      if (AudioCtxClass) globalAudioCtx = new AudioCtxClass()
    }
    if (!globalAudioCtx) return
    if (globalAudioCtx.state === 'suspended') {
      globalAudioCtx.resume()
    }

    const now = globalAudioCtx.currentTime
    const osc = globalAudioCtx.createOscillator()
    const gain = globalAudioCtx.createGain()
    osc.connect(gain)
    gain.connect(globalAudioCtx.destination)

    if (type === 'click' || type === 'keystroke') {
      osc.type = 'triangle'
      osc.frequency.setValueAtTime(600 + Math.random() * 200, now)
      osc.frequency.exponentialRampToValueAtTime(100, now + 0.04)
      gain.gain.setValueAtTime(0.08, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04)
      osc.start(now)
      osc.stop(now + 0.04)
    } else if (type === 'alert') {
      osc.type = 'sawtooth'
      osc.frequency.setValueAtTime(440, now)
      osc.frequency.linearRampToValueAtTime(880, now + 0.15)
      gain.gain.setValueAtTime(0.12, now)
      gain.gain.linearRampToValueAtTime(0.01, now + 0.2)
      osc.start(now)
      osc.stop(now + 0.2)
    } else if (type === 'coffee') {
      osc.type = 'sine'
      osc.frequency.setValueAtTime(250, now)
      osc.frequency.exponentialRampToValueAtTime(450, now + 0.08)
      gain.gain.setValueAtTime(0.09, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08)
      osc.start(now)
      osc.stop(now + 0.08)
    } else if (type === 'success') {
      osc.type = 'triangle'
      osc.frequency.setValueAtTime(523.25, now) // C5
      osc.frequency.setValueAtTime(659.25, now + 0.08) // E5
      osc.frequency.setValueAtTime(783.99, now + 0.16) // G5
      gain.gain.setValueAtTime(0.1, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3)
      osc.start(now)
      osc.stop(now + 0.3)
    }
  } catch (err) {
    console.debug('Audio foley unavailable:', err)
  }
}

// Helper label formatters for Agent Environment fields
function getEngineLabel(val: string) {
  switch (val) {
    case 'opencode_run': return 'OpenCode'
    case 'kilo_run': return 'KiloCode'
    case 'antigravity_run': return 'Antigravity'
    case 'groq': return 'Groq'
    default: return val
  }
}

function getWorkspaceLabel(val: string) {
  switch (val) {
    case 'repo_active': return 'Active Repo (jarvis-57)'
    case 'desktop_root': return 'Desktop / Root'
    case 'web_sandbox': return 'Sandbox Isolated'
    case 'ui_tokens': return 'UI / Tokens (web/src)'
    case 'daemon_ring': return 'Background Daemon Ring'
    case 'sqlite_db': return 'memory/zezo_brain.db'
    case 'config_secrets': return 'config/api_keys.json'
    case 'human_gate': return 'Human Gate / Audit Stack'
    default: return val
  }
}

export const ENGINE_MODELS_MAP: Record<string, { id: string; label: string }[]> = {
  opencode_run: [
    { id: 'opencode/big-pickle', label: 'Big Pickle (Specialized Coding)' },
    { id: 'opencode/nemotron-3-ultra-free', label: 'NVIDIA Nemotron 3 Ultra (Free)' },
    { id: 'opencode/nemotron-3.5-lightning-free', label: 'NVIDIA Nemotron Lightning (Free)' },
    { id: 'opencode/fledge-alpha-free', label: 'Fledge Alpha Reasoning (Free)' },
    { id: 'opencode/mimo-v2.6-flash-free', label: 'Xiaomi Mimo Flash (Free)' },
    { id: 'opencode/ling-3.1-flash-free', label: 'Ling 3.1 Flash (Multimodal)' },
    { id: 'opencode/space-bunny-free', label: 'Space Bunny Agile (Free)' },
    { id: 'opencode/longcat-2.5-preview-free', label: 'Longcat 2.5 Extended (Free)' },
    { id: 'opencode/muse-spark-1.3-contributor-free', label: 'Muse Spark Contributor (Free)' },
  ],
  kilo_run: [
    { id: 'kilo/kilo-auto/free', label: 'Kilo Auto Free (Dynamic Router)' },
    { id: 'kilo/dots-studio/dots-3-note-preview:free', label: 'Dots-3 Note Preview (Free)' },
    { id: 'kilo/inclusionai/ling-3.0-flash-vl:free', label: 'Ling 3.0 Flash VL (Free)' },
    { id: 'kilo/nex-agi/nex-n2.5-pro:free', label: 'Nex AGI Nex-N2.5-Pro (Free)' },
    { id: 'kilo/nvidia/nemotron-3-ultra-550b-a55b:free', label: 'NVIDIA Nemotron 3 Ultra (Free)' },
    { id: 'kilo/stepfun/step-3.7-flash:free', label: 'StepFun Step 3.7 Flash (Free)' },
  ],
  antigravity_run: [
    { id: 'gemini-3.8-flash-high', label: 'Gemini 3.8 Flash (High)' },
    { id: 'gemini-3.8-flash-medium', label: 'Gemini 3.8 Flash (Medium)' },
    { id: 'gemini-3.8-flash-low', label: 'Gemini 3.8 Flash (Low)' },
    { id: 'gemini-3.7-flash-medium', label: 'Gemini 3.7 Flash (Medium)' },
    { id: 'gemini-3.1-pro-high', label: 'Gemini 3.1 Pro (High)' },
    { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 (Thinking)' },
    { id: 'claude-opus-4-6-thinking', label: 'Claude Opus 4.6 (Thinking)' },
  ],
  groq: [
    { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B Versatile' },
    { id: 'deepseek-r1-distill-llama-70b', label: 'DeepSeek R1 Distill Llama 70B' },
    { id: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B 32k' },
    { id: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B Instant' },
  ],
}

function getModelLabel(val: string) {
  for (const list of Object.values(ENGINE_MODELS_MAP)) {
    const found = list.find((m) => m.id === val)
    if (found) return found.label
  }
  switch (val) {
    case 'gemini-2.5-flash': return 'Gemini 2.5 Flash'
    case 'gemini-3.1-flash-live': return 'Gemini 3.1 Live Preview'
    case 'groq/llama-3.3-70b-versatile': return 'Groq Llama-3.3-70B'
    case 'opencode/space-bunny-free': return 'OpenCode Free Tier'
    case 'cron-engine': return 'Cron Engine'
    case 'fts5-bm25': return 'SQLite BM25 Engine'
    case 'safety-gate': return 'Safety Gate Tier'
    default: return val
  }
}

function getSafetyTierLabel(val: string) {
  switch (val) {
    case 'L0_READ_ONLY': return 'Read-Only (L0)'
    case 'L1_MUTATION': return 'Standard Edit (L1)'
    case 'L2_DESTRUCTIVE': return 'Full Destructive (L2)'
    default: return val
  }
}

const AVATAR_PRESETS = [
  'Andy',
  'Creed',
  'Erin',
  'Darryl',
  'Phyllis',
  'Meredith',
  'Kelly',
  'Clark',
  'Nate',
  'Nellie',
]

interface SkillDefinition {
  id: string
  name: string
  desc: string
}

interface ToolDefinition {
  id: string
  name: string
  desc: string
}

const AVAILABLE_SKILLS: SkillDefinition[] = [
  { id: 'hamza_taste', name: 'hamza_taste', desc: 'Studio UI aesthetic, anti-slop rules & design presets' },
  { id: 'opencode', name: 'opencode', desc: 'Full autonomous multi-file coding workflow' },
  { id: 'kilo_code', name: 'kilo_code', desc: 'Free-tier fast refactoring & edits' },
  { id: 'antigravity_agent', name: 'antigravity_agent', desc: 'Agentic code synthesis & studio UI' },
  { id: 'git_workflow', name: 'git_workflow', desc: 'Professional Git staging & commit workflow' },
  { id: 'social_research', name: 'social_research', desc: 'YouTube, Reddit & GitHub research pipeline' },
  { id: 'system_diagnostics', name: 'system_diagnostics', desc: 'Hardware telemetry & diagnostic routine' },
  { id: 'web_scraper', name: 'web_scraper', desc: 'Anti-bot web extraction pipeline' },
  { id: 'web_research_pipeline', name: 'web_research_pipeline', desc: 'Query decomposition & deep research' },
  { id: 'test_fastapi_deploy', name: 'test_fastapi_deploy', desc: 'Backend deployment verification' },
]

const AVAILABLE_TOOLS: ToolDefinition[] = [
  { id: 'opencode_run', name: 'opencode_run', desc: 'Autonomous multi-file coding agent' },
  { id: 'kilo_run', name: 'kilo_run', desc: 'Free-tier fast refactoring agent' },
  { id: 'antigravity_run', name: 'antigravity_run', desc: 'Studio UI & Antigravity synthesis' },
  { id: 'groq', name: 'groq', desc: 'Ultra-fast Groq LLM inference' },
  { id: 'code_helper', name: 'code_helper', desc: 'Single function / snippet generator' },
  { id: 'file_controller', name: 'file_controller', desc: 'File/folder CRUD, search, organization' },
  { id: 'file_processor', name: 'file_processor', desc: 'File reading, parsing, batch edits' },
  { id: 'web_search', name: 'web_search', desc: 'Google / DuckDuckGo live search' },
  { id: 'web_reader', name: 'web_reader', desc: 'Deep web scraping & markdown extraction' },
  { id: 'browser_control', name: 'browser_control', desc: 'Browser tab navigation & interactions' },
  { id: 'computer_control', name: 'computer_control', desc: 'Keyboard shortcuts, clicks, hotkeys' },
  { id: 'screen_process', name: 'screen_process', desc: 'Desktop screenshot capture & analysis' },
  { id: 'system_monitor', name: 'system_monitor', desc: 'Live CPU, RAM, GPU, battery metrics' },
  { id: 'background_monitor', name: 'background_monitor', desc: 'Long-running process surveillance' },
  { id: 'open_app', name: 'open_app', desc: 'Launch / terminate desktop apps & files' },
]

export type CorePersonaFileKey = 'SOUL.md' | 'AGENTS.md' | 'PROFILE.md' | 'MEMORY.md'

export interface CorePersonaFileItem {
  id: CorePersonaFileKey
  name: CorePersonaFileKey
  desc: string
  iconColor: string
  badgeText: string
  badgeVariant: 'default' | 'secondary' | 'outline' | 'success' | 'destructive' | 'running'
}

export const CORE_PERSONA_FILES: CorePersonaFileItem[] = [
  {
    id: 'SOUL.md',
    name: 'SOUL.md',
    desc: 'Persona & prompt rules',
    iconColor: 'text-amber-400',
    badgeText: 'SOUL / PROMPT',
    badgeVariant: 'running',
  },
  {
    id: 'AGENTS.md',
    name: 'AGENTS.md',
    desc: 'System constraints & QA',
    iconColor: 'text-cyan-400',
    badgeText: 'GOVERNANCE',
    badgeVariant: 'outline',
  },
  {
    id: 'PROFILE.md',
    name: 'PROFILE.md',
    desc: 'Expertise & backstory',
    iconColor: 'text-yellow-400',
    badgeText: 'PROFILE',
    badgeVariant: 'secondary',
  },
  {
    id: 'MEMORY.md',
    name: 'MEMORY.md',
    desc: 'Episodic memory palace',
    iconColor: 'text-purple-400',
    badgeText: 'MEMORY FTS5',
    badgeVariant: 'default',
  },
]

export function getPersonaFileContent(
  fileKey: CorePersonaFileKey,
  agent: AgentOfficeMember,
  overrides?: Partial<Record<CorePersonaFileKey, string>>
): string {
  if (overrides && overrides[fileKey] !== undefined) {
    return overrides[fileKey]!
  }
  switch (fileKey) {
    case 'SOUL.md':
      return agent.personality || `You are ${agent.name}, an autonomous specialist operating under Zezo OS.\nRole: ${agent.role}\nEngine: ${agent.engine}\nModel: ${agent.model}\n\nInstructions:\n- Adhere strictly to antislop rules and clean concise reasoning.\n- Always keep cyclomatic complexity < 15.`
    case 'AGENTS.md':
      return `# AGENTS.md — System Context for ${agent.name}\n\n- Always prioritize code correctness, security, and safety.\n- Target OS: Windows (Primary), macOS, Linux.\n- Enforce cyclomatic complexity < 15.\n- No decorative comments or bloated boilerplate.\n- Use 3-Layer verification (Static, Runtime, Regression) before reporting completion.\n- Clean-room integration standards enforced.`
    case 'PROFILE.md':
      return `# PROFILE.md — ${agent.name}\n\n- Name: ${agent.name}\n- Role: ${agent.role}\n- Status: ${agent.status}\n- Risk Tier: ${agent.safetyTier || 'L1_MUTATION'}\n- Primary Engine: ${agent.engine}\n- Target Model: ${agent.model}\n- Specialty: ${agent.specialty || 'Full-stack autonomous execution'}\n- Workspace: ${agent.workspace === 'repo_active' ? 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57' : agent.workspace}`
    case 'MEMORY.md':
      return `# MEMORY.md — Episodic Context for ${agent.name}\n\n- Workspace Mount: ${agent.workspace === 'repo_active' ? 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57' : agent.workspace}\n- Memory Palace: SQLite FTS5 (zezo_brain.db) active with BM25 vector search.\n- Recent Episodic Events:\n${agent.logs.map((log) => `  * ${log}`).join('\n')}`
  }
}

export const AutonomousOfficeScreen: React.FC<AutonomousOfficeScreenProps> = ({ backendLogs = [] }) => {
  const [agents, setAgents] = useState<AgentOfficeMember[]>(INITIAL_AGENTS)
  const [selectedAgentId, setSelectedAgentId] = useState<string>('MICHAEL')
  const [internalLogs, setInternalLogs] = useState<LogEntry[]>([])
  const [logFilterMode, setLogFilterMode] = useState<'agent' | 'errors'>('agent')
  const [logSearchQuery, setLogSearchQuery] = useState('')
  const [autoFollowLogs, setAutoFollowLogs] = useState(true)
  const logsEndRef = useRef<HTMLDivElement>(null)

  // Fetch initial logs snapshot from backend API
  useEffect(() => {
    api.getBackendLogs().then((res) => {
      if (res && Array.isArray(res.lines) && res.lines.length > 0) {
        const formatted: LogEntry[] = res.lines.map((line: any, idx: number) => {
          if (typeof line === 'string') {
            return {
              id: `init-${idx}`,
              time: new Date().toLocaleTimeString(),
              source: 'SYS',
              text: line,
              type: line.includes('ERROR') ? 'ERROR' : line.includes('WARN') ? 'WARNING' : 'INFO',
              level: line.includes('ERROR') ? 'ERROR' : line.includes('WARN') ? 'WARNING' : 'INFO',
            }
          }
          const rawLvl = (line.level || line.type || 'INFO').toUpperCase()
          return {
            id: line.id || (line.seq !== undefined ? `init-${line.seq}` : `init-${idx}`),
            time: line.time || line.timestamp || line.ts || new Date().toLocaleTimeString(),
            source: (line.source || line.logger || line.src || 'SYS').toUpperCase(),
            text: line.text || line.message || line.msg || '',
            type: rawLvl,
            level: rawLvl,
          }
        })
        setInternalLogs(formatted)
      }
    }).catch(() => {})
  }, [])

  const loadFleet = useCallback(async () => {
    try {
      const res = await api.getFleetState()
      const rawList = res.fleet || (res.agents ? Object.values(res.agents) : [])
      if (rawList && rawList.length > 0) {
        setAgents((prev) => {
          const prevMap = new Map(prev.map((a) => [a.id, a]))
          return rawList.map((raw, idx) => mapRawAgentToOfficeMember(raw, idx, prevMap.get(raw.id)))
        })
      }
    } catch (e) {
      console.debug('Failed to fetch fleet state:', e)
    }
  }, [])

  useEffect(() => {
    loadFleet()
    const handleUpdate = () => {
      loadFleet()
    }
    window.addEventListener('zezo_fleet_updated', handleUpdate)
    const interval = setInterval(loadFleet, 4000)
    return () => {
      window.removeEventListener('zezo_fleet_updated', handleUpdate)
      clearInterval(interval)
    }
  }, [loadFleet])

  const [agentToDismiss, setAgentToDismiss] = useState<AgentOfficeMember | null>(null)
  const [isDismissing, setIsDismissing] = useState(false)

  const handleConfirmDismissAgent = async () => {
    if (!agentToDismiss) return
    setIsDismissing(true)
    try {
      await api.deleteAgent(agentToDismiss.id)
      try {
        localStorage.removeItem(`zezo_agent_threads_${agentToDismiss.id}`)
      } catch {
        // ignore storage errors
      }
      triggerToast(`Agent ${agentToDismiss.name} dismissed from fleet`)
      const remaining = agents.filter((a) => a.id !== agentToDismiss.id)
      setAgents(remaining)
      if (remaining.length > 0) setSelectedAgentId(remaining[0].id)
      setAgentToDismiss(null)
      loadFleet()
    } catch (err) {
      console.error('Failed to delete agent:', err)
    } finally {
      setIsDismissing(false)
    }
  }
  const [isEnvDrawerOpen, setIsEnvDrawerOpen] = useState(true)
  const [copiedLogs, setCopiedLogs] = useState(false)
  const [officeMode, setOfficeMode] = useState<'spatial' | 'matrix' | 'kanban' | 'chat'>('spatial')
  const [matrixFilter, setMatrixFilter] = useState<'ALL' | 'WORKING' | 'IDLE' | 'REVIEW'>('ALL')
  const [isAddAgentOpen, setIsAddAgentOpen] = useState(false)
  const [newAgentName, setNewAgentName] = useState('')
  const [newAgentRole, setNewAgentRole] = useState('')
  const [newAgentAvatar, setNewAgentAvatar] = useState('Andy')
  const [newAgentInstructions, setNewAgentInstructions] = useState('')
  const [newAgentWorkspace, setNewAgentWorkspace] = useState('c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57')
  const [newAgentEngine, setNewAgentEngine] = useState('opencode_run')
  const [newAgentModel, setNewAgentModel] = useState('gemini-2.5-flash')
  const [newAgentSelectedTools, setNewAgentSelectedTools] = useState<string[]>([
    'file_controller',
    'web_search',
  ])
  const [newAgentSelectedSkills, setNewAgentSelectedSkills] = useState<string[]>([
    'opencode',
    'hamza_taste',
  ])
  const folderInputRef = useRef<HTMLInputElement>(null)

  // Edit Agent Modal State
  const [isEditAgentOpen, setIsEditAgentOpen] = useState(false)
  const [editAgentName, setEditAgentName] = useState('')
  const [editAgentRole, setEditAgentRole] = useState('')
  const [editAgentPersonality, setEditAgentPersonality] = useState('')
  const [editAgentWorkspace, setEditAgentWorkspace] = useState('c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57')
  const [editAgentEngine, setEditAgentEngine] = useState('opencode_run')
  const [editAgentModel, setEditAgentModel] = useState('gemini-2.5-flash')
  const [editAgentTools, setEditAgentTools] = useState<string[]>([])
  const [editAgentSkills, setEditAgentSkills] = useState<string[]>([])
  const editFolderInputRef = useRef<HTMLInputElement>(null)

  // Files Modal State (Matching office.html lines 2984-3069 & 3687-3716)
  const [isFilesModalOpen, setIsFilesModalOpen] = useState(false)
  const [selectedPersonaFile, setSelectedPersonaFile] = useState<CorePersonaFileKey>('SOUL.md')
  const [personaEditorContent, setPersonaEditorContent] = useState<string>('')
  const [personaFileToggles, setPersonaFileToggles] = useState<Record<string, Record<CorePersonaFileKey, boolean>>>({})
  const [personaFileOverrides, setPersonaFileOverrides] = useState<Record<string, Partial<Record<CorePersonaFileKey, string>>>>({})

  const handleOpenFilesModal = () => {
    setSelectedPersonaFile('SOUL.md')
    const initialContent = getPersonaFileContent(
      'SOUL.md',
      selectedAgent,
      personaFileOverrides[selectedAgent.id]
    )
    setPersonaEditorContent(initialContent)
    setIsFilesModalOpen(true)
    playOfficeFoley('click', soundEnabled)
  }

  const handleSelectPersonaFile = (fileKey: CorePersonaFileKey) => {
    setSelectedPersonaFile(fileKey)
    const content = getPersonaFileContent(
      fileKey,
      selectedAgent,
      personaFileOverrides[selectedAgent.id]
    )
    setPersonaEditorContent(content)
    playOfficeFoley('click', soundEnabled)
  }

  const handleTogglePersonaFile = (fileKey: CorePersonaFileKey, checked: boolean) => {
    setPersonaFileToggles((prev) => ({
      ...prev,
      [selectedAgent.id]: {
        ...(prev[selectedAgent.id] || {
          'SOUL.md': true,
          'AGENTS.md': true,
          'PROFILE.md': true,
          'MEMORY.md': true,
        }),
        [fileKey]: checked,
      },
    }))
    playOfficeFoley('click', soundEnabled)
    triggerToast(`${fileKey} ${checked ? 'Enabled' : 'Disabled'} for ${selectedAgent.name}`)
  }

  const handleSavePersonaFile = () => {
    if (!selectedAgent) return
    setPersonaFileOverrides((prev) => ({
      ...prev,
      [selectedAgent.id]: {
        ...(prev[selectedAgent.id] || {}),
        [selectedPersonaFile]: personaEditorContent,
      },
    }))

    if (selectedPersonaFile === 'SOUL.md') {
      setAgents((prev) =>
        prev.map((ag) =>
          ag.id === selectedAgent.id
            ? {
                ...ag,
                personality: personaEditorContent.trim(),
                logs: [
                  ...ag.logs,
                  `[${new Date().toLocaleTimeString()}] SOUL.md prompt updated & saved.`,
                ],
              }
            : ag
        )
      )
    }

    playOfficeFoley('success', soundEnabled)
    triggerToast(`${selectedPersonaFile} saved for ${selectedAgent.name} ✓`)
  }

  const handleOpenActiveWorktreeInExplorer = () => {
    const worktreePath =
      selectedAgent.workspace === 'repo_active'
        ? 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57'
        : selectedAgent.workspace
    navigator.clipboard.writeText(worktreePath)
    triggerToast(`Worktree path copied: ${worktreePath}`)
    playOfficeFoley('click', soundEnabled)
  }

  const handleOpenEditModal = (agent: AgentOfficeMember) => {
    setEditAgentName(agent.name)
    setEditAgentRole(agent.role)
    setEditAgentPersonality(agent.personality || '')
    setEditAgentWorkspace(
      agent.workspace === 'repo_active'
        ? 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57'
        : agent.workspace || 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57'
    )
    setEditAgentEngine(agent.engine || 'opencode_run')
    setEditAgentModel(agent.model || 'opencode/nemotron-3-ultra-free')
    setEditAgentTools([...(agent.tools || [])])
    const currentSkills = AVAILABLE_SKILLS.filter((s) =>
      agent.specialty?.toLowerCase().includes(s.id.toLowerCase())
    ).map((s) => s.id)
    setEditAgentSkills(currentSkills.length > 0 ? currentSkills : ['opencode', 'hamza_taste'])
    setIsEditAgentOpen(true)
    playOfficeFoley('click', soundEnabled)
  }

  const handleSaveEditAgent = () => {
    if (!selectedAgent) return
    const updatedName = editAgentName.trim() || selectedAgent.name
    const updatedRole = editAgentRole.trim() || selectedAgent.role

    setAgents((prev) =>
      prev.map((ag) => {
        if (ag.id !== selectedAgent.id) return ag
        return {
          ...ag,
          name: updatedName,
          role: updatedRole,
          status: ag.status,
          personality: editAgentPersonality.trim() || ag.personality,
          workspace: editAgentWorkspace.trim() || ag.workspace,
          engine: editAgentEngine,
          model: editAgentModel,
          tools: editAgentTools.length > 0 ? editAgentTools : ag.tools,
          specialty: `${editAgentEngine}, ${editAgentSkills.join(', ')}`,
          logs: [
            ...ag.logs,
            `[${new Date().toLocaleTimeString()}] Config updated: Engine=${editAgentEngine}, Model=${editAgentModel}, Workspace=${editAgentWorkspace}`,
          ],
        }
      })
    )
    setIsEditAgentOpen(false)
    playOfficeFoley('success', soundEnabled)
    triggerToast(`Agent ${updatedName} configuration updated!`)

    api.saveAgent({
      id: selectedAgent.id,
      name: updatedName,
      role: updatedRole,
      specialty: `${editAgentEngine}, ${editAgentSkills.join(', ')}`,
      color: selectedAgent.color,
      default_tool: editAgentEngine,
      risk_tier: selectedAgent.safetyTier || 'L1_MUTATION',
      model_id: editAgentModel,
      worktree: editAgentWorkspace,
      allowed_tools: editAgentTools.length > 0 ? editAgentTools : selectedAgent.tools,
      allowed_skills: editAgentSkills,
      prompt_prefix: editAgentPersonality.trim() || selectedAgent.personality,
    } as any).then(() => {
      loadFleet()
    }).catch((err) => {
      console.error('Failed to update agent:', err)
    })
  }

  const toggleEditSkill = (skill: string) => {
    setEditAgentSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    )
  }

  const toggleEditTool = (tool: string) => {
    setEditAgentTools((prev) =>
      prev.includes(tool) ? prev.filter((t) => t !== tool) : [...prev, tool]
    )
  }

  const toggleSkill = (skill: string) => {
    setNewAgentSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    )
  }

  const toggleTool = (tool: string) => {
    setNewAgentSelectedTools((prev) =>
      prev.includes(tool) ? prev.filter((t) => t !== tool) : [...prev, tool]
    )
  }

  // Handle Add New Agent
  const handleCreateNewAgent = () => {
    const name = newAgentName.trim() || newAgentAvatar || `Agent-${agents.length + 1}`
    const role = newAgentRole.trim() || 'Autonomous Worker'
    const newId = `agent-${Date.now()}`
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4']
    const pickedColor = colors[agents.length % colors.length]

    const newAgent: AgentOfficeMember = {
      id: newId,
      name,
      role,
      badge: 'CUSTOM',
      badgeVariant: 'default',
      color: pickedColor,
      hairColor: '#2b2926',
      shirtColor: pickedColor,
      status: 'IDLE',
      currentTask: newAgentInstructions.trim() || 'Initialized and waiting for fleet dispatch',
      deskPct: { x: 50.0, y: 55.0 },
      currentPct: { x: 50.0, y: 55.0 },
      targetPct: { x: 50.0, y: 55.0 },
      speechBubble: `Agent ${name} online and ready!`,
      tools: newAgentSelectedTools.length > 0 ? newAgentSelectedTools : [newAgentEngine],
      logs: [
        `[${new Date().toLocaleTimeString()}] Agent ${name} joined fleet`,
        `[${new Date().toLocaleTimeString()}] Engine initialized: ${newAgentEngine}`,
        `[${new Date().toLocaleTimeString()}] Workspace mounted: ${newAgentWorkspace}`,
      ],
      personality: newAgentInstructions.trim() || 'Custom configured autonomous agent operating under Zezo OS.',
      engine: newAgentEngine,
      model: newAgentModel,
      workspace: newAgentWorkspace,
      safetyTier: 'L1_MUTATION',
      specialty: `${newAgentEngine}, ${newAgentSelectedSkills.join(', ')}`,
    }

    setAgents((prev) => [...prev, newAgent])
    setSelectedAgentId(newId)
    setIsAddAgentOpen(false)
    setNewAgentName('')
    setNewAgentRole('')
    setNewAgentInstructions('')

    api.saveAgent({
      id: newId,
      name,
      role,
      specialty: `${newAgentEngine}, ${newAgentSelectedSkills.join(', ')}`,
      color: pickedColor,
      default_tool: newAgentEngine,
      risk_tier: 'L1_MUTATION',
      model_id: newAgentModel,
      worktree: newAgentWorkspace,
      allowed_tools: newAgentSelectedTools.length > 0 ? newAgentSelectedTools : [newAgentEngine],
      allowed_skills: newAgentSelectedSkills,
      prompt_prefix: newAgentInstructions.trim() || `You are ${name}, an autonomous specialist operating under Zezo OS.`,
    } as any).then(() => {
      triggerToast(`Agent ${name} joined autonomous fleet!`)
      loadFleet()
    }).catch((err) => {
      console.error('Failed to save agent to backend:', err)
    })
  }

  const selectedAgent = agents.find((a) => a.id === selectedAgentId) || agents[0]

  const effectiveBackendLogs = (backendLogs && backendLogs.length > 0) ? backendLogs : internalLogs

  const displayedLogs = useMemo(() => {
    let result = effectiveBackendLogs

    if (logFilterMode === 'agent' && selectedAgent) {
      const nameL = selectedAgent.name.toLowerCase()
      const idL = selectedAgent.id.toLowerCase()
      const toolL = (selectedAgent.engine || '').toLowerCase()
      const filtered = result.filter((l) => {
        const txt = l.text.toLowerCase()
        const src = l.source.toLowerCase()
        return (
          txt.includes(nameL) ||
          txt.includes(idL) ||
          src.includes(nameL) ||
          src.includes(idL) ||
          (toolL && (txt.includes(toolL) || src.includes(toolL)))
        )
      })
      if (filtered.length === 0 && selectedAgent.logs && selectedAgent.logs.length > 0) {
        result = selectedAgent.logs.map((text, idx) => ({
          id: `agent-act-${idx}`,
          time: new Date().toLocaleTimeString(),
          source: selectedAgent.name.toUpperCase(),
          text,
          type: 'INFO',
          level: 'INFO',
        }))
      } else {
        result = filtered
      }
    } else if (logFilterMode === 'errors') {
      result = result.filter((l) => {
        const lvl = (l.level || l.type || '').toUpperCase()
        return lvl.includes('ERR') || l.text.toLowerCase().includes('error') || l.text.toLowerCase().includes('fail')
      })
    }

    if (logSearchQuery.trim()) {
      const q = logSearchQuery.toLowerCase()
      result = result.filter((l) => l.text.toLowerCase().includes(q) || l.source.toLowerCase().includes(q))
    }

    return result
  }, [effectiveBackendLogs, logFilterMode, selectedAgent, logSearchQuery])

  useEffect(() => {
    if (autoFollowLogs) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [displayedLogs.length, autoFollowLogs])

  // Copy logs to clipboard
  const handleCopyLogs = () => {
    if (!selectedAgent) return
    let logText = ''
    if (logFilterMode === 'agent' && displayedLogs.length === 0) {
      logText = selectedAgent.logs.join('\n')
    } else {
      logText = displayedLogs.map((l) => `[${l.time}] [${l.source}] ${l.text}`).join('\n')
    }
    navigator.clipboard.writeText(logText)
    setCopiedLogs(true)
    setTimeout(() => setCopiedLogs(false), 1800)
  }
  const [soundEnabled, setSoundEnabled] = useState(true)
  const [simulationToast, setSimulationToast] = useState<string | null>(null)
  const [collabBeam] = useState<{
    from: { x: number; y: number }
    to: { x: number; y: number }
    label?: string
  } | null>(null)

  // Helper to show brief toast
  const triggerToast = (msg: string) => {
    setSimulationToast(msg)
    setTimeout(() => setSimulationToast(null), 3000)
  }

  return (
    <div className="flex flex-col w-full h-full min-w-0 min-h-0 bg-[var(--background)] text-[var(--foreground)] overflow-hidden select-none transition-colors duration-200">
      {/* ── Main Workspace Layout using 100% ReUI Frames (Full Height & Fully Responsive) ── */}
      <div className={cn(
        "flex-1 min-h-0 min-w-0 grid gap-2 p-2 overflow-hidden w-full h-full bg-[var(--background)]",
        officeMode === 'chat'
          ? "grid-cols-1 md:grid-cols-[260px_minmax(0,1fr)]"
          : "grid-cols-1 md:grid-cols-[230px_minmax(0,1fr)] lg:grid-cols-[240px_minmax(0,1fr)_330px]"
      )}>

        {/* LEFT PANEL: Agent Fleet Roster */}
        <Frame className="h-full min-h-0 min-w-0 w-full overflow-hidden">
          <FramePanel className="flex flex-col h-full min-h-0 p-0 overflow-hidden bg-[var(--card)] border-[var(--border)]">
            <FrameHeader className="p-2.5 border-b border-[var(--border)] flex flex-row items-center justify-between">
              <FrameTitle className="text-xs">Agents</FrameTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddAgentOpen(true)}
                className="h-6 text-[10px] px-2 gap-1 border-[var(--border)] hover:bg-[var(--muted)] text-[var(--foreground)]"
              >
                <Plus className="w-3 h-3" />
                <span>Add Agent</span>
              </Button>
            </FrameHeader>

            <ScrollArea className="flex-1 px-2 py-2">
              <div className="space-y-1.5 pr-2.5">
                {agents.map((ag) => {
                  const isSelected = ag.id === selectedAgentId
                  return (
                    <Button
                      key={ag.id}
                      variant={isSelected ? 'secondary' : 'ghost'}
                      size="sm"
                      onClick={() => setSelectedAgentId(ag.id)}
                      className={`w-full h-auto p-2 flex items-center justify-between gap-2 overflow-hidden rounded-[var(--radius,0.5rem)] border transition-colors duration-150 text-left font-normal ${isSelected
                        ? 'bg-[var(--primary)]/15 border-[var(--primary)] text-[var(--foreground)] shadow-xs'
                        : 'bg-[var(--input)]/30 border-[var(--border)] hover:bg-[var(--muted)] text-[var(--foreground)]'
                        }`}
                    >
                      <div className="flex items-center gap-2.5 flex-1 min-w-0 overflow-hidden">
                        <div className="w-7 h-7 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center shrink-0 border border-[var(--border)] bg-[var(--input)]/40 shadow-2xs">
                          <Blobatar name={ag.name} size={28} animate="hover" className="w-full h-full object-contain" />
                        </div>
                        <div className="flex-1 min-w-0 overflow-hidden">
                          <div className="text-xs font-semibold truncate text-[var(--foreground)]">{ag.name}</div>
                          <div className="text-[9px] text-[var(--muted-foreground)] truncate">{ag.role}</div>
                        </div>
                      </div>

                      <Badge variant={ag.badgeVariant} size="xs" className="shrink-0 text-[8px] px-1.5 py-0.5">
                        {ag.status}
                      </Badge>
                    </Button>
                  )
                })}
              </div>
            </ScrollArea>
          </FramePanel>
        </Frame>

        {/* CENTER PANEL: Authentic Scranton Office Floor with Live Blobatars */}
        <Frame className="h-full min-h-0 min-w-0 w-full overflow-hidden">
          <FramePanel className="flex flex-col h-full min-h-0 min-w-0 w-full p-0 overflow-hidden bg-[var(--card)] border-[var(--border)] relative">
            {/* Header with Mode Switcher, Simulation Controls & Audio Toggle */}
            <FrameHeader className="p-2 border-b border-[var(--border)] flex flex-row items-center justify-between bg-[var(--card)] z-20 shrink-0 gap-2 overflow-x-auto scrollbar-none">
              <div className="flex items-center gap-2 min-w-0">
                <FrameTitle className="text-xs flex items-center gap-1.5 truncate">
                  {officeMode === 'chat' ? (
                    <>
                      <MessageSquare className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                      <span>Direct Chat</span>
                    </>
                  ) : officeMode === 'kanban' ? (
                    <>
                      <Kanban className="w-3.5 h-3.5 text-[var(--primary)] shrink-0" />
                      <span className="hidden sm:inline">Task View</span>
                      <span className="sm:hidden">Tasks</span>
                    </>
                  ) : (
                    <>
                      <Boxes className="w-3.5 h-3.5 text-[var(--primary)] shrink-0" />
                      <span className="hidden sm:inline">Office View</span>
                      <span className="sm:hidden">Office</span>
                    </>
                  )}
                </FrameTitle>
                {officeMode !== 'chat' && (
                  <Badge variant="outline" size="xs" className="hidden md:inline-flex font-mono text-[9px]">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1" />
                    {officeMode === 'kanban'
                      ? `${agents.length} AGENTS`
                      : `${agents.filter((a) => a.status === 'WORKING').length} ACTIVE`}
                  </Badge>
                )}
              </div>

              {/* Audio Foley & View Mode Controls */}
              <div className="flex items-center gap-1 shrink-0">
                {officeMode === 'spatial' && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setSoundEnabled(!soundEnabled)
                        playOfficeFoley('click', !soundEnabled)
                      }}
                      className="h-6 text-[10px] px-2 font-mono text-[var(--muted-foreground)] hover:text-[var(--foreground)] gap-1"
                      title={soundEnabled ? 'Audio Foley: ON' : 'Audio Foley: MUTED'}
                    >
                      {soundEnabled ? (
                        <Volume2 className="w-3.5 h-3.5 text-[var(--primary)]" />
                      ) : (
                        <VolumeX className="w-3.5 h-3.5 text-muted-foreground" />
                      )}
                      <span className="hidden md:inline text-[9px] font-mono">
                        {soundEnabled ? 'AUDIO' : 'MUTED'}
                      </span>
                    </Button>

                    <div className="h-4 w-px bg-[var(--border)] mx-1" />
                  </>
                )}

                {/* View Mode Controls */}
                <Button
                  variant={officeMode === 'spatial' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setOfficeMode('spatial')}
                  className="h-6 text-[10px] px-2 gap-1 font-mono"
                  title="Scranton 2D Office Floor"
                >
                  <Boxes className="w-3 h-3" />
                  <span className="hidden sm:inline">Floor</span>
                </Button>

                <Button
                  variant={officeMode === 'kanban' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setOfficeMode('kanban')}
                  className="h-6 text-[10px] px-2 gap-1 font-mono"
                  title="Kanban Board"
                >
                  <Kanban className="w-3 h-3" />
                  <span className="hidden sm:inline">Tasks</span>
                </Button>
              </div>
            </FrameHeader>

            {/* ── VIEW 1: AUTHENTIC SCRANTON OFFICE FLOOR WITH LIVE BLOBATARS ── */}
            {officeMode === 'spatial' && (
              <div className="flex-1 min-h-0 min-w-0 w-full h-full relative overflow-hidden bg-[#050507] flex items-center justify-center p-3 select-none">
                {/* 988x640 Scaled Responsive Office Container */}
                <div
                  className="relative w-full max-w-[988px] aspect-[988/640] rounded-sm overflow-hidden border-4 border-[#171717] shadow-2xl shrink-0"
                  style={{
                    backgroundColor: '#e9e2de',
                    boxShadow: '0 0 0 2px #d8d1cb inset, 0 15px 40px rgba(0,0,0,0.85)',
                  }}
                >
                  {/* 1. SAGE GREEN TILE FLOOR */}
                  <div
                    className="absolute inset-x-0 top-[12.5%] bottom-[1.4%] pointer-events-none"
                    style={{
                      backgroundColor: '#7d9989',
                      backgroundImage: `linear-gradient(90deg, transparent 96%, #6c8d7d 96%, #6c8d7d 99%, transparent 99%), linear-gradient(0deg, transparent 96%, #6c8d7d 96%, #6c8d7d 99%, transparent 99%)`,
                      backgroundSize: '78px 58px',
                    }}
                  >
                    {/* Subtle Dot Grid */}
                    <div
                      className="absolute inset-0 opacity-80"
                      style={{
                        backgroundImage: `radial-gradient(circle at 50% 50%, #638779 0 3px, transparent 4px)`,
                        backgroundSize: '78px 58px',
                      }}
                    />
                  </div>

                  {/* 2. TOP WALL DECORATIONS (Windows, Clock, Clipboard, Whiteboard, Plants) */}
                  {/* Glass Windows */}
                  <div
                    className="absolute top-[3%] left-[4%] w-[4.6%] h-[8%] border-[3px] border-[#292929] shadow-inner z-10"
                    style={{
                      background: `linear-gradient(90deg, transparent 46%, #242424 46%, #242424 53%, transparent 53%), linear-gradient(0deg, transparent 46%, #242424 46%, #242424 53%, transparent 53%), #b8dce8`,
                    }}
                  />
                  <div
                    className="absolute top-[3%] left-[28%] w-[4.6%] h-[8%] border-[3px] border-[#292929] shadow-inner z-10"
                    style={{
                      background: `linear-gradient(90deg, transparent 46%, #242424 46%, #242424 53%, transparent 53%), linear-gradient(0deg, transparent 46%, #242424 46%, #242424 53%, transparent 53%), #b8dce8`,
                    }}
                  />
                  <div
                    className="absolute top-[3%] left-[40%] w-[4.6%] h-[8%] border-[3px] border-[#292929] shadow-inner z-10"
                    style={{
                      background: `linear-gradient(90deg, transparent 46%, #242424 46%, #242424 53%, transparent 53%), linear-gradient(0deg, transparent 46%, #242424 46%, #242424 53%, transparent 53%), #b8dce8`,
                    }}
                  />

                  {/* Red Wall Clock */}
                  <div className="absolute top-[4%] left-[1%] w-5 h-5 rounded-full border-[3px] border-[#a94343] bg-white z-10 flex items-center justify-center">
                    <div className="w-0.5 h-2 bg-[#222] origin-bottom transform rotate-45 -translate-y-0.5" />
                  </div>

                  {/* Clipboard Calendar */}
                  <div className="absolute top-[2.5%] left-[11%] w-3.5 h-6 bg-[#eeddb9] border-2 border-[#54483b] z-10 rounded-[1px] shadow-xs">
                    <div className="w-2 h-1 bg-[#888] mx-auto -mt-0.5" />
                  </div>

                  {/* Whiteboard "TODO" */}
                  <div className="absolute top-[2%] left-[19%] w-[6%] h-[8.5%] bg-white border-2 border-[#47433e] z-10 shadow-xs p-0.5">
                    <div className="text-[7px] font-mono font-bold text-blue-500">TODO</div>
                    <div className="space-y-0.5 mt-0.5">
                      <div className="w-3/4 h-0.5 bg-gray-400" />
                      <div className="w-1/2 h-0.5 bg-gray-400" />
                    </div>
                  </div>

                  {/* Clover Plant Pots */}
                  <div className="absolute top-[9.5%] left-[16%] w-3.5 h-2 bg-[#c5b7a0] border-2 border-[#38342d] z-10">
                    <span className="absolute -top-4 -left-0.5 text-emerald-700 text-sm font-bold">♣</span>
                  </div>
                  <div className="absolute top-[9.5%] left-[49%] w-3.5 h-2 bg-[#c5b7a0] border-2 border-[#38342d] z-10">
                    <span className="absolute -top-4 -left-0.5 text-emerald-700 text-sm font-bold">♣</span>
                  </div>
                  <div className="absolute bottom-[0.5%] left-[68%] w-3.5 h-2 bg-[#c5b7a0] border-2 border-[#38342d] z-10">
                    <span className="absolute -top-4 -left-0.5 text-emerald-700 text-sm font-bold">♣</span>
                  </div>
                  <div className="absolute bottom-[0.5%] left-[96%] w-3.5 h-2 bg-[#c5b7a0] border-2 border-[#38342d] z-10">
                    <span className="absolute -top-4 -left-0.5 text-emerald-700 text-sm font-bold">♣</span>
                  </div>

                  {/* 3. PARTITION WALLS (Exact office.html architecture) */}
                  {/* Michael's Office Partition */}
                  <div className="absolute left-[18.2%] top-[12.5%] w-[1.6%] h-[27%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />
                  <div className="absolute left-0 top-[38%] w-[12.8%] h-[3.8%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />

                  {/* Conference Room Partitions */}
                  <div className="absolute left-[21%] top-[12.5%] w-[1.6%] h-[27%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />
                  <div className="absolute left-[52%] top-[12.5%] w-[1.6%] h-[18%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />
                  <div className="absolute left-[15.2%] top-[38%] w-[23%] h-[3.8%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />
                  <div className="absolute left-[39.5%] top-[38%] w-[16.5%] h-[3.8%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />

                  {/* Annex Partitions */}
                  <div className="absolute left-[74%] top-[12.5%] w-[1.6%] h-[32%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />
                  <div className="absolute left-[74%] top-[42%] w-[26%] h-[3.8%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />

                  {/* Kitchen & Breakroom Dividers */}
                  <div className="absolute left-[73%] top-[56%] w-[1.6%] h-[14%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />
                  <div className="absolute left-[71%] top-[74%] w-[1.6%] h-[26%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />
                  <div className="absolute left-0 bottom-[1.4%] w-full h-[1.6%] bg-[#f8f6f1] border-[3px] border-[#171717] z-10" />

                  {/* 4. CONFERENCE ROOM TABLE & PURPLE CHAIRS */}
                  <div
                    className="absolute left-[28%] top-[18.5%] w-[18.5%] h-[9.3%] border-2 border-[#4a3320] shadow-sm z-10"
                    style={{
                      backgroundColor: '#b88a4c',
                      boxShadow: 'inset 0 3px #d5ae70',
                    }}
                  >
                    {/* Green Folder */}
                    <div className="absolute left-[8%] top-[15%] w-[7%] h-[12%] bg-[#2c9b59] border border-[#28472f]" />
                    {/* Paper Sheet */}
                    <div className="absolute right-[4%] top-[10%] w-[9%] h-[42%] bg-[#eee5ce] border border-[#443b31] -rotate-12" />
                  </div>
                  {/* Purple Conference Chairs */}
                  {[31, 34, 37, 40].map((leftPct, i) => (
                    <React.Fragment key={`conf-chair-${i}`}>
                      <div
                        className="absolute w-[2.3%] h-[3.8%] bg-[#914c66] border-2 border-[#49313a] shadow-xs z-5"
                        style={{ left: `${leftPct}%`, top: '14.5%' }}
                      />
                      <div
                        className="absolute w-[2.3%] h-[3.8%] bg-[#914c66] border-2 border-[#49313a] shadow-xs z-5"
                        style={{ left: `${leftPct}%`, top: '28%' }}
                      />
                    </React.Fragment>
                  ))}

                  {/* 5. SERVER RACK HQ (Left Wall with blinking colored LEDs) */}
                  <div className="absolute left-[1%] top-[42%] w-[4.8%] h-[9%] bg-[#080d12] border-2 border-[#333] z-10 p-0.5 space-y-1">
                    <div className="w-full h-1 bg-[#06b6d4] shadow-xs" />
                    <div className="w-full h-1 bg-[#10b981] shadow-xs animate-pulse" />
                    <div className="w-full h-1 bg-[#f59e0b] shadow-xs" />
                  </div>

                  {/* 6. WATER COOLER & KITCHEN BREAKROOM */}
                  {/* Glowing Water Cooler */}
                  <div className="absolute right-[1.5%] top-[56%] w-[7.5%] h-[15%] bg-[#b1f4c9] border-[3px] border-[#273d32] z-10 shadow-inner p-1">
                    <div className="w-full h-full bg-[#0c7654] border-2 border-[#214337] flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-cyan-300 animate-pulse" />
                    </div>
                  </div>

                  {/* Kitchen Counter, Fridge & Shelf */}
                  <div className="absolute right-[3%] bottom-[8%] w-[18%] h-[10%] z-10 flex items-end gap-1">
                    {/* Counter & Sink */}
                    <div className="w-[47%] h-[75%] bg-[#b9b9ad] border-2 border-[#363632] relative">
                      <div className="absolute left-2 top-1 w-4 h-3 bg-[#e2e5dc] border border-[#6e7770]" />
                    </div>
                    {/* Fridge */}
                    <div className="w-[20%] h-full bg-[#c7c9c6] border-2 border-[#525653] relative">
                      <div className="absolute inset-x-1 top-1/2 border-t-2 border-[#7b817d]" />
                    </div>
                    {/* Microwave Shelf */}
                    <div
                      className="w-[30%] h-full border-2 border-[#535752]"
                      style={{
                        background: `repeating-linear-gradient(0deg, #b6b9b4 0 7px, #474b48 7px 9px)`,
                      }}
                    />
                  </div>

                  {/* 7. ALL 18 WORKSTATION DESKS */}
                  {WORKSTATION_SLOTS.map((desk) => {
                    const seatedAgent = agents.find(
                      (a) =>
                        Math.abs(a.currentPct.x - (desk.x + 3.9)) < 4 &&
                        Math.abs(a.currentPct.y - (desk.y + 8.8)) < 4
                    )
                    const isWorking = seatedAgent?.status === 'WORKING'

                    return (
                      <div
                        key={desk.id}
                        className="absolute w-[7.8%] h-[7.1%] z-10 pointer-events-none"
                        style={{
                          left: `${desk.x}%`,
                          top: `${desk.y}%`,
                          backgroundColor: '#b88b4e',
                          border: '2px solid #4b3421',
                          boxShadow: 'inset 0 3px #d5ae70',
                        }}
                      >
                        {/* Underdesk Drawer Base */}
                        <div className="absolute inset-x-[7%] bottom-[9%] h-[14%] bg-[#74502c] border border-[#392a1b]" />

                        {/* Computer Monitor (Glows blue/cyan when working) */}
                        <div
                          className={`absolute left-[23%] -top-[48%] w-[54%] h-[55%] border-[3px] border-[#292b2d] z-10 overflow-hidden ${
                            isWorking
                              ? 'bg-[#071521] shadow-[inset_0_0_0_2px_#8bdcff,0_0_10px_rgba(56,190,255,0.75)]'
                              : 'bg-[#080d12] shadow-[inset_0_0_0_2px_#414b54]'
                          }`}
                        >
                          {isWorking && (
                            <div className="w-full h-full bg-cyan-400/30 animate-pulse flex items-center justify-center">
                              <div className="w-2 h-1 bg-cyan-200" />
                            </div>
                          )}
                        </div>

                        {/* Monitor Stand */}
                        <div className="absolute left-[34%] -top-[8px] w-[32%] h-[5px] bg-[#c4b7a0] border border-[#39332e] z-5" />

                        {/* Keyboard */}
                        <div
                          className="absolute left-[20%] bottom-[13%] w-[43%] h-[15%] border border-[#4b4439] z-10"
                          style={{
                            background: `repeating-linear-gradient(90deg, #e2dac7 0 3px, #aaa18d 3px 4px)`,
                          }}
                        />

                        {/* Mouse */}
                        <div className="absolute right-[15%] bottom-[10%] w-[9%] h-[18%] bg-[#ded8c8] border border-[#4b4439] rounded-full z-10" />

                        {/* Coffee Mug */}
                        <div className="absolute right-[5%] bottom-[20%] w-[7px] h-[7px] bg-[#eee7d7] border border-[#40372d] z-10" />

                        {/* Wooden Desk Chair Base */}
                        <div
                          className="absolute left-[24%] top-[100%] w-[52%] h-[38%] bg-[#a17b43] border-2 border-[#46321f] z-5"
                          style={{ boxShadow: 'inset 0 0 0 2px #c6a36a' }}
                        />
                      </div>
                    )
                  })}

                  {/* ── 8. DYNAMIC SVG COLLABORATION BEAM LAYER ── */}
                  {collabBeam && (
                    <svg
                      className="absolute inset-0 w-full h-full pointer-events-none z-30 overflow-visible"
                    >
                      <line
                        x1={`${collabBeam.from.x}%`}
                        y1={`${collabBeam.from.y}%`}
                        x2={`${collabBeam.to.x}%`}
                        y2={`${collabBeam.to.y}%`}
                        stroke="#06b6d4"
                        strokeWidth="2.5"
                        strokeDasharray="5 5"
                        className="animate-pulse"
                      />
                      {collabBeam.label && (
                        <text
                          x={`${(collabBeam.from.x + collabBeam.to.x) / 2}%`}
                          y={`${(collabBeam.from.y + collabBeam.to.y) / 2 - 2}%`}
                          fill="#ffffff"
                          fontSize="9"
                          fontFamily="monospace"
                          fontWeight="bold"
                          textAnchor="middle"
                          className="drop-shadow-md"
                        >
                          {collabBeam.label}
                        </text>
                      )}
                    </svg>
                  )}

                  {/* ── 9. DYNAMIC ANIMATED BLOBATARS LAYER (Live Walking, Sitting, Speech) ── */}
                  {agents.map((ag) => {
                    const isSelected = ag.id === selectedAgentId
                    const isWorking = ag.status === 'WORKING'
                    const isWalking = ag.status === 'WALKING'
                    const isInMeeting = ag.status === 'IN_MEETING'
                    const isCoffee = ag.status === 'COFFEE_BREAK'

                    return (
                      <div
                        key={ag.id}
                        onClick={() => {
                          setSelectedAgentId(ag.id)
                          playOfficeFoley('click', soundEnabled)
                        }}
                        className={`absolute z-30 cursor-pointer flex flex-col items-center group select-none`}
                        style={{
                          left: `${ag.currentPct.x}%`,
                          top: `${ag.currentPct.y}%`,
                          transform: 'translate(-50%, -50%)',
                          transition: isWalking
                            ? 'left 1.2s cubic-bezier(0.2, 0.9, 0.4, 1), top 1.2s cubic-bezier(0.2, 0.9, 0.4, 1)'
                            : 'left 0.8s ease-out, top 0.8s ease-out',
                        }}
                      >
                        {/* Active Glowing Halation */}
                        {(isSelected || isWorking || isWalking) && (
                          <div
                            className={`absolute -inset-1 rounded-full blur-[4px] animate-pulse pointer-events-none ${
                              isSelected
                                ? 'bg-[var(--primary)] opacity-80'
                                : isWalking
                                ? 'bg-cyan-400 opacity-70'
                                : isWorking
                                ? 'bg-orange-500 opacity-60'
                                : 'bg-amber-400 opacity-50'
                            }`}
                          />
                        )}

                        {/* Live Animated Blobatar Avatar */}
                        <div
                          className={`w-8 h-8 rounded-full overflow-hidden flex items-center justify-center p-0.5 bg-black/40 border border-white/20 shadow-md relative z-10 transition-transform duration-150 ${
                            isWalking ? 'animate-bounce' : 'group-hover:scale-110'
                          }`}
                        >
                          <Blobatar
                            name={ag.name}
                            size={32}
                            animate={isWorking || isWalking ? 'always' : 'hover'}
                            className="w-full h-full object-contain"
                          />
                        </div>

                        {/* Monospace Nameplate Label */}
                        <div
                          className={`mt-0.5 px-1.5 py-0.2 rounded text-[8px] font-mono font-bold tracking-wider uppercase border shadow-xs truncate max-w-[65px] ${
                            isSelected
                              ? 'bg-[var(--primary)] text-black border-white'
                              : isWalking
                              ? 'bg-cyan-900 text-cyan-200 border-cyan-400'
                              : isInMeeting
                              ? 'bg-purple-900 text-purple-200 border-purple-400'
                              : isCoffee
                              ? 'bg-amber-900 text-amber-200 border-amber-400'
                              : isWorking
                              ? 'bg-black text-white border-orange-500'
                              : 'bg-black/90 text-white border-[#333]'
                          }`}
                        >
                          {ag.name}
                        </div>

                        {/* Floating Comic Speech Bubble */}
                        {ag.speechBubble && (
                          <div className="absolute -top-7 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded bg-white text-black border-2 border-black text-[8px] font-sans font-bold whitespace-nowrap shadow-md z-40 animate-bounce">
                            {ag.speechBubble.slice(0, 30)}
                            <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-black" />
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                {/* Simulation Floating Toast */}
                {simulationToast && (
                  <div className="absolute top-4 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded bg-black/90 text-white border border-cyan-400/60 shadow-xl text-xs font-mono font-bold z-50 animate-bounce">
                    {simulationToast}
                  </div>
                )}
              </div>
            )}

            {/* ── VIEW 2: TACTICAL WAR ROOM MATRIX ── */}
            {officeMode === 'matrix' && (
              <div className="flex-1 min-h-0 min-w-0 w-full h-full flex flex-col overflow-hidden bg-[var(--background)]">
                {/* Filter Sub-header */}
                <div className="p-1.5 px-2.5 border-b border-[var(--border)] flex items-center justify-between gap-2 bg-[var(--card)]/50 shrink-0">
                  <div className="flex items-center gap-1 overflow-x-auto scrollbar-none">
                    <Button
                      variant={matrixFilter === 'ALL' ? 'secondary' : 'ghost'}
                      size="sm"
                      onClick={() => setMatrixFilter('ALL')}
                      className={`h-5.5 text-[10px] px-2 gap-1 font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] ${
                        matrixFilter === 'ALL' ? 'bg-[var(--input)] text-[var(--foreground)] font-bold' : 'text-[var(--muted-foreground)]'
                      }`}
                    >
                      <LayoutGrid className="w-2.5 h-2.5" />
                      <span>All ({agents.length})</span>
                    </Button>
                    <Button
                      variant={matrixFilter === 'WORKING' ? 'secondary' : 'ghost'}
                      size="sm"
                      onClick={() => setMatrixFilter('WORKING')}
                      className={`h-5.5 text-[10px] px-2 gap-1 font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] ${
                        matrixFilter === 'WORKING' ? 'bg-emerald-500/20 text-emerald-400 font-bold' : 'text-emerald-400/80 hover:text-emerald-300'
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      <span>Executing ({agents.filter((a) => a.status === 'WORKING').length})</span>
                    </Button>
                    <Button
                      variant={matrixFilter === 'REVIEW' ? 'secondary' : 'ghost'}
                      size="sm"
                      onClick={() => setMatrixFilter('REVIEW')}
                      className={`h-5.5 text-[10px] px-2 gap-1 font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] ${
                        matrixFilter === 'REVIEW' ? 'bg-amber-500/20 text-amber-400 font-bold' : 'text-amber-400/80 hover:text-amber-300'
                      }`}
                    >
                      <Shield className="w-2.5 h-2.5" />
                      <span>AST Citadel ({agents.filter((a) => a.badge === 'SECURITY' || a.badge === 'SAFETY').length})</span>
                    </Button>
                  </div>

                  <div className="flex items-center gap-1.5 text-[9px] font-mono text-emerald-400 shrink-0">
                    <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
                    <span className="hidden sm:inline">WAR ROOM LIVE</span>
                  </div>
                </div>

                {/* 4 Execution Lanes */}
                <div className="flex-1 min-h-0 min-w-0 w-full p-2.5 overflow-auto">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2.5 h-full">
                    {/* Lane 1: DISPATCH & ORCHESTRATION */}
                    <div className="flex flex-col gap-2 min-h-0">
                      <div className="flex items-center justify-between px-1.5 py-1 border-b border-[var(--border)] bg-[var(--card)]/40 rounded-t">
                        <div className="flex items-center gap-1.5">
                          <GitBranch className="w-3.5 h-3.5 text-orange-400" />
                          <span className="text-xs font-semibold text-[var(--foreground)] font-mono">01 // Dispatch</span>
                        </div>
                        <Badge variant="outline" size="xs">
                          {agents.filter((a) => a.badge === 'LEAD').length}
                        </Badge>
                      </div>
                      <ScrollArea className="flex-1 [&>div]:!block">
                        <div className="space-y-2 pr-1">
                          {agents
                            .filter((a) => a.badge === 'LEAD')
                            .map((ag) => (
                              <Card
                                key={ag.id}
                                onClick={() => setSelectedAgentId(ag.id)}
                                className={`cursor-pointer transition-all border ${
                                  ag.id === selectedAgentId
                                    ? 'border-[var(--primary)] bg-[var(--primary)]/10 shadow-xs'
                                    : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/50'
                                }`}
                              >
                                <CardContent className="p-2.5 space-y-2">
                                  <div className="flex items-center justify-between gap-1">
                                    <div className="flex items-center gap-1.5 min-w-0">
                                      <div className="w-6 h-6 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center shrink-0 border border-[var(--border)] bg-[var(--input)]/40">
                                        <Blobatar name={ag.name} size={24} animate="always" className="w-full h-full object-contain" />
                                      </div>
                                      <span className="text-xs font-medium truncate text-[var(--foreground)]">{ag.name}</span>
                                    </div>
                                    <Badge variant="default" size="xs">{ag.badge}</Badge>
                                  </div>
                                  <p className="text-[11px] text-[var(--muted-foreground)] line-clamp-2 leading-tight">
                                    {ag.currentTask}
                                  </p>
                                  <div className="flex items-center justify-between text-[10px] font-mono text-[var(--muted-foreground)] pt-1 border-t border-[var(--border)]/50">
                                    <span className="truncate">{ag.engine}</span>
                                    <span className="text-orange-400 font-bold">ORCHESTRATING</span>
                                  </div>
                                </CardContent>
                              </Card>
                            ))}
                        </div>
                      </ScrollArea>
                    </div>

                    {/* Lane 2: CODE SYNTHESIS & REFACTOR */}
                    <div className="flex flex-col gap-2 min-h-0">
                      <div className="flex items-center justify-between px-1.5 py-1 border-b border-[var(--border)] bg-[var(--card)]/40 rounded-t">
                        <div className="flex items-center gap-1.5">
                          <Terminal className="w-3.5 h-3.5 text-blue-400" />
                          <span className="text-xs font-semibold text-[var(--foreground)] font-mono">02 // Code Synth</span>
                        </div>
                        <Badge variant="running" size="xs">
                          {agents.filter((a) => a.badge === 'CODER' || a.badge === 'ASSIST').length}
                        </Badge>
                      </div>
                      <ScrollArea className="flex-1 [&>div]:!block">
                        <div className="space-y-2 pr-1">
                          {agents
                            .filter((a) => a.badge === 'CODER' || a.badge === 'ASSIST')
                            .map((ag) => (
                              <Card
                                key={ag.id}
                                onClick={() => setSelectedAgentId(ag.id)}
                                className={`cursor-pointer transition-all border ${
                                  ag.id === selectedAgentId
                                    ? 'border-[var(--primary)] bg-[var(--primary)]/10 shadow-xs'
                                    : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/50'
                                }`}
                              >
                                <CardContent className="p-2.5 space-y-2">
                                  <div className="flex items-center justify-between gap-1">
                                    <div className="flex items-center gap-1.5 min-w-0">
                                      <div className="w-6 h-6 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center shrink-0 border border-[var(--border)] bg-[var(--input)]/40">
                                        <Blobatar name={ag.name} size={24} animate="always" className="w-full h-full object-contain" />
                                      </div>
                                      <span className="text-xs font-medium truncate text-[var(--foreground)]">{ag.name}</span>
                                    </div>
                                    <Badge variant="running" size="xs">ACTIVE</Badge>
                                  </div>
                                  <p className="text-[11px] text-[var(--foreground)] font-medium line-clamp-2 leading-tight">
                                    {ag.currentTask}
                                  </p>
                                  <div className="flex items-center justify-between text-[10px] font-mono text-[var(--muted-foreground)] pt-1 border-t border-[var(--border)]/50">
                                    <span className="truncate">{ag.model}</span>
                                    <span className="text-emerald-400 font-bold">SYNTHESIZING</span>
                                  </div>
                                </CardContent>
                              </Card>
                            ))}
                        </div>
                      </ScrollArea>
                    </div>

                    {/* Lane 3: GOVERNANCE & AST AUDIT */}
                    <div className="flex flex-col gap-2 min-h-0">
                      <div className="flex items-center justify-between px-1.5 py-1 border-b border-[var(--border)] bg-[var(--card)]/40 rounded-t">
                        <div className="flex items-center gap-1.5">
                          <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                          <span className="text-xs font-semibold text-[var(--foreground)] font-mono">03 // AST Defense</span>
                        </div>
                        <Badge variant="outline" size="xs">
                          {agents.filter((a) => a.badge === 'SECURITY' || a.badge === 'SAFETY').length}
                        </Badge>
                      </div>
                      <ScrollArea className="flex-1 [&>div]:!block">
                        <div className="space-y-2 pr-1">
                          {agents
                            .filter((a) => a.badge === 'SECURITY' || a.badge === 'SAFETY')
                            .map((ag) => (
                              <Card
                                key={ag.id}
                                onClick={() => setSelectedAgentId(ag.id)}
                                className={`cursor-pointer transition-all border ${
                                  ag.id === selectedAgentId
                                    ? 'border-[var(--primary)] bg-[var(--primary)]/10 shadow-xs'
                                    : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/50'
                                }`}
                              >
                                <CardContent className="p-2.5 space-y-2">
                                  <div className="flex items-center justify-between gap-1">
                                    <div className="flex items-center gap-1.5 min-w-0">
                                      <div className="w-6 h-6 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center shrink-0 border border-[var(--border)] bg-[var(--input)]/40">
                                        <Blobatar name={ag.name} size={24} animate="always" className="w-full h-full object-contain" />
                                      </div>
                                      <span className="text-xs font-medium truncate text-[var(--foreground)]">{ag.name}</span>
                                    </div>
                                    <Badge variant="destructive" size="xs">{ag.badge}</Badge>
                                  </div>
                                  <p className="text-[11px] text-[var(--muted-foreground)] line-clamp-2 leading-tight">
                                    {ag.currentTask}
                                  </p>
                                  <div className="flex items-center justify-between text-[10px] font-mono text-[var(--muted-foreground)] pt-1 border-t border-[var(--border)]/50">
                                    <span className="truncate">AST Gate / Policy</span>
                                    <span className="text-emerald-400 font-bold">GUARD ACTIVE</span>
                                  </div>
                                </CardContent>
                              </Card>
                            ))}
                        </div>
                      </ScrollArea>
                    </div>

                    {/* Lane 4: VERIFIED & PRODUCTION READY */}
                    <div className="flex flex-col gap-2 min-h-0">
                      <div className="flex items-center justify-between px-1.5 py-1 border-b border-[var(--border)] bg-[var(--card)]/40 rounded-t">
                        <div className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span className="text-xs font-semibold text-[var(--foreground)] font-mono">04 // Verified</span>
                        </div>
                        <Badge variant="completed" size="xs">
                          {agents.filter((a) => a.logs.length > 2).length}
                        </Badge>
                      </div>
                      <ScrollArea className="flex-1 [&>div]:!block">
                        <div className="space-y-2 pr-1">
                          {agents
                            .filter((a) => a.logs.length > 2)
                            .map((ag) => (
                              <Card
                                key={ag.id}
                                onClick={() => setSelectedAgentId(ag.id)}
                                className={`cursor-pointer transition-all border ${
                                  ag.id === selectedAgentId
                                    ? 'border-[var(--primary)] bg-[var(--primary)]/10 shadow-xs'
                                    : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/50'
                                }`}
                              >
                                <CardContent className="p-2.5 space-y-2">
                                  <div className="flex items-center justify-between gap-1">
                                    <div className="flex items-center gap-1.5 min-w-0">
                                      <div className="w-6 h-6 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center shrink-0 border border-[var(--border)] bg-[var(--input)]/40">
                                        <Blobatar name={ag.name} size={24} animate="hover" className="w-full h-full object-contain" />
                                      </div>
                                      <span className="text-xs font-medium truncate text-[var(--foreground)]">{ag.name}</span>
                                    </div>
                                    <Badge variant="completed" size="xs">VERIFIED</Badge>
                                  </div>
                                  <p className="text-[11px] text-[var(--muted-foreground)] line-clamp-2 leading-tight">
                                    {ag.logs[ag.logs.length - 1]}
                                  </p>
                                  <div className="flex items-center justify-between text-[10px] font-mono text-[var(--muted-foreground)] pt-1 border-t border-[var(--border)]/50">
                                    <span className="truncate">{ag.engine}</span>
                                    <span className="text-emerald-400 font-bold">100% OK</span>
                                  </div>
                                </CardContent>
                              </Card>
                            ))}
                        </div>
                      </ScrollArea>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ── VIEW 3: TASK KANBAN BOARD ── */}
            {officeMode === 'kanban' && (
              <div className="flex-1 min-h-0 min-w-0 w-full p-3 bg-[var(--background)] overflow-auto">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 h-full">
                  {/* Column 1: QUEUED */}
                  <div className="flex flex-col gap-2 min-h-0">
                    <div className="flex items-center justify-between px-1 py-0.5 border-b border-[var(--border)]">
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                        <span className="text-xs font-semibold text-[var(--foreground)]">Queued</span>
                      </div>
                      <Badge variant="secondary" size="xs">
                        {agents.filter((a) => a.status === 'IDLE').length}
                      </Badge>
                    </div>
                    <ScrollArea className="flex-1 [&>div]:!block">
                      <div className="space-y-2 pr-1">
                        {agents
                          .filter((a) => a.status === 'IDLE')
                          .map((ag) => (
                            <Card
                              key={ag.id}
                              onClick={() => setSelectedAgentId(ag.id)}
                              className={`cursor-pointer transition-all border ${
                                ag.id === selectedAgentId
                                  ? 'border-[var(--primary)] bg-[var(--primary)]/10 shadow-xs'
                                  : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/50'
                              }`}
                            >
                              <CardContent className="p-2.5 space-y-2">
                                <div className="flex items-center justify-between gap-1">
                                  <div className="flex items-center gap-1.5 min-w-0">
                                    <div className="w-5 h-5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center shrink-0 border border-[var(--border)] bg-[var(--input)]/40">
                                      <Blobatar name={ag.name} size={20} animate="hover" className="w-full h-full object-contain" />
                                    </div>
                                    <span className="text-xs font-medium truncate text-[var(--foreground)]">{ag.name}</span>
                                  </div>
                                  <Badge variant="outline" size="xs">{ag.badge}</Badge>
                                </div>
                                <p className="text-[11px] text-[var(--muted-foreground)] line-clamp-2 leading-tight">
                                  {ag.currentTask}
                                </p>
                                <div className="flex items-center justify-between text-[10px] font-mono text-[var(--muted-foreground)] pt-1 border-t border-[var(--border)]/50">
                                  <span className="truncate">{ag.engine}</span>
                                  <span className="text-[9px] uppercase opacity-75">{ag.safetyTier.split('_')[0]}</span>
                                </div>
                              </CardContent>
                            </Card>
                          ))}
                      </div>
                    </ScrollArea>
                  </div>

                  {/* Column 2: IN PROGRESS / RUNNING */}
                  <div className="flex flex-col gap-2 min-h-0">
                    <div className="flex items-center justify-between px-1 py-0.5 border-b border-[var(--border)]">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-[var(--primary)] animate-pulse" />
                        <span className="text-xs font-semibold text-[var(--foreground)]">Running</span>
                      </div>
                      <Badge variant="running" size="xs">
                        {agents.filter((a) => a.status === 'WORKING').length}
                      </Badge>
                    </div>
                    <ScrollArea className="flex-1 [&>div]:!block">
                      <div className="space-y-2 pr-1">
                        {agents
                          .filter((a) => a.status === 'WORKING')
                          .map((ag) => (
                            <Card
                              key={ag.id}
                              onClick={() => setSelectedAgentId(ag.id)}
                              className={`cursor-pointer transition-all border ${
                                ag.id === selectedAgentId
                                  ? 'border-[var(--primary)] bg-[var(--primary)]/10 shadow-xs'
                                  : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/50'
                              }`}
                            >
                              <CardContent className="p-2.5 space-y-2">
                                <div className="flex items-center justify-between gap-1">
                                  <div className="flex items-center gap-1.5 min-w-0">
                                    <div className="w-5 h-5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center shrink-0 border border-[var(--border)] bg-[var(--input)]/40">
                                      <Blobatar name={ag.name} size={20} animate="hover" className="w-full h-full object-contain" />
                                    </div>
                                    <span className="text-xs font-medium truncate text-[var(--foreground)]">{ag.name}</span>
                                  </div>
                                  <Badge variant="running" size="xs">ACTIVE</Badge>
                                </div>
                                <p className="text-[11px] text-[var(--foreground)] font-medium line-clamp-2 leading-tight">
                                  {ag.currentTask}
                                </p>
                                <div className="flex items-center justify-between text-[10px] font-mono text-[var(--muted-foreground)] pt-1 border-t border-[var(--border)]/50">
                                  <span className="truncate">{ag.model}</span>
                                  <Badge variant="outline" size="xs">{ag.badge}</Badge>
                                </div>
                              </CardContent>
                            </Card>
                          ))}
                      </div>
                    </ScrollArea>
                  </div>

                  {/* Column 3: REVIEW / GOVERNANCE */}
                  <div className="flex flex-col gap-2 min-h-0">
                    <div className="flex items-center justify-between px-1 py-0.5 border-b border-[var(--border)]">
                      <div className="flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                        <span className="text-xs font-semibold text-[var(--foreground)]">In Review</span>
                      </div>
                      <Badge variant="outline" size="xs">
                        {agents.filter((a) => a.badge === 'SECURITY' || a.badge === 'SAFETY').length}
                      </Badge>
                    </div>
                    <ScrollArea className="flex-1 [&>div]:!block">
                      <div className="space-y-2 pr-1">
                        {agents
                          .filter((a) => a.badge === 'SECURITY' || a.badge === 'SAFETY')
                          .map((ag) => (
                            <Card
                              key={ag.id}
                              onClick={() => setSelectedAgentId(ag.id)}
                              className={`cursor-pointer transition-all border ${
                                ag.id === selectedAgentId
                                  ? 'border-[var(--primary)] bg-[var(--primary)]/10 shadow-xs'
                                  : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/50'
                              }`}
                            >
                              <CardContent className="p-2.5 space-y-2">
                                <div className="flex items-center justify-between gap-1">
                                  <div className="flex items-center gap-1.5 min-w-0">
                                    <div className="w-5 h-5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center shrink-0 border border-[var(--border)] bg-[var(--input)]/40">
                                      <Blobatar name={ag.name} size={20} animate="hover" className="w-full h-full object-contain" />
                                    </div>
                                    <span className="text-xs font-medium truncate text-[var(--foreground)]">{ag.name}</span>
                                  </div>
                                  <Badge variant="destructive" size="xs">{ag.badge}</Badge>
                                </div>
                                <p className="text-[11px] text-[var(--muted-foreground)] line-clamp-2 leading-tight">
                                  {ag.currentTask}
                                </p>
                                <div className="flex items-center justify-between text-[10px] font-mono text-[var(--muted-foreground)] pt-1 border-t border-[var(--border)]/50">
                                  <span className="truncate">AST Gate / Verify</span>
                                  <span className="text-emerald-500 text-[10px]">PASS</span>
                                </div>
                              </CardContent>
                            </Card>
                          ))}
                      </div>
                    </ScrollArea>
                  </div>

                  {/* Column 4: COMPLETED */}
                  <div className="flex flex-col gap-2 min-h-0">
                    <div className="flex items-center justify-between px-1 py-0.5 border-b border-[var(--border)]">
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                        <span className="text-xs font-semibold text-[var(--foreground)]">Done</span>
                      </div>
                      <Badge variant="completed" size="xs">
                        {agents.filter((a) => a.logs.length > 2).length}
                      </Badge>
                    </div>
                    <ScrollArea className="flex-1 [&>div]:!block">
                      <div className="space-y-2 pr-1">
                        {agents
                          .filter((a) => a.logs.length > 2)
                          .map((ag) => (
                            <Card
                              key={ag.id}
                              onClick={() => setSelectedAgentId(ag.id)}
                              className={`cursor-pointer transition-all border ${
                                ag.id === selectedAgentId
                                  ? 'border-[var(--primary)] bg-[var(--primary)]/10 shadow-xs'
                                  : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/50'
                              }`}
                            >
                              <CardContent className="p-2.5 space-y-2">
                                <div className="flex items-center justify-between gap-1">
                                  <div className="flex items-center gap-1.5 min-w-0">
                                    <div className="w-5 h-5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center shrink-0 border border-[var(--border)] bg-[var(--input)]/40">
                                      <Blobatar name={ag.name} size={20} animate="hover" className="w-full h-full object-contain" />
                                    </div>
                                    <span className="text-xs font-medium truncate text-[var(--foreground)]">{ag.name}</span>
                                  </div>
                                  <Badge variant="completed" size="xs">VERIFIED</Badge>
                                </div>
                                <p className="text-[11px] text-[var(--muted-foreground)] line-clamp-2 leading-tight">
                                  {ag.logs[ag.logs.length - 1]}
                                </p>
                                <div className="flex items-center justify-between text-[10px] font-mono text-[var(--muted-foreground)] pt-1 border-t border-[var(--border)]/50">
                                  <span className="truncate">{ag.engine}</span>
                                  <span className="text-emerald-500 text-[10px]">100% OK</span>
                                </div>
                              </CardContent>
                            </Card>
                          ))}
                      </div>
                    </ScrollArea>
                  </div>
                </div>
              </div>
            )}

            {/* ── VIEW 4: DIRECT 1-ON-1 AGENT CHAT VIEW (ASSISTANT-UI + REUI) ── */}
            {officeMode === 'chat' && selectedAgent && (
              <div className="flex-1 min-h-0 min-w-0 w-full h-full flex flex-col overflow-hidden bg-[var(--background)]">
                <AgentDirectChatView
                  key={selectedAgent.id}
                  agent={selectedAgent}
                  onBackToFloor={() => setOfficeMode('spatial')}
                  onUpdateAgent={(updated) => {
                    setAgents((prev) =>
                      prev.map((a) => (a.id === selectedAgent.id ? { ...a, ...updated } : a))
                    )
                    api.saveAgent({
                      id: selectedAgent.id,
                      name: selectedAgent.name,
                      role: selectedAgent.role,
                      specialty: selectedAgent.specialty,
                      color: selectedAgent.color,
                      default_tool: updated.engine ?? selectedAgent.engine,
                      risk_tier: selectedAgent.safetyTier || 'L1_MUTATION',
                      model_id: updated.model ?? selectedAgent.model,
                      worktree: selectedAgent.workspace,
                      allowed_tools: selectedAgent.tools,
                      allowed_skills: (selectedAgent as any).allowed_skills || [],
                      prompt_prefix: selectedAgent.personality,
                    } as any).catch((err) => {
                      console.error('Failed to persist agent engine/model update:', err)
                    })
                  }}
                  onUpdateAgentStatus={(agentId, status, speech) => {
                    setAgents((prev) =>
                      prev.map((a) =>
                        a.id === agentId
                          ? {
                              ...a,
                              status,
                              speechBubble: speech ?? a.speechBubble,
                            }
                          : a
                      )
                    )
                  }}
                />
              </div>
            )}
          </FramePanel>
        </Frame>

        {/* RIGHT COLUMN: 2 Separate ReUI Frame Blocks (Overview + Activity Logs) */}
        {officeMode !== 'chat' && (
          <div className="flex flex-col gap-2 h-full min-h-0 min-w-0 w-full overflow-hidden">

          {/* ── TOP FRAME BLOCK: Agent Details ── */}
          <Frame className="flex-shrink-0 min-h-0 min-w-0 w-full overflow-hidden">
            <FramePanel className="flex flex-col p-0 overflow-hidden min-w-0 w-full bg-[var(--card)] border-[var(--border)]">
              {/* Agent Details Header */}
              <FrameHeader className="p-2.5 border-b border-[var(--border)] flex flex-row items-center justify-between shrink-0 min-w-0 w-full">
                <div className="flex items-center gap-1.5 min-w-0">
                  <FrameTitle className="text-xs truncate">Agent Details</FrameTitle>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => {
                      setAgents((prev) =>
                        prev.map((ag) =>
                          ag.id === selectedAgent.id
                            ? { ...ag, status: 'IDLE', currentTask: 'Decommissioned by user' }
                            : ag
                        )
                      )
                    }}
                    className="h-6 px-2 text-[9px] font-mono shrink-0"
                    title="Decommission & Reset this Agent"
                  >
                    <Trash2 className="w-2.5 h-2.5 mr-1" />
                    FIRE
                  </Button>
                </div>
              </FrameHeader>

              <ScrollArea className="p-2.5 w-full min-w-0 [&>div]:!block">
                <div className="flex flex-col gap-2 w-full min-w-0">
                  {/* 1. Active Agent Profile using ReUI Card */}
                  <Card className="bg-[var(--input)]/40 border-[var(--border)] shadow-none w-full min-w-0">
                    <CardContent className="p-2.5 flex items-center gap-2.5 w-full min-w-0">
                      <div className="w-12 h-14 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center border border-[var(--border)] shadow-2xs shrink-0 bg-[var(--input)]/60">
                        <Blobatar name={selectedAgent.name} size={48} animate="always" className="w-full h-full object-contain" />
                      </div>

                      <div className="min-w-0 flex-1 overflow-hidden">
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="text-xs font-bold font-mono text-[var(--foreground)] tracking-wide uppercase truncate">
                            {selectedAgent.name}
                          </span>
                          <Badge variant={selectedAgent.badgeVariant} size="xs" className="shrink-0">
                            {selectedAgent.status}
                          </Badge>
                        </div>
                        <div className="text-[10px] text-[var(--muted-foreground)] font-sans truncate">
                          {selectedAgent.role}
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* 2. Tactical Action Buttons: [CHAT] [EDIT] [FILES] using ReUI Button */}
                  <div className="flex items-center gap-1.5 w-full min-w-0">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setOfficeMode('chat')
                        setAgents((prev) =>
                          prev.map((ag) =>
                            ag.id === selectedAgent.id
                              ? {
                                ...ag,
                                speechBubble: `Direct channel open: ${selectedAgent.name}`,
                                logs: [
                                  ...ag.logs,
                                  `[${new Date().toLocaleTimeString()}] Direct interactive session opened with ${selectedAgent.name}`,
                                ],
                              }
                              : ag
                          )
                        )
                      }}
                      className="flex-1 h-7 min-w-0 px-1 text-[10px] font-semibold tracking-wider font-mono gap-1 text-purple-400 hover:text-purple-300 border-purple-500/30 hover:bg-purple-500/10"
                    >
                      <MessageSquare className="w-3 h-3 text-purple-400 shrink-0" />
                      <span className="truncate">CHAT</span>
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenEditModal(selectedAgent)}
                      className="flex-1 h-7 min-w-0 px-1 text-[10px] font-semibold tracking-wider font-mono gap-1 text-[var(--primary)] border-[var(--primary)]/30 hover:bg-[var(--primary)]/10"
                      title="Edit Agent Configuration"
                    >
                      <Edit3 className="w-3 h-3 text-[var(--primary)] shrink-0" />
                      <span className="truncate">EDIT</span>
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleOpenFilesModal}
                      className="flex-1 h-7 min-w-0 px-1 text-[10px] font-semibold tracking-wider font-mono gap-1 text-cyan-400 hover:text-cyan-300 border-cyan-500/30 hover:bg-cyan-500/10"
                      title="Manage Agent Context Files & SOUL.md"
                    >
                      <Folder className="w-3 h-3 text-cyan-400 shrink-0" />
                      <span className="truncate">FILES</span>
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setAgentToDismiss(selectedAgent)}
                      className="h-7 px-2 text-[10px] font-semibold tracking-wider font-mono gap-1 text-red-400 hover:text-red-300 border-red-500/30 hover:bg-red-500/10 shrink-0"
                      title="Dismiss Agent from Fleet"
                    >
                      <Trash2 className="w-3 h-3 text-red-400 shrink-0" />
                      <span className="hidden sm:inline">DISMISS</span>
                    </Button>
                  </div>

                  {/* 3. Collapsible "AGENT ENVIRONMENT & CONTROLS" Drawer */}
                  <Card className="border-[var(--border)] bg-[var(--input)]/20 shadow-none overflow-hidden w-full min-w-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsEnvDrawerOpen((prev) => !prev)}
                      className="w-full h-8 px-2.5 flex items-center justify-between text-left rounded-none hover:bg-[var(--muted)]/50"
                    >
                      <span className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--primary)]">
                        <Sliders className="w-3 h-3" />
                        <span>ENVIRONMENT</span>
                      </span>
                      {isEnvDrawerOpen ? (
                        <ChevronUp className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                      )}
                    </Button>

                    {isEnvDrawerOpen && (
                      <CardContent className="p-2 space-y-2 border-t border-[var(--border)] text-xs font-mono w-full min-w-0">
                        {/* ENGINE ROW */}
                        <div className="flex items-center justify-between gap-1.5 w-full min-w-0">
                          <span className="text-[10px] uppercase font-mono text-[var(--muted-foreground)] w-20 shrink-0">
                            ENGINE :
                          </span>
                          <div className="flex-1 flex items-center gap-1.5 px-2 py-1 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/40 border border-[var(--border)] text-[10px] font-mono text-[var(--foreground)] min-w-0">
                            <Terminal className="w-3 h-3 text-[var(--primary)] shrink-0" />
                            <span className="truncate">{getEngineLabel(selectedAgent.engine)}</span>
                          </div>
                        </div>

                        {/* WORKSPACE ROW */}
                        <div className="flex items-center justify-between gap-1.5 w-full min-w-0">
                          <span className="text-[10px] uppercase font-mono text-[var(--muted-foreground)] w-20 shrink-0">
                            WORKSPACE :
                          </span>
                          <div
                            title={selectedAgent.workspace}
                            className="flex-1 flex items-center gap-1.5 px-2 py-1 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/40 border border-[var(--border)] text-[10px] font-mono text-[var(--foreground)] min-w-0"
                          >
                            <Folder className="w-3 h-3 text-cyan-400 shrink-0" />
                            <span className="truncate">{getWorkspaceLabel(selectedAgent.workspace)}</span>
                          </div>
                        </div>

                        {/* MODEL ROW */}
                        <div className="flex items-center justify-between gap-1.5 w-full min-w-0">
                          <span className="text-[10px] uppercase font-mono text-[var(--muted-foreground)] w-20 shrink-0">
                            MODEL :
                          </span>
                          <div className="flex-1 flex items-center gap-1.5 px-2 py-1 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/40 border border-[var(--border)] text-[10px] font-mono text-[var(--foreground)] min-w-0">
                            <Cpu className="w-3 h-3 text-purple-400 shrink-0" />
                            <span className="truncate">{getModelLabel(selectedAgent.model)}</span>
                          </div>
                        </div>

                        {/* SAFETY TIER ROW */}
                        <div className="flex items-center justify-between gap-1.5 w-full min-w-0">
                          <span className="text-[10px] uppercase font-mono text-[var(--muted-foreground)] w-20 shrink-0">
                            SAFETY TIER :
                          </span>
                          <div className="flex-1 flex items-center gap-1.5 px-2 py-1 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/40 border border-[var(--border)] text-[10px] font-mono text-[var(--foreground)] min-w-0">
                            {selectedAgent.safetyTier === 'L0_READ_ONLY' ? (
                              <Shield className="w-3 h-3 text-emerald-400 shrink-0" />
                            ) : selectedAgent.safetyTier === 'L2_DESTRUCTIVE' ? (
                              <AlertCircle className="w-3 h-3 text-red-400 shrink-0" />
                            ) : (
                              <Zap className="w-3 h-3 text-amber-400 shrink-0" />
                            )}
                            <span className="truncate">{getSafetyTierLabel(selectedAgent.safetyTier)}</span>
                          </div>
                        </div>
                      </CardContent>
                    )}
                  </Card>
                </div>
              </ScrollArea>
            </FramePanel>
          </Frame>

          {/* ── BOTTOM FRAME BLOCK: Activity Logs ── */}
          <Frame className="flex-1 min-h-0 min-w-0 w-full overflow-hidden">
            <FramePanel className="flex flex-col h-full min-h-0 min-w-0 w-full p-0 overflow-hidden bg-[var(--card)] border-[var(--border)]">
              {/* Activity & Logs Header with Filter Tabs & Live Pulse */}
              <FrameHeader className="p-2 border-b border-[var(--border)] flex flex-row items-center justify-between shrink-0 gap-1.5 flex-wrap">
                <div className="flex items-center gap-1.5 min-w-0">
                  <FrameTitle className="text-xs">Live Logs</FrameTitle>
                  <span className="flex items-center gap-1 text-[9px] font-mono font-medium px-1.5 py-0.2 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    LIVE
                  </span>
                  <Badge variant="outline" className="text-[9px] font-mono px-1 py-0 h-4 text-muted-foreground border-border">
                    {displayedLogs.length}
                  </Badge>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <div className="flex items-center bg-muted/60 p-0.5 rounded-md border border-border">
                    <button
                      type="button"
                      onClick={() => setLogFilterMode('agent')}
                      className={`px-1.5 py-0.5 text-[9px] font-mono rounded transition-colors ${
                        logFilterMode === 'agent'
                          ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                      title={`Show logs for ${selectedAgent?.name || 'selected agent'}`}
                    >
                      AGENT
                    </button>
                    <button
                      type="button"
                      onClick={() => setLogFilterMode('errors')}
                      className={`px-1.5 py-0.5 text-[9px] font-mono rounded transition-colors ${
                        logFilterMode === 'errors'
                          ? 'bg-destructive text-destructive-foreground font-semibold shadow-xs'
                          : 'text-muted-foreground hover:text-destructive'
                      }`}
                      title="Show errors only"
                    >
                      ERR
                    </button>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setAutoFollowLogs(!autoFollowLogs)}
                    className="h-5 w-5 p-0 text-muted-foreground hover:text-foreground"
                    title={autoFollowLogs ? 'Auto-scroll ON' : 'Auto-scroll OFF'}
                  >
                    {autoFollowLogs ? <Play className="w-2.5 h-2.5 text-emerald-500" /> : <Pause className="w-2.5 h-2.5 text-amber-500" />}
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopyLogs}
                    className="h-5 px-1.5 text-[9px] font-mono gap-1"
                  >
                    {copiedLogs ? <Check className="w-2.5 h-2.5 text-emerald-500" /> : <Copy className="w-2.5 h-2.5" />}
                    <span>{copiedLogs ? 'COPIED' : 'COPY'}</span>
                  </Button>
                </div>
              </FrameHeader>

              {/* Sub-bar with Live Search Input */}
              <div className="px-2 py-1 bg-muted/30 border-b border-border/60 flex items-center gap-1.5">
                <Search className="w-3 h-3 text-muted-foreground shrink-0" />
                <input
                  type="text"
                  placeholder="Filter logs by keyword or tool..."
                  value={logSearchQuery}
                  onChange={(e) => setLogSearchQuery(e.target.value)}
                  className="w-full bg-transparent text-[10px] text-foreground placeholder:text-muted-foreground/60 focus:outline-hidden font-mono"
                />
                {logSearchQuery && (
                  <button
                    type="button"
                    onClick={() => setLogSearchQuery('')}
                    className="text-[9px] text-muted-foreground hover:text-foreground"
                  >
                    <X className="w-2.5 h-2.5" />
                  </button>
                )}
              </div>

              {/* Monospace Live Logs Feed */}
              <ScrollArea className="flex-1 p-2 font-mono text-[10px] text-[var(--foreground)]">
                {displayedLogs.length === 0 ? (
                  <div className="p-4 text-center text-muted-foreground space-y-1">
                    <Terminal className="w-5 h-5 mx-auto opacity-30" />
                    <p className="text-[10px]">No logs recorded matching this filter.</p>
                    {logFilterMode === 'agent' && selectedAgent && selectedAgent.logs.length > 0 && (
                      <div className="mt-2 text-left space-y-1">
                        <div className="text-[9px] text-muted-foreground uppercase tracking-wider font-semibold">Registered Status:</div>
                        {selectedAgent.logs.map((agLog, idx) => (
                          <div key={idx} className="p-1 rounded bg-muted/40 border border-border/50 text-[10px] text-foreground/80">
                            {agLog}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-1 pr-1">
                    {displayedLogs.map((entry) => {
                      const lvl = (entry.level || entry.type || 'INFO').toUpperCase()
                      const isError = lvl.includes('ERR') || entry.text.toLowerCase().includes('error')
                      const isWarn = lvl.includes('WARN')
                      return (
                        <div
                          key={entry.id}
                          className={`leading-relaxed p-1 rounded-sm border break-all text-[10px] transition-colors select-text flex items-start gap-1.5 ${
                            isError
                              ? 'bg-destructive/15 border-destructive/40 text-destructive-foreground'
                              : isWarn
                              ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                              : 'bg-[var(--input)]/30 border-[var(--border)]/50 text-[var(--foreground)] hover:bg-[var(--muted)]/40'
                          }`}
                        >
                          <span className="text-muted-foreground shrink-0 text-[9px] select-none">
                            [{entry.time}]
                          </span>
                          <span className="text-[9px] font-semibold px-1 rounded bg-muted border border-border shrink-0 select-none uppercase">
                            {entry.source}
                          </span>
                          {isError && (
                            <span className="text-red-400 font-bold shrink-0 text-[9px] select-none">
                              [ERR]
                            </span>
                          )}
                          {isWarn && (
                            <span className="text-amber-400 font-bold shrink-0 text-[9px] select-none">
                              [WARN]
                            </span>
                          )}
                          <span className="flex-1 whitespace-pre-wrap">{entry.text}</span>
                        </div>
                      )
                    })}
                    <div ref={logsEndRef} />
                  </div>
                )}
              </ScrollArea>
            </FramePanel>
          </Frame>

        </div>
        )}

      </div>

      {/* ── Add Agent Modal Dialog ── */}
      {isAddAgentOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 animate-in fade-in duration-150">
          <Frame className="w-full max-w-lg shadow-2xl border-[var(--border)] max-h-[90vh] flex flex-col">
            <FramePanel className="bg-[var(--card)] border-[var(--border)] p-0 overflow-hidden flex flex-col max-h-[90vh]">
              {/* Header */}
              <FrameHeader className="p-3 border-b border-[var(--border)] flex flex-row items-center justify-between shrink-0">
                <FrameTitle className="text-sm font-semibold text-[var(--foreground)]">
                  Add New Agent
                </FrameTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsAddAgentOpen(false)}
                  className="h-6 w-6 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  <X className="w-4 h-4" />
                </Button>
              </FrameHeader>

              {/* Scrollable Form Content */}
              <ScrollArea className="flex-1 p-4 overflow-y-auto">
                <div className="space-y-3.5 pr-1">

                  {/* 1. SELECT AVATAR & NAME */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Select Avatar & Name</label>
                    <div className="flex items-center gap-3 p-2.5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/30 border border-[var(--border)]">
                      <div className="w-14 h-14 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center border border-[var(--border)] bg-[var(--card)] shadow-xs shrink-0 p-1">
                        <Blobatar name={newAgentName || newAgentAvatar} size={48} animate="always" className="w-full h-full object-contain" />
                      </div>
                      <div className="flex-1 space-y-2 min-w-0">
                        <input
                          type="text"
                          value={newAgentName}
                          onChange={(e) => {
                            setNewAgentName(e.target.value)
                            if (e.target.value) setNewAgentAvatar(e.target.value)
                          }}
                          placeholder="Agent Name (e.g. Andy, Creed, Erin...)"
                          className="w-full h-8 px-2.5 text-xs rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                        />
                        {/* Avatar Presets (Fixed sizing and padding to prevent cutoff) */}
                        <div className="flex items-center gap-1.5 overflow-x-auto py-1 px-0.5 scrollbar-thin">
                          {AVATAR_PRESETS.map((preset) => {
                            const isPicked = (newAgentName === preset) || (newAgentAvatar === preset && !newAgentName)
                            return (
                              <button
                                key={preset}
                                type="button"
                                onClick={() => {
                                  setNewAgentAvatar(preset)
                                  setNewAgentName(preset)
                                }}
                                className={`w-8 h-8 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] flex items-center justify-center shrink-0 border transition-all ${isPicked
                                  ? 'border-[var(--primary)] ring-2 ring-[var(--primary)]/30 bg-[var(--primary)]/10 scale-105'
                                  : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--muted-foreground)] opacity-75 hover:opacity-100'
                                  }`}
                                title={preset}
                              >
                                <Blobatar name={preset} size={24} animate="hover" className="w-full h-full object-contain" />
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 2. SHORT DESCRIPTION */}
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Short Description</label>
                    <input
                      type="text"
                      value={newAgentRole}
                      onChange={(e) => setNewAgentRole(e.target.value)}
                      placeholder="e.g. Frontend Specialist, PR Reviewer, Dev Hunter"
                      className="w-full h-8 px-2.5 text-xs rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                    />
                  </div>

                  {/* 3. INSTRUCTION INPUT */}
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Instructions / Prompt</label>
                    <textarea
                      rows={3}
                      value={newAgentInstructions}
                      onChange={(e) => setNewAgentInstructions(e.target.value)}
                      placeholder="e.g. You are an autonomous coding specialist under Zezo OS. Always adhere strictly to antislop rules, cyclomatic complexity < 15, and verified tests..."
                      className="w-full p-2.5 text-xs font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)] resize-none"
                    />
                  </div>

                  {/* 4. SELECT WORKSPACE FOLDER (VS Code style Open Folder Picker) */}
                  <div className="space-y-1.5 pt-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase flex items-center gap-1.5">
                        <FolderOpen className="w-3.5 h-3.5 text-[var(--primary)]" />
                        <span>Workspace Folder</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setNewAgentWorkspace('c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57')}
                        className="text-[10px] font-mono text-[var(--primary)] hover:underline opacity-80 hover:opacity-100"
                      >
                        Reset to Active Repo
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <input
                        type="file"
                        ref={folderInputRef}
                        className="hidden"
                        // @ts-expect-error webkitdirectory is standard in modern Chromium/desktop browsers
                        webkitdirectory=""
                        directory=""
                        onChange={(e) => {
                          const files = e.target.files
                          if (files && files.length > 0) {
                            const folderPath = files[0].webkitRelativePath?.split('/')[0] || files[0].name || 'Selected Folder'
                            setNewAgentWorkspace(folderPath)
                          }
                        }}
                      />
                      <div className="relative flex-1 min-w-0">
                        <input
                          type="text"
                          value={newAgentWorkspace}
                          onChange={(e) => setNewAgentWorkspace(e.target.value)}
                          placeholder="c:/path/to/workspace or select folder..."
                          className="w-full h-8 pl-8 pr-2.5 text-xs font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                        />
                        <Folder className="w-3.5 h-3.5 text-cyan-400 absolute left-2.5 top-2.5" />
                      </div>

                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => folderInputRef.current?.click()}
                        className="h-8 text-xs font-mono px-3 gap-1.5 shrink-0 bg-[var(--input)]/40 hover:bg-[var(--muted)] border-[var(--border)] text-[var(--foreground)]"
                        title="Open Folder (Browse local directory)"
                      >
                        <FolderOpen className="w-3.5 h-3.5 text-[var(--primary)]" />
                        <span>Open Folder</span>
                      </Button>
                    </div>
                  </div>

                  {/* 5. ENGINE & TARGET MODEL */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                    <div className="space-y-1">
                      <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Engine</label>
                      <Select
                        value={newAgentEngine}
                        onValueChange={(val) => {
                          setNewAgentEngine(val)
                          const available = ENGINE_MODELS_MAP[val]
                          if (available && available.length > 0) {
                            setNewAgentModel(available[0].id)
                          }
                        }}
                      >
                        <SelectTrigger className="h-8 text-xs font-mono">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="opencode_run">OpenCode</SelectItem>
                          <SelectItem value="kilo_run">KiloCode</SelectItem>
                          <SelectItem value="antigravity_run">Antigravity</SelectItem>
                          <SelectItem value="groq">Groq</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Target Model</label>
                      <Select value={newAgentModel} onValueChange={setNewAgentModel}>
                        <SelectTrigger className="h-8 text-xs font-mono">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {(ENGINE_MODELS_MAP[newAgentEngine] || ENGINE_MODELS_MAP['opencode_run']).map((m) => (
                            <SelectItem key={m.id} value={m.id}>
                              {m.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* 6. SKILLS & TOOLS TAB LAYOUT */}
                  <div className="space-y-2 pt-1">
                    <Tabs defaultValue="skills" className="w-full">
                      <div className="flex items-center justify-between pb-1.5">
                        <TabsList className="h-7.5 p-0.5 bg-[var(--input)]/80 border border-[var(--border)]">
                          <TabsTrigger value="skills" className="text-xs h-6.5 px-3 gap-1.5 font-mono">
                            <Sparkles className="w-3 h-3 text-amber-400" />
                            <span>Skills ({newAgentSelectedSkills.length})</span>
                          </TabsTrigger>
                          <TabsTrigger value="tools" className="text-xs h-6.5 px-3 gap-1.5 font-mono">
                            <Wrench className="w-3 h-3 text-cyan-400" />
                            <span>Tools ({newAgentSelectedTools.length})</span>
                          </TabsTrigger>
                        </TabsList>

                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => {
                              if (newAgentSelectedSkills.length === AVAILABLE_SKILLS.length) {
                                setNewAgentSelectedSkills([])
                              } else {
                                setNewAgentSelectedSkills(AVAILABLE_SKILLS.map((s) => s.id))
                              }
                            }}
                            className="text-[10px] font-mono text-[var(--muted-foreground)] hover:text-[var(--foreground)] px-2 py-0.5 rounded border border-[var(--border)] bg-[var(--input)]/30 hover:bg-[var(--muted)]"
                          >
                            {newAgentSelectedSkills.length === AVAILABLE_SKILLS.length ? 'Clear Skills' : 'All Skills'}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              if (newAgentSelectedTools.length === AVAILABLE_TOOLS.length) {
                                setNewAgentSelectedTools([])
                              } else {
                                setNewAgentSelectedTools(AVAILABLE_TOOLS.map((t) => t.id))
                              }
                            }}
                            className="text-[10px] font-mono text-[var(--muted-foreground)] hover:text-[var(--foreground)] px-2 py-0.5 rounded border border-[var(--border)] bg-[var(--input)]/30 hover:bg-[var(--muted)]"
                          >
                            {newAgentSelectedTools.length === AVAILABLE_TOOLS.length ? 'Clear Tools' : 'All Tools'}
                          </button>
                        </div>
                      </div>

                      {/* SKILLS TAB CONTENT */}
                      <TabsContent value="skills" className="mt-1">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-44 overflow-y-auto pr-1">
                          {AVAILABLE_SKILLS.map((skill) => {
                            const isSelected = newAgentSelectedSkills.includes(skill.id)
                            return (
                              <button
                                key={skill.id}
                                type="button"
                                onClick={() => toggleSkill(skill.id)}
                                className={`flex flex-col items-start p-2 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] border text-left transition-all ${isSelected
                                  ? 'bg-[var(--primary)]/15 border-[var(--primary)] text-[var(--foreground)] ring-1 ring-[var(--primary)]/30'
                                  : 'bg-[var(--input)]/30 border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--input)]/50'
                                  }`}
                              >
                                <div className="flex items-center justify-between w-full gap-1">
                                  <span className="text-xs font-mono font-semibold text-[var(--foreground)] truncate">
                                    {isSelected ? '✓ ' : '+ '}{skill.name}
                                  </span>
                                  {isSelected && (
                                    <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-[var(--primary)]/20 text-[var(--primary)] shrink-0 font-bold">
                                      ACTIVE
                                    </span>
                                  )}
                                </div>
                                <span className="text-[10px] text-[var(--muted-foreground)] line-clamp-1 mt-0.5">
                                  {skill.desc}
                                </span>
                              </button>
                            )
                          })}
                        </div>
                      </TabsContent>

                      {/* TOOLS TAB CONTENT */}
                      <TabsContent value="tools" className="mt-1">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-44 overflow-y-auto pr-1">
                          {AVAILABLE_TOOLS.map((tool) => {
                            const isSelected = newAgentSelectedTools.includes(tool.id)
                            return (
                              <button
                                key={tool.id}
                                type="button"
                                onClick={() => toggleTool(tool.id)}
                                className={`flex flex-col items-start p-2 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] border text-left transition-all ${isSelected
                                  ? 'bg-cyan-500/15 border-cyan-500 text-[var(--foreground)] ring-1 ring-cyan-500/30'
                                  : 'bg-[var(--input)]/30 border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--input)]/50'
                                  }`}
                              >
                                <div className="flex items-center justify-between w-full gap-1">
                                  <span className="text-xs font-mono font-semibold text-[var(--foreground)] truncate">
                                    {isSelected ? '✓ ' : '+ '}{tool.name}
                                  </span>
                                  {isSelected && (
                                    <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-cyan-500/20 text-cyan-400 shrink-0 font-bold">
                                      ACTIVE
                                    </span>
                                  )}
                                </div>
                                <span className="text-[10px] text-[var(--muted-foreground)] line-clamp-1 mt-0.5">
                                  {tool.desc}
                                </span>
                              </button>
                            )
                          })}
                        </div>
                      </TabsContent>
                    </Tabs>
                  </div>

                </div>
              </ScrollArea>

              {/* Modal Footer */}
              <div className="p-3 border-t border-[var(--border)] flex items-center justify-end gap-2 shrink-0 bg-[var(--card)]">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsAddAgentOpen(false)}
                  className="h-7 text-xs px-3"
                >
                  Cancel
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleCreateNewAgent}
                  className="h-7 text-xs px-3 gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Create Agent</span>
                </Button>
              </div>
            </FramePanel>
          </Frame>
        </div>
      )}

      {/* ── Edit Agent Modal Dialog ── */}
      {isEditAgentOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 animate-in fade-in duration-150">
          <Frame className="w-full max-w-lg shadow-2xl border-[var(--border)] max-h-[90vh] flex flex-col">
            <FramePanel className="bg-[var(--card)] border-[var(--border)] p-0 overflow-hidden flex flex-col max-h-[90vh]">
              {/* Header */}
              <FrameHeader className="p-3 border-b border-[var(--border)] flex flex-row items-center justify-between shrink-0">
                <div className="flex items-center gap-2">
                  <FrameTitle className="text-sm font-semibold text-[var(--foreground)]">
                    Edit Agent: {selectedAgent.name}
                  </FrameTitle>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsEditAgentOpen(false)}
                  className="h-6 w-6 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  <X className="w-4 h-4" />
                </Button>
              </FrameHeader>

              {/* Scrollable Form Content */}
              <ScrollArea className="flex-1 p-4 overflow-y-auto">
                <div className="space-y-3.5 pr-1">
                  {/* 1. AVATAR & NAME */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Agent Name & Identity</label>
                    <div className="flex items-center gap-3 p-2.5 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/30 border border-[var(--border)]">
                      <div className="w-14 h-14 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center border border-[var(--border)] bg-[var(--card)] shadow-xs shrink-0 p-1">
                        <Blobatar name={editAgentName || selectedAgent.name} size={48} animate="always" className="w-full h-full object-contain" />
                      </div>
                      <div className="flex-1 space-y-2 min-w-0">
                        <input
                          type="text"
                          value={editAgentName}
                          onChange={(e) => setEditAgentName(e.target.value)}
                          placeholder="Agent Name..."
                          className="w-full h-8 px-2.5 text-xs rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                        />
                        {/* Avatar Presets */}
                        <div className="flex items-center gap-1.5 overflow-x-auto py-1 px-0.5 scrollbar-thin">
                          {AVATAR_PRESETS.map((preset) => {
                            const isPicked = editAgentName === preset
                            return (
                              <button
                                key={preset}
                                type="button"
                                onClick={() => setEditAgentName(preset)}
                                className={`w-8 h-8 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] flex items-center justify-center shrink-0 border transition-all ${
                                  isPicked
                                    ? 'border-[var(--primary)] ring-2 ring-[var(--primary)]/30 bg-[var(--primary)]/10 scale-105'
                                    : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--muted-foreground)] opacity-75 hover:opacity-100'
                                }`}
                                title={preset}
                              >
                                <Blobatar name={preset} size={24} animate="hover" className="w-full h-full object-contain" />
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 2. ROLE */}
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Role / Title</label>
                    <input
                      type="text"
                      value={editAgentRole}
                      onChange={(e) => setEditAgentRole(e.target.value)}
                      placeholder="e.g. Lead Software Architect, Tech Lead..."
                      className="w-full h-8 px-2.5 text-xs rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                    />
                  </div>

                  {/* 3. INSTRUCTIONS / PERSONALITY */}
                  <div className="space-y-1">
                    <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Instructions / Personality</label>
                    <textarea
                      rows={3}
                      value={editAgentPersonality}
                      onChange={(e) => setEditAgentPersonality(e.target.value)}
                      placeholder="Agent behavior rules and guidelines..."
                      className="w-full p-2.5 text-xs font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)] resize-none"
                    />
                  </div>

                  {/* 4. WORKSPACE FOLDER */}
                  <div className="space-y-1.5 pt-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase flex items-center gap-1.5">
                        <FolderOpen className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Workspace Folder</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setEditAgentWorkspace('c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57')}
                        className="text-[10px] font-mono text-[var(--primary)] hover:underline opacity-80 hover:opacity-100"
                      >
                        Reset to Active Repo
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <input
                        type="file"
                        ref={editFolderInputRef}
                        className="hidden"
                        // @ts-expect-error webkitdirectory is standard in modern Chromium/desktop browsers
                        webkitdirectory=""
                        directory=""
                        onChange={(e) => {
                          const files = e.target.files
                          if (files && files.length > 0) {
                            const folderPath = files[0].webkitRelativePath?.split('/')[0] || files[0].name || 'Selected Folder'
                            setEditAgentWorkspace(folderPath)
                          }
                        }}
                      />
                      <div className="relative flex-1 min-w-0">
                        <input
                          type="text"
                          value={editAgentWorkspace}
                          onChange={(e) => setEditAgentWorkspace(e.target.value)}
                          placeholder="c:/path/to/workspace..."
                          className="w-full h-8 pl-8 pr-2.5 text-xs font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                        />
                        <Folder className="w-3.5 h-3.5 text-cyan-400 absolute left-2.5 top-2.5" />
                      </div>

                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => editFolderInputRef.current?.click()}
                        className="h-8 text-xs font-mono px-3 gap-1.5 shrink-0 bg-[var(--input)]/40 hover:bg-[var(--muted)] border-[var(--border)] text-[var(--foreground)]"
                      >
                        <FolderOpen className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Browse</span>
                      </Button>
                    </div>
                  </div>

                  {/* 5. ENGINE & TARGET MODEL */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                    <div className="space-y-1">
                      <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Engine</label>
                      <Select
                        value={editAgentEngine}
                        onValueChange={(val) => {
                          setEditAgentEngine(val)
                          const available = ENGINE_MODELS_MAP[val]
                          if (available && available.length > 0) {
                            setEditAgentModel(available[0].id)
                          }
                        }}
                      >
                        <SelectTrigger className="h-8 text-xs font-mono">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="opencode_run">OpenCode</SelectItem>
                          <SelectItem value="kilo_run">KiloCode</SelectItem>
                          <SelectItem value="antigravity_run">Antigravity</SelectItem>
                          <SelectItem value="groq">Groq</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Target Model</label>
                      <Select value={editAgentModel} onValueChange={setEditAgentModel}>
                        <SelectTrigger className="h-8 text-xs font-mono">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {(ENGINE_MODELS_MAP[editAgentEngine] || ENGINE_MODELS_MAP['opencode_run']).map((m) => (
                            <SelectItem key={m.id} value={m.id}>
                              {m.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* 6. SKILLS & TOOLS TABS */}
                  <div className="space-y-2 pt-1">
                    <Tabs defaultValue="skills" className="w-full">
                      <div className="flex items-center justify-between pb-1.5">
                        <TabsList className="h-7.5 p-0.5 bg-[var(--input)]/80 border border-[var(--border)]">
                          <TabsTrigger value="skills" className="text-xs h-6.5 px-3 gap-1.5 font-mono">
                            <Sparkles className="w-3 h-3 text-amber-400" />
                            <span>Skills ({editAgentSkills.length})</span>
                          </TabsTrigger>
                          <TabsTrigger value="tools" className="text-xs h-6.5 px-3 gap-1.5 font-mono">
                            <Wrench className="w-3 h-3 text-cyan-400" />
                            <span>Tools ({editAgentTools.length})</span>
                          </TabsTrigger>
                        </TabsList>
                      </div>

                      {/* SKILLS TAB */}
                      <TabsContent value="skills" className="mt-1">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-40 overflow-y-auto pr-1">
                          {AVAILABLE_SKILLS.map((skill) => {
                            const isSelected = editAgentSkills.includes(skill.id)
                            return (
                              <button
                                key={skill.id}
                                type="button"
                                onClick={() => toggleEditSkill(skill.id)}
                                className={`flex flex-col items-start p-2 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] border text-left transition-all ${
                                  isSelected
                                    ? 'bg-[var(--primary)]/15 border-[var(--primary)] text-[var(--foreground)] ring-1 ring-[var(--primary)]/30'
                                    : 'bg-[var(--input)]/30 border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--input)]/50'
                                }`}
                              >
                                <div className="flex items-center justify-between w-full gap-1">
                                  <span className="text-xs font-mono font-semibold text-[var(--foreground)] truncate">
                                    {isSelected ? '✓ ' : '+ '}{skill.name}
                                  </span>
                                  {isSelected && (
                                    <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-[var(--primary)]/20 text-[var(--primary)] shrink-0 font-bold">
                                      ACTIVE
                                    </span>
                                  )}
                                </div>
                                <span className="text-[10px] text-[var(--muted-foreground)] line-clamp-1 mt-0.5">
                                  {skill.desc}
                                </span>
                              </button>
                            )
                          })}
                        </div>
                      </TabsContent>

                      {/* TOOLS TAB */}
                      <TabsContent value="tools" className="mt-1">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-40 overflow-y-auto pr-1">
                          {AVAILABLE_TOOLS.map((tool) => {
                            const isSelected = editAgentTools.includes(tool.id)
                            return (
                              <button
                                key={tool.id}
                                type="button"
                                onClick={() => toggleEditTool(tool.id)}
                                className={`flex flex-col items-start p-2 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] border text-left transition-all ${
                                  isSelected
                                    ? 'bg-cyan-500/15 border-cyan-500 text-[var(--foreground)] ring-1 ring-cyan-500/30'
                                    : 'bg-[var(--input)]/30 border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--input)]/50'
                                }`}
                              >
                                <div className="flex items-center justify-between w-full gap-1">
                                  <span className="text-xs font-mono font-semibold text-[var(--foreground)] truncate">
                                    {isSelected ? '✓ ' : '+ '}{tool.name}
                                  </span>
                                  {isSelected && (
                                    <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-cyan-500/20 text-cyan-400 shrink-0 font-bold">
                                      ACTIVE
                                    </span>
                                  )}
                                </div>
                                <span className="text-[10px] text-[var(--muted-foreground)] line-clamp-1 mt-0.5">
                                  {tool.desc}
                                </span>
                              </button>
                            )
                          })}
                        </div>
                      </TabsContent>
                    </Tabs>
                  </div>
                </div>
              </ScrollArea>

              {/* Modal Footer */}
              <div className="p-3 border-t border-[var(--border)] flex items-center justify-end gap-2 shrink-0 bg-[var(--card)]">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEditAgentOpen(false)}
                  className="h-7 text-xs px-3"
                >
                  Cancel
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSaveEditAgent}
                  className="h-7 text-xs px-3 gap-1"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Changes</span>
                </Button>
              </div>
            </FramePanel>
          </Frame>
        </div>
      )}

      {/* ── Modal: Manage Files & Soul Live Editor (100% ReUI Component Architecture) ── */}
      {isFilesModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 animate-in fade-in duration-150">
          <Frame className="w-full max-w-3xl shadow-2xl border-[var(--border)] max-h-[88vh] flex flex-col">
            <FramePanel className="bg-[var(--card)] border-[var(--border)] p-0 overflow-hidden flex flex-col max-h-[88vh]">
              {/* Modal Head */}
              <FrameHeader className="p-3 border-b border-[var(--border)] flex flex-row items-center justify-between shrink-0">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
                  <FrameTitle className="text-sm font-semibold text-[var(--foreground)]">
                    Files
                  </FrameTitle>
                  <Badge variant="outline" size="xs" className="font-mono text-cyan-400 border-cyan-500/30">
                    {selectedAgent.name}
                  </Badge>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsFilesModalOpen(false)}
                  className="h-6 w-6 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  <X className="w-4 h-4" />
                </Button>
              </FrameHeader>

              {/* Modal Body: Dual-Pane ReUI Architecture */}
              <div className="flex-1 grid grid-cols-1 md:grid-cols-[250px_1fr] min-h-[460px] overflow-hidden">
                {/* Left Pane: Core File Switchers */}
                <div className="border-r border-[var(--border)] p-3 flex flex-col gap-2.5 bg-[var(--input)]/15 overflow-hidden">
                  <div className="text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--muted-foreground)] px-0.5">
                    Core Persona Files
                  </div>

                  <ScrollArea className="flex-1 pr-1">
                    <div className="flex flex-col gap-1.5 pb-1">
                      {CORE_PERSONA_FILES.map((file) => {
                        const isSelected = selectedPersonaFile === file.id
                        const agentToggles = personaFileToggles[selectedAgent.id] || {
                          'SOUL.md': true,
                          'AGENTS.md': true,
                          'PROFILE.md': true,
                          'MEMORY.md': true,
                        }
                        const isChecked = agentToggles[file.id] ?? true

                        return (
                          <Card
                            key={file.id}
                            onClick={() => handleSelectPersonaFile(file.id)}
                            className={`cursor-pointer transition-colors shadow-none ${
                              isSelected
                                ? 'bg-[var(--primary)]/10 border-[var(--primary)] text-[var(--foreground)] ring-1 ring-[var(--primary)]/30'
                                : 'bg-[var(--card)] border-[var(--border)] hover:bg-[var(--input)]/50 text-[var(--muted-foreground)]'
                            }`}
                          >
                            <CardContent className="p-2.5 flex items-center justify-between gap-2">
                              <div className="min-w-0 flex items-start gap-2.5 flex-1">
                                {file.id === 'SOUL.md' ? (
                                  <FileText className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${file.iconColor}`} />
                                ) : file.id === 'AGENTS.md' ? (
                                  <ShieldCheck className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${file.iconColor}`} />
                                ) : file.id === 'PROFILE.md' ? (
                                  <User className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${file.iconColor}`} />
                                ) : (
                                  <Database className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${file.iconColor}`} />
                                )}
                                <div className="min-w-0 flex-1">
                                  <div className="text-xs font-mono font-semibold text-[var(--foreground)] truncate">
                                    {file.name}
                                  </div>
                                  <div className="text-[11px] text-[var(--muted-foreground)] truncate font-sans">
                                    {file.desc}
                                  </div>
                                </div>
                              </div>

                              <div onClick={(e) => e.stopPropagation()} className="shrink-0 pl-1">
                                <Switch
                                  checked={isChecked}
                                  onCheckedChange={(checked) => handleTogglePersonaFile(file.id, checked)}
                                  className="scale-75 origin-right"
                                />
                              </div>
                            </CardContent>
                          </Card>
                        )
                      })}
                    </div>
                  </ScrollArea>

                  {/* Open in Explorer Button (Single Lucide icon, no duplicate emoji) */}
                  <div className="pt-2 border-t border-[var(--border)] mt-auto shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleOpenActiveWorktreeInExplorer}
                      className="w-full h-8 text-xs font-mono justify-center gap-2 border-[var(--border)] bg-[var(--card)] hover:bg-[var(--muted)] text-[var(--foreground)]"
                      title="Open active worktree folder in Explorer"
                    >
                      <FolderOpen className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Open in Explorer</span>
                    </Button>
                  </div>
                </div>

                {/* Right Pane: Live Editor */}
                <div className="p-3 flex flex-col gap-2 min-h-0 bg-[var(--card)] overflow-hidden">
                  <div className="flex items-center justify-between gap-2 shrink-0 pb-1.5 border-b border-[var(--border)]">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-[var(--primary)] uppercase">
                        {selectedPersonaFile}
                      </span>
                      <Badge variant="outline" size="xs" className="text-[10px] font-mono text-[var(--muted-foreground)]">
                        {selectedPersonaFile === 'SOUL.md'
                          ? 'config/fleet_agents.json'
                          : selectedPersonaFile === 'AGENTS.md'
                          ? 'AGENTS.md (Root Guidelines)'
                          : selectedPersonaFile === 'PROFILE.md'
                          ? 'Agent Identity Specification'
                          : 'memory/zezo_brain.db'}
                      </Badge>
                    </div>

                    <div className="text-[10px] font-mono text-[var(--muted-foreground)]">
                      {personaEditorContent.length} chars
                    </div>
                  </div>

                  {/* Live Monospace Textarea Editor */}
                  <textarea
                    value={personaEditorContent}
                    onChange={(e) => setPersonaEditorContent(e.target.value)}
                    placeholder="File content loading..."
                    className="flex-1 w-full min-h-[280px] p-3 text-xs font-mono bg-[var(--input)]/25 border border-[var(--border)] rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)] resize-none leading-relaxed select-text"
                  />

                  {/* Footer Action Buttons */}
                  <div className="flex items-center justify-end gap-2 pt-1.5 border-t border-[var(--border)] shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setIsFilesModalOpen(false)}
                      className="h-7 text-xs px-3"
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="default"
                      size="sm"
                      onClick={handleSavePersonaFile}
                      className="h-7 text-xs px-3 gap-1.5"
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>Save File</span>
                    </Button>
                  </div>
                </div>
              </div>
            </FramePanel>
          </Frame>
        </div>
      )}

      {/* ReUI Confirmation Dialog for Dismissing Agent */}
      <ConfirmDialog
        open={Boolean(agentToDismiss)}
        onOpenChange={(open) => !open && setAgentToDismiss(null)}
        title="Dismiss Agent from Fleet"
        description={`Are you sure you want to dismiss agent "${agentToDismiss?.name || ''}" from the active fleet?`}
        warningText="This agent process will be terminated, removed from the workspace office matrix, and its heartbeat monitoring will stop."
        confirmText="Dismiss Agent"
        cancelText="Cancel"
        variant="destructive"
        isLoading={isDismissing}
        onConfirm={handleConfirmDismissAgent}
      />
    </div>
  )
}
