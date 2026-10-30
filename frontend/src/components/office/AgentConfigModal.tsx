import React, { useState, useEffect, useRef } from 'react'
import {
  X,
  Save,
  Folder,
  FolderOpen,
  Sparkles,
  Wrench,
  Shield,
  Palette,
  MapPin,
  Check,
  Cpu,
} from 'lucide-react'
import { Frame, FramePanel, FrameHeader, FrameTitle } from '../reui/frame'
import { Badge } from '../reui/badge'
import { Button } from '../ui/button'
import { ScrollArea } from '../ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from '../ui/tabs'
import { Blobatar } from 'blobatar/react'
import type { AgentOfficeMember } from './AutonomousOfficeScreen'
import { ENGINE_MODELS_MAP, WORKSTATION_SLOTS } from './AutonomousOfficeScreen'
import { api } from '../../lib/api'
import type { AgentProfile } from '../../types/zezo'

export interface AgentConfigModalProps {
  isOpen: boolean
  onClose: () => void
  agent: AgentOfficeMember | null
  onSave?: (updatedAgent: AgentOfficeMember) => void
}

export interface SkillItem {
  id: string
  name: string
  desc: string
}

export interface ToolItem {
  id: string
  name: string
  desc: string
}

const DEFAULT_ACTIVE_SKILLS: SkillItem[] = [
  { id: 'website_build', name: 'website_build', desc: 'Studio UI aesthetic, anti-slop rules & design presets' },
  { id: 'website_clone', name: 'website_clone', desc: 'Autonomous full-stack website cloning & styling pipeline' },
  { id: 'generate_design_md', name: 'generate_design_md', desc: 'Generate DESIGN.md UI specs and design tokens' },
]

const AVAILABLE_TOOLS: ToolItem[] = [
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

const COLOR_PRESETS = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ec4899',
  '#8b5cf6',
  '#06b6d4',
  '#f43f5e',
  '#eab308',
]

export const AgentConfigModal: React.FC<AgentConfigModalProps> = ({
  isOpen,
  onClose,
  agent,
  onSave,
}) => {
  if (!isOpen || !agent) return null

  // Local Form States
  const [name, setName] = useState(agent.name || '')
  const [role, setRole] = useState(agent.role || '')
  const [personality, setPersonality] = useState(agent.personality || '')
  const [workspace, setWorkspace] = useState(
    agent.workspace === 'repo_active'
      ? 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57'
      : agent.workspace || 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57'
  )
  const [color, setColor] = useState(agent.color || '#3b82f6')
  const [deskX, setDeskX] = useState<number>(agent.deskPct?.x ?? 50)
  const [deskY, setDeskY] = useState<number>(agent.deskPct?.y ?? 50)
  const [engine, setEngine] = useState(agent.engine || 'opencode_run')
  const [model, setModel] = useState(agent.model || 'gemini-2.5-flash')
  const [riskTier, setRiskTier] = useState(agent.safetyTier || 'L1_MUTATION')
  const [allowedTools, setAllowedTools] = useState<string[]>(() => {
    return Array.isArray(agent.tools) && agent.tools.length > 0
      ? agent.tools
      : ['file_processor', 'file_controller']
  })

  // Dynamic Skills State (loaded from /api/skills)
  const [skillsList, setSkillsList] = useState<SkillItem[]>(DEFAULT_ACTIVE_SKILLS)
  const [allowedSkills, setAllowedSkills] = useState<string[]>(() => {
    if (Array.isArray(agent.allowed_skills) && agent.allowed_skills.length > 0) {
      return agent.allowed_skills
    }
    // Infer existing active skills from specialty if allowed_skills wasn't initialized
    const inferred = DEFAULT_ACTIVE_SKILLS.filter((s) =>
      agent.specialty?.toLowerCase().includes(s.id.toLowerCase())
    ).map((s) => s.id)
    return inferred.length > 0 ? inferred : ['website_build', 'website_clone', 'generate_design_md']
  })

  const [isSaving, setIsSaving] = useState(false)
  const folderInputRef = useRef<HTMLInputElement>(null)

  // Synchronize initial state when agent prop changes
  useEffect(() => {
    setName(agent.name || '')
    setRole(agent.role || '')
    setPersonality(agent.personality || '')
    setWorkspace(
      agent.workspace === 'repo_active'
        ? 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57'
        : agent.workspace || 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57'
    )
    setColor(agent.color || '#3b82f6')
    setDeskX(agent.deskPct?.x ?? 50)
    setDeskY(agent.deskPct?.y ?? 50)
    setEngine(agent.engine || 'opencode_run')
    setModel(agent.model || 'gemini-2.5-flash')
    setRiskTier(agent.safetyTier || 'L1_MUTATION')
    setAllowedTools(
      Array.isArray(agent.tools) && agent.tools.length > 0
        ? agent.tools
        : ['file_processor', 'file_controller']
    )
    if (Array.isArray(agent.allowed_skills) && agent.allowed_skills.length > 0) {
      setAllowedSkills(agent.allowed_skills)
    } else {
      const inferred = DEFAULT_ACTIVE_SKILLS.filter((s) =>
        agent.specialty?.toLowerCase().includes(s.id.toLowerCase())
      ).map((s) => s.id)
      setAllowedSkills(inferred.length > 0 ? inferred : ['website_build', 'website_clone', 'generate_design_md'])
    }
  }, [agent])

  // Load Active Skills from /api/skills
  useEffect(() => {
    let isMounted = true
    const fetchActiveSkills = async () => {
      try {
        const res = await api.getSkills()
        if (isMounted && res && Array.isArray(res.skills) && res.skills.length > 0) {
          const loaded: SkillItem[] = res.skills
            .filter((s: any) => s && s.name && s.name !== 'custom_skill_10' && s.name !== 'hamza_taste')
            .map((s: any) => ({
              id: s.name,
              name: s.display_name || s.name,
              desc: s.description || (s.triggers && s.triggers.length > 0 ? s.triggers.slice(0, 3).join(', ') : 'Autonomous skill module'),
            }))
          if (loaded.length > 0) {
            setSkillsList(loaded)
          }
        }
      } catch (err) {
        console.warn('Failed to load active skills from /api/skills, keeping default active skills:', err)
      }
    }

    fetchActiveSkills()
    window.addEventListener('zezo_skills_updated', fetchActiveSkills)
    return () => {
      isMounted = false
      window.removeEventListener('zezo_skills_updated', fetchActiveSkills)
    }
  }, [])

  // Toggle single skill check/uncheck
  const toggleSkill = (skillId: string) => {
    setAllowedSkills((prev) =>
      prev.includes(skillId) ? prev.filter((s) => s !== skillId) : [...prev, skillId]
    )
  }

  // Toggle single tool check/uncheck
  const toggleTool = (toolId: string) => {
    setAllowedTools((prev) =>
      prev.includes(toolId) ? prev.filter((t) => t !== toolId) : [...prev, toolId]
    )
  }

  // Workstation slot selector handler
  const handleSelectWorkstation = (slotId: string) => {
    const slot = WORKSTATION_SLOTS.find((s) => s.id === slotId)
    if (slot) {
      setDeskX(Number((slot.x + 3.9).toFixed(1)))
      setDeskY(Number((slot.y + 8.8).toFixed(1)))
    }
  }

  // Save handler: updates agent and persists via POST /api/fleet/agents
  const handleSave = async () => {
    setIsSaving(true)
    const updatedName = name.trim() || agent.name
    const updatedRole = role.trim() || agent.role

    const updatedAgent: AgentOfficeMember = {
      ...agent,
      name: updatedName,
      role: updatedRole,
      personality: personality.trim() || agent.personality,
      workspace: workspace.trim() || agent.workspace,
      color,
      shirtColor: color,
      deskPct: { x: deskX, y: deskY },
      engine,
      model,
      safetyTier: riskTier,
      tools: allowedTools.length > 0 ? allowedTools : agent.tools,
      allowed_skills: allowedSkills,
      specialty: `${engine}, ${allowedSkills.join(', ')}`,
      logs: [
        ...agent.logs,
        `[${new Date().toLocaleTimeString()}] Config saved: Engine=${engine}, Model=${model}, Skills=[${allowedSkills.join(', ')}]`,
      ],
    }

    const payload: AgentProfile = {
      id: agent.id,
      name: updatedName,
      role: updatedRole,
      specialty: `${engine}, ${allowedSkills.join(', ')}`,
      color,
      default_tool: engine,
      risk_tier: riskTier,
      model_id: model,
      worktree: workspace,
      desk_x: deskX,
      desk_y: deskY,
      allowed_tools: allowedTools.length > 0 ? allowedTools : agent.tools,
      allowed_skills: allowedSkills,
      prompt_prefix: personality.trim() || agent.personality,
    }

    try {
      // Persist to backend POST /api/fleet/agents
      await api.saveAgent(payload)
      if (onSave) {
        onSave(updatedAgent)
      }
      onClose()
    } catch (err) {
      console.error('Failed to persist agent configuration:', err)
      // Call onSave optimistically so UI updates even if backend is temporarily disconnected
      if (onSave) {
        onSave(updatedAgent)
      }
      onClose()
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 animate-in fade-in duration-150">
      <Frame className="w-full max-w-xl border-[var(--border)] max-h-[90vh] flex flex-col">
        <FramePanel className="bg-[var(--card)] border-[var(--border)] p-0 overflow-hidden flex flex-col max-h-[90vh]">
          {/* Header */}
          <FrameHeader className="p-3 border-b border-[var(--border)] flex flex-row items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[var(--primary)]" />
              <FrameTitle className="text-sm font-semibold text-[var(--foreground)]">
                Agent Configuration: {agent.name}
              </FrameTitle>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-6 w-6 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              <X className="w-4 h-4" />
            </Button>
          </FrameHeader>

          {/* Scrollable Form Content */}
          <ScrollArea className="flex-1 p-4 overflow-y-auto">
            <div className="space-y-4 pr-1">
              {/* 1. IDENTITY, AVATAR & COLOR */}
              <div className="space-y-2">
                <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase flex items-center gap-1.5">
                  <Palette className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                  <span>Agent Identity, Avatar & Color</span>
                </label>
                <div className="flex items-center gap-3 p-3 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)]/30 border border-[var(--border)]">
                  {/* Avatar Preview */}
                  <div
                    className="w-14 h-14 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] overflow-hidden flex items-center justify-center border shrink-0 p-1"
                    style={{ borderColor: color, backgroundColor: `${color}15` }}
                  >
                    <Blobatar name={name || agent.name} size={48} animate="always" className="w-full h-full object-contain" />
                  </div>

                  <div className="flex-1 space-y-2 min-w-0">
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Agent Name..."
                      className="w-full h-8 px-2.5 text-xs rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                    />

                    {/* Presets and Color Palette */}
                    <div className="flex items-center justify-between gap-2">
                      {/* Avatar Name Presets */}
                      <div className="flex items-center gap-1 overflow-x-auto py-0.5 scrollbar-thin">
                        {AVATAR_PRESETS.map((preset) => {
                          const isPicked = name === preset
                          return (
                            <button
                              key={preset}
                              type="button"
                              onClick={() => setName(preset)}
                              className={`w-7 h-7 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] flex items-center justify-center shrink-0 border transition-all ${
                                isPicked
                                  ? 'border-[var(--primary)] ring-2 ring-[var(--primary)]/30 bg-[var(--primary)]/10 scale-105'
                                  : 'border-[var(--border)] bg-[var(--card)] hover:border-[var(--muted-foreground)] opacity-75 hover:opacity-100'
                              }`}
                              title={preset}
                            >
                              <Blobatar name={preset} size={20} animate="hover" className="w-full h-full object-contain" />
                            </button>
                          )
                        })}
                      </div>

                      {/* Color Presets */}
                      <div className="flex items-center gap-1 shrink-0">
                        {COLOR_PRESETS.slice(0, 6).map((c) => (
                          <button
                            key={c}
                            type="button"
                            onClick={() => setColor(c)}
                            className={`w-5 h-5 rounded-full border transition-transform ${
                              color === c ? 'scale-125 ring-2 ring-white/50 border-white' : 'border-black/30 hover:scale-110'
                            }`}
                            style={{ backgroundColor: c }}
                            title={c}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 2. DESK COORDINATES & POSITION */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                    <span>Desk Coordinates & Workstation</span>
                  </label>
                  <span className="text-[10px] font-mono text-[var(--muted-foreground)]">
                    Pos: ({deskX.toFixed(1)}%, {deskY.toFixed(1)}%)
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono text-[var(--muted-foreground)]">Desk X (%)</span>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="100"
                      value={deskX}
                      onChange={(e) => setDeskX(parseFloat(e.target.value) || 0)}
                      className="w-full h-8 px-2.5 text-xs font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                    />
                  </div>

                  <div className="space-y-1">
                    <span className="text-[10px] font-mono text-[var(--muted-foreground)]">Desk Y (%)</span>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="100"
                      value={deskY}
                      onChange={(e) => setDeskY(parseFloat(e.target.value) || 0)}
                      className="w-full h-8 px-2.5 text-xs font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                    />
                  </div>

                  <div className="space-y-1">
                    <span className="text-[10px] font-mono text-[var(--muted-foreground)]">Snap to Desk Slot</span>
                    <Select onValueChange={handleSelectWorkstation}>
                      <SelectTrigger className="h-8 text-xs font-mono">
                        <SelectValue placeholder="Preset Slot" />
                      </SelectTrigger>
                      <SelectContent>
                        {WORKSTATION_SLOTS.map((slot) => (
                          <SelectItem key={slot.id} value={slot.id} className="text-xs font-mono">
                            {slot.defaultAgentId || slot.id} ({slot.x}%, {slot.y}%)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* 3. ROLE & TITLE */}
              <div className="space-y-1">
                <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Role / Title</label>
                <input
                  type="text"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="e.g. Lead Software Architect, Tech Lead..."
                  className="w-full h-8 px-2.5 text-xs rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                />
              </div>

              {/* 4. INSTRUCTIONS / PERSONALITY */}
              <div className="space-y-1">
                <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Instructions / Personality</label>
                <textarea
                  rows={2}
                  value={personality}
                  onChange={(e) => setPersonality(e.target.value)}
                  placeholder="Agent behavior rules and guidelines..."
                  className="w-full p-2 text-xs font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)] resize-none"
                />
              </div>

              {/* 5. WORKSPACE FOLDER */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase flex items-center gap-1.5">
                    <FolderOpen className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                    <span>Workspace Folder</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setWorkspace('c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57')}
                    className="text-[10px] font-mono text-[var(--muted-foreground)] hover:underline opacity-80 hover:opacity-100"
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
                        setWorkspace(folderPath)
                      }
                    }}
                  />
                  <div className="relative flex-1 min-w-0">
                    <input
                      type="text"
                      value={workspace}
                      onChange={(e) => setWorkspace(e.target.value)}
                      placeholder="c:/path/to/workspace..."
                      className="w-full h-8 pl-8 pr-2.5 text-xs font-mono rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--input)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                    />
                    <Folder className="w-3.5 h-3.5 text-[var(--muted-foreground)] absolute left-2.5 top-2.5" />
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => folderInputRef.current?.click()}
                    className="h-8 text-xs font-mono px-3 gap-1.5 shrink-0 bg-[var(--input)]/40 hover:bg-[var(--muted)] border-[var(--border)] text-[var(--foreground)]"
                  >
                    <FolderOpen className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                    <span>Browse</span>
                  </Button>
                </div>
              </div>

              {/* 6. ENGINE, MODEL & RISK TIER */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <div className="space-y-1">
                  <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase">Engine</label>
                  <Select
                    value={engine}
                    onValueChange={(val) => {
                      setEngine(val)
                      const available = ENGINE_MODELS_MAP[val]
                      if (available && available.length > 0) {
                        setModel(available[0].id)
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
                  <Select value={model} onValueChange={setModel}>
                    <SelectTrigger className="h-8 text-xs font-mono">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(ENGINE_MODELS_MAP[engine] || ENGINE_MODELS_MAP['opencode_run']).map((m) => (
                        <SelectItem key={m.id} value={m.id}>
                          {m.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-mono text-[var(--muted-foreground)] uppercase flex items-center gap-1">
                    <Shield className="w-3 h-3 text-[var(--muted-foreground)]" />
                    <span>Risk Tier</span>
                  </label>
                  <Select value={riskTier} onValueChange={setRiskTier}>
                    <SelectTrigger className="h-8 text-xs font-mono">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="L0_READ_ONLY">Read-Only (L0)</SelectItem>
                      <SelectItem value="L1_MUTATION">Standard Edit (L1)</SelectItem>
                      <SelectItem value="L2_DESTRUCTIVE">Destructive / Shell (L2)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* 7. ENGINE & TOOLS / ALLOWED SKILLS SECTION */}
              <div className="space-y-2 pt-1 border-t border-[var(--border)]">
                <Tabs defaultValue="skills" className="w-full">
                  <div className="flex items-center justify-between pb-1.5">
                    <TabsList className="h-7.5 p-0.5 bg-[var(--input)]/80 border border-[var(--border)]">
                      <TabsTrigger value="skills" className="text-xs h-6.5 px-3 gap-1.5 font-mono">
                        <Sparkles className="w-3 h-3 text-[var(--primary)]" />
                        <span>Allowed Skills ({allowedSkills.length})</span>
                      </TabsTrigger>
                      <TabsTrigger value="tools" className="text-xs h-6.5 px-3 gap-1.5 font-mono">
                        <Wrench className="w-3 h-3 text-[var(--muted-foreground)]" />
                        <span>Tools ({allowedTools.length})</span>
                      </TabsTrigger>
                    </TabsList>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => {
                          if (allowedSkills.length === skillsList.length) {
                            setAllowedSkills([])
                          } else {
                            setAllowedSkills(skillsList.map((s) => s.id))
                          }
                        }}
                        className="text-[10px] font-mono text-[var(--muted-foreground)] hover:text-[var(--foreground)] px-2 py-0.5 rounded border border-[var(--border)] bg-[var(--input)]/30 hover:bg-[var(--muted)]"
                      >
                        {allowedSkills.length === skillsList.length ? 'Clear Skills' : 'All Skills'}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (allowedTools.length === AVAILABLE_TOOLS.length) {
                            setAllowedTools([])
                          } else {
                            setAllowedTools(AVAILABLE_TOOLS.map((t) => t.id))
                          }
                        }}
                        className="text-[10px] font-mono text-[var(--muted-foreground)] hover:text-[var(--foreground)] px-2 py-0.5 rounded border border-[var(--border)] bg-[var(--input)]/30 hover:bg-[var(--muted)]"
                      >
                        {allowedTools.length === AVAILABLE_TOOLS.length ? 'Clear Tools' : 'All Tools'}
                      </button>
                    </div>
                  </div>

                  {/* SKILLS TAB: Clean ReUI Badge Multi-Select Checklist */}
                  <TabsContent value="skills" className="mt-1 space-y-2">
                    <div className="grid grid-cols-1 gap-1.5 max-h-48 overflow-y-auto pr-1">
                      {skillsList.map((skill) => {
                        const isSelected = allowedSkills.includes(skill.id)
                        return (
                          <div
                            key={skill.id}
                            onClick={() => toggleSkill(skill.id)}
                            className={`flex items-start justify-between p-2 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] border text-left cursor-pointer transition-all ${
                              isSelected
                                ? 'bg-[var(--primary)]/10 border-[var(--primary)]/60 text-[var(--foreground)] ring-1 ring-[var(--primary)]/20'
                                : 'bg-[var(--input)]/25 border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--input)]/45'
                            }`}
                          >
                            <div className="flex flex-col min-w-0 pr-2">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-mono font-semibold text-[var(--foreground)]">
                                  {skill.name}
                                </span>
                              </div>
                              <span className="text-[10px] text-[var(--muted-foreground)] line-clamp-1 mt-0.5">
                                {skill.desc}
                              </span>
                            </div>

                            {/* ReUI Badge Check Indicator */}
                            <Badge
                              variant={isSelected ? 'default' : 'outline'}
                              size="xs"
                              className={`shrink-0 transition-all font-mono ${
                                isSelected
                                  ? 'bg-[var(--primary)] text-white border-[var(--primary)] font-bold'
                                  : 'opacity-60 text-[var(--muted-foreground)] hover:opacity-100'
                              }`}
                            >
                              {isSelected ? (
                                <span className="flex items-center gap-1">
                                  <Check className="w-2.5 h-2.5" />
                                  <span>ALLOWED</span>
                                </span>
                              ) : (
                                <span>+ ADD</span>
                              )}
                            </Badge>
                          </div>
                        )
                      })}
                    </div>
                  </TabsContent>

                  {/* TOOLS TAB */}
                  <TabsContent value="tools" className="mt-1">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-48 overflow-y-auto pr-1">
                      {AVAILABLE_TOOLS.map((tool) => {
                        const isSelected = allowedTools.includes(tool.id)
                        return (
                          <div
                            key={tool.id}
                            onClick={() => toggleTool(tool.id)}
                            className={`flex flex-col items-start p-2 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] border text-left cursor-pointer transition-all ${
                              isSelected
                                ? 'bg-cyan-500/15 border-cyan-500 text-[var(--foreground)] ring-1 ring-cyan-500/30'
                                : 'bg-[var(--input)]/30 border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--input)]/50'
                            }`}
                          >
                            <div className="flex items-center justify-between w-full gap-1">
                              <span className="text-xs font-mono font-semibold text-[var(--foreground)] truncate">
                                {tool.name}
                              </span>
                              <Badge
                                variant={isSelected ? 'success' : 'outline'}
                                size="xs"
                                className="shrink-0 text-[8px]"
                              >
                                {isSelected ? 'ACTIVE' : '+ ADD'}
                              </Badge>
                            </div>
                            <span className="text-[10px] text-[var(--muted-foreground)] line-clamp-1 mt-0.5">
                              {tool.desc}
                            </span>
                          </div>
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
              onClick={onClose}
              disabled={isSaving}
              className="h-7 text-xs px-3"
            >
              Cancel
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleSave}
              disabled={isSaving}
              className="h-7 text-xs px-3 gap-1"
            >
              {isSaving ? (
                <span>Saving...</span>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Changes</span>
                </>
              )}
            </Button>
          </div>
        </FramePanel>
      </Frame>
    </div>
  )
}
