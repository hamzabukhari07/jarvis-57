import sys
from pathlib import Path

file_path = Path("web/src/components/office/AutonomousOfficeScreen.tsx")
text = file_path.read_text(encoding="utf-8")

# 1. Imports
text = text.replace(
    "import React, { useState, useRef } from 'react'",
    "import React, { useState, useRef, useEffect, useCallback } from 'react'"
)
text = text.replace(
    "  Database,\n} from 'lucide-react'",
    "  Database,\n  Volume2,\n  VolumeX,\n} from 'lucide-react'"
)
text = text.replace(
    "import { cn } from '@/lib/utils'",
    "import { cn } from '@/lib/utils'\nimport { api } from '../../lib/api'\nimport type { AgentProfile } from '../../types/zezo'"
)

# 2. INITIAL_AGENTS replacement
start_marker = "const INITIAL_AGENTS: AgentOfficeMember[] = ["
end_marker = "]\n// Web Audio Foley Synthesizer (Retro Micro-Foley)"

idx_start = text.find(start_marker)
idx_end = text.find(end_marker)

if idx_start == -1 or idx_end == -1:
    print("Failed to find INITIAL_AGENTS markers", idx_start, idx_end)
    sys.exit(1)

workstation_code = '''export const WORKSTATION_SLOTS = [
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
    engine: raw.default_tool || 'opencode_run',
    model: raw.model_id || 'gemini-2.5-flash',
    workspace: raw.active_worktree || raw.worktree || 'repo_active',
    safetyTier: raw.risk_tier || 'L1_MUTATION',
    specialty: raw.specialty || `${raw.default_tool || 'opencode_run'}, ${role}`,
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
]'''

text = text[:idx_start] + workstation_code + text[idx_end + len("]"):]

# 3. Default selectedAgentId
text = text.replace(
    "  const [selectedAgentId, setSelectedAgentId] = useState<string>('agent-2')",
    "  const [selectedAgentId, setSelectedAgentId] = useState<string>('MICHAEL')"
)

# 4. Add loadFleet, useEffect, and delete agent
hook_insert = '''  const loadFleet = useCallback(async () => {
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

  const handleDeleteAgent = async (agentId: string) => {
    const ag = agents.find((a) => a.id === agentId)
    if (!window.confirm(`Are you sure you want to dismiss agent ${ag?.name || agentId} from the fleet?`)) return
    try {
      await api.deleteAgent(agentId)
      triggerToast(`Agent ${ag?.name || agentId} dismissed from fleet`)
      const remaining = agents.filter((a) => a.id !== agentId)
      if (remaining.length > 0) setSelectedAgentId(remaining[0].id)
      loadFleet()
    } catch (err) {
      console.error('Failed to delete agent:', err)
    }
  }
'''

target_state_hook = "  const [isEnvDrawerOpen, setIsEnvDrawerOpen] = useState(true)"
text = text.replace(target_state_hook, hook_insert + target_state_hook)

# 5. Wire handleCreateNewAgent to api.saveAgent
old_create_func = '''    setAgents((prev) => [...prev, newAgent])
    setSelectedAgentId(newId)
    setIsAddAgentOpen(false)
    setNewAgentName('')
    setNewAgentRole('')
    setNewAgentInstructions('')
  }'''

new_create_func = '''    setAgents((prev) => [...prev, newAgent])
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
  }'''

text = text.replace(old_create_func, new_create_func)

# 6. Wire handleSaveEditAgent to api.saveAgent
old_edit_save = '''    setIsEditAgentOpen(false)
    playOfficeFoley('success', soundEnabled)
    triggerToast(`Agent ${updatedName} configuration updated!`)
  }'''

new_edit_save = '''    setIsEditAgentOpen(false)
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
  }'''

text = text.replace(old_edit_save, new_edit_save)

# 7. Update Top Bar simulation buttons and sound icon
old_top_bar = '''              {/* Simulation Action Triggers & View Mode Controls */}
              <div className="flex items-center gap-1 shrink-0">
                {officeMode === 'spatial' && (
                  <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRunSprintSimulation}
                  disabled={isSimulating}
                  className="h-6 text-[10px] px-2 gap-1 font-mono bg-orange-500/10 border-orange-500/30 text-orange-400 hover:bg-orange-500/20"
                  title="Run Full Autonomous Sprint Simulation"
                >
                  <Zap className="w-3 h-3 text-orange-400" />
                  <span className="hidden lg:inline">Sprint Sim</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleAllHandsMeeting}
                  disabled={isSimulating}
                  className="h-6 text-[10px] px-2 gap-1 font-mono bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20"
                  title="Call All-Hands Boardroom Meeting"
                >
                  <AlertCircle className="w-3 h-3 text-red-400" />
                  <span className="hidden lg:inline">Boardroom</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCoffeeBreak}
                  className="h-6 text-[10px] px-2 gap-1 font-mono bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/20"
                  title="Send Selected Agent to Coffee Break"
                >
                  <Sparkles className="w-3 h-3 text-amber-400" />
                  <span className="hidden xl:inline">Coffee</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePairReview}
                  className="h-6 text-[10px] px-2 gap-1 font-mono bg-cyan-500/10 border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20"
                  title="Pair Programming Review"
                >
                  <GitBranch className="w-3 h-3 text-cyan-400" />
                  <span className="hidden xl:inline">Pair</span>
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSoundEnabled(!soundEnabled)
                    playOfficeFoley('click', !soundEnabled)
                  }}
                  className="h-6 text-[10px] px-1.5 font-mono text-[var(--muted-foreground)]"
                  title={soundEnabled ? 'Audio Foley: ON' : 'Audio Foley: MUTED'}
                >
                  {soundEnabled ? '🔊' : '🔇'}
                </Button>

                <div className="h-4 w-px bg-[var(--border)] mx-1" />
              </>
            )}'''

new_top_bar = '''              {/* Audio Foley & View Mode Controls */}
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
                )}'''

text = text.replace(old_top_bar, new_top_bar)

# 8. Desks Canvas Loop
old_desks_start = '''                  {/* 7. ALL 18 STATIC WORKSTATION DESKS */}
                  {[
                    { id: 'desk-michael', x: 4.1, y: 22.8, label: 'MICHAEL' },
                    { id: 'desk-jim', x: 56.7, y: 27.5, label: 'JIM' },
                    { id: 'desk-dwight', x: 65.8, y: 27.5, label: 'DWIGHT' },
                    { id: 'desk-annex-1', x: 79.1, y: 16.0, label: 'OPEN' },
                    { id: 'desk-annex-2', x: 88.2, y: 16.0, label: 'OPEN' },
                    { id: 'desk-oscar', x: 2.1, y: 52.5, label: 'OSCAR' },
                    { id: 'desk-r1-2', x: 14.2, y: 52.5, label: 'STANLEY' },
                    { id: 'desk-r1-3', x: 26.3, y: 52.5, label: 'OPEN' },
                    { id: 'desk-ryan', x: 38.5, y: 52.5, label: 'RYAN' },
                    { id: 'desk-pam', x: 50.6, y: 52.5, label: 'PAM' },
                    { id: 'desk-kevin', x: 62.7, y: 52.5, label: 'KEVIN' },
                    { id: 'desk-angela', x: 2.1, y: 79.2, label: 'ANGELA' },
                    { id: 'desk-r2-2', x: 14.2, y: 79.2, label: 'OPEN' },
                    { id: 'desk-kelly', x: 26.3, y: 79.2, label: 'KELLY' },
                    { id: 'desk-r2-4', x: 38.5, y: 79.2, label: 'OPEN' },
                    { id: 'desk-r2-5', x: 50.6, y: 79.2, label: 'OPEN' },
                    { id: 'desk-r2-6', x: 62.7, y: 79.2, label: 'OPEN' },
                    { id: 'desk-r2-7', x: 74.8, y: 79.2, label: 'OPEN' },
                  ].map((desk) => {
                    const seatedAgent = agents.find(
                      (a) =>
                        Math.abs(a.currentPct.x - (desk.x + 1.4)) < 3 &&
                        Math.abs(a.currentPct.y - (desk.y + 2.7)) < 3
                    )'''

new_desks_start = '''                  {/* 7. ALL 18 WORKSTATION DESKS */}
                  {WORKSTATION_SLOTS.map((desk) => {
                    const seatedAgent = agents.find(
                      (a) =>
                        Math.abs(a.currentPct.x - (desk.x + 3.9)) < 4 &&
                        Math.abs(a.currentPct.y - (desk.y + 8.8)) < 4
                    )'''

text = text.replace(old_desks_start, new_desks_start)

# 9. Add DISMISS button next to [CHAT] [EDIT] [FILES]
old_action_btns = '''                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleOpenFilesModal}
                      className="flex-1 h-7 min-w-0 px-1 text-[10px] font-semibold tracking-wider font-mono gap-1 text-cyan-400 hover:text-cyan-300 border-cyan-500/30 hover:bg-cyan-500/10"
                      title="Manage Agent Context Files & SOUL.md"
                    >
                      <Folder className="w-3 h-3 text-cyan-400 shrink-0" />
                      <span className="truncate">FILES</span>
                    </Button>
                  </div>'''

new_action_btns = '''                    <Button
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
                      onClick={() => handleDeleteAgent(selectedAgent.id)}
                      className="h-7 px-2 text-[10px] font-semibold tracking-wider font-mono gap-1 text-red-400 hover:text-red-300 border-red-500/30 hover:bg-red-500/10 shrink-0"
                      title="Dismiss Agent from Fleet"
                    >
                      <Trash2 className="w-3 h-3 text-red-400 shrink-0" />
                      <span className="hidden sm:inline">DISMISS</span>
                    </Button>
                  </div>'''

text = text.replace(old_action_btns, new_action_btns)

file_path.write_text(text, encoding="utf-8")
print("AutonomousOfficeScreen.tsx successfully updated!")

