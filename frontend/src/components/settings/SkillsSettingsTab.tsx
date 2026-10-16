import React, { useState, useMemo, useEffect } from 'react'
import { api } from '../../lib/api'
import { Card } from '../reui/card'
import { Badge } from '../reui/badge'
import { Callout } from '../reui/callout'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Switch } from '../ui/switch'
import { ScrollArea } from '../ui/scroll-area'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/tabs'
import {
  Search,
  Code2,
  Globe,
  Cpu,
  Palette,
  Workflow,
  RotateCcw,
  Check,
  Bot,
  Eye,
  Edit3,
  Save,
  FileCode,
  X,
  ChevronRight,
} from 'lucide-react'

export interface SkillItem {
  id: string
  name: string
  type: 'skill' | 'action' | 'plugin'
  category: 'coding' | 'design' | 'research' | 'system' | 'media' | 'orchestration'
  version: string
  author: string
  description: string
  enabled: boolean
  tags: string[]
  markdownDoc: string
}

const DEFAULT_SKILLS: SkillItem[] = [
  {
    id: 'hamza_taste',
    name: 'Hamza Taste (Studio UI)',
    type: 'skill',
    category: 'design',
    version: '2.5.0',
    author: 'Hamza Bukhari',
    description: 'Master Studio UI Anti-Slop Directive & Reference-First Design Protocol for autonomous web generation and frontend agents.',
    enabled: true,
    tags: ['Design System', 'Anti-Slop', 'Tailwind', 'ReUI'],
    markdownDoc: `# 🎨 Hamza Taste — Studio UI Anti-Slop Directive

> **Lead Architect & Creator:** Hamza Bukhari  
> **Target Audience:** Google Antigravity Agent, OpenCode, Kilo Code, and all Autonomous Coding Agents  
> **Core Principle:** Anti-Slop is a **FILTER** (what to reject), while **Reference HTML Templates** supply 100% of the **DIRECTION**.

---

### 💎 Core Architectural Contract
1. **Reference-First Design:** Coding agents MUST adopt exact colors, typography, radii, glassmorphic elevation, and card geometry extracted from reference templates.
2. **Zero Hallucinated Slop:** No cliché purple-indigo blobs, no unstyled native controls, and no fake telemetry copy.
3. **4px/8px Modular Rhythm:** All padding, margins, and gaps adhere to strict 4px/8px increments.`
  },
  {
    id: 'opencode',
    name: 'OpenCode Autonomous Coding',
    type: 'skill',
    category: 'coding',
    version: '3.1.2',
    author: 'ZEZO Core',
    description: 'Deep multi-file autonomous programming workflow. Reads codebase graph, writes clean diffs, and self-verifies 3 layers.',
    enabled: true,
    tags: ['Autonomous', 'Multi-File', 'Code Graph', 'KùzuDB'],
    markdownDoc: `# ⚡ OpenCode Coding Workflow

Autonomous multi-file code authoring engine powered by AST graph analysis.

- Queries KùzuDB CGC graph before editing callers/callees.
- Dispatches changes asynchronously with thread-safe task IDs.
- Runs mandatory 3-Layer verification before reporting completion.`
  },
  {
    id: 'kilo_code',
    name: 'Kilo Code Fast Refactor',
    type: 'skill',
    category: 'coding',
    version: '1.9.0',
    author: 'ZEZO Core',
    description: 'High-speed inline refactoring, snippet authoring, and file chunk transformations with low token overhead.',
    enabled: true,
    tags: ['Fast Refactor', 'Chunk Edits', 'Low Latency', 'Free Tier'],
    markdownDoc: `# 🚀 Kilo Code Refactoring Engine

Specialized for fast single-file and multi-chunk code mutations without blocking live agent loops.`
  },
  {
    id: 'antigravity_agent',
    name: 'Antigravity Studio Synthesis',
    type: 'skill',
    category: 'coding',
    version: '2.4.0',
    author: 'Hamza Bukhari',
    description: 'Direct integration with Google Antigravity Studio agent for end-to-end full-stack web and desktop software synthesis.',
    enabled: true,
    tags: ['Google Antigravity', 'Full Stack', 'Vite', 'React', 'PyQt6'],
    markdownDoc: `# 🌌 Antigravity Synthesis Engine

Coordinates full-stack generation, scaffolding, preview servers, and automated browser verification.`
  },
  {
    id: 'git_workflow',
    name: 'Git Workflow & Staging',
    type: 'skill',
    category: 'coding',
    version: '1.4.0',
    author: 'ZEZO Core',
    description: 'Automated atomic Git commit authoring, semantic branch management, stash management, and PR summaries.',
    enabled: true,
    tags: ['Git', 'Atomic Commits', 'Semantic Versioning', 'Staging'],
    markdownDoc: `# 🌿 Git Workflow Protocol

Standardizes staging, branch safety gates, and conventional commit messaging (feat, fix, refactor, docs).`
  },
  {
    id: 'web_research_pipeline',
    name: 'Deep Web Research Pipeline',
    type: 'skill',
    category: 'research',
    version: '2.2.0',
    author: 'Hamza Bukhari',
    description: 'Autonomous query decomposition, recursive DuckDuckGo & Google searching, anti-bot web scraping, and factual synthesis.',
    enabled: true,
    tags: ['Deep Research', 'Query Decomposition', 'Anti-Bot'],
    markdownDoc: `# 🔍 Deep Web Research Pipeline

Decomposes complex questions into multi-hop sub-queries, executes parallel searches, and strips boilerplate ads to output clean markdown reports.`
  },
  {
    id: 'social_research',
    name: 'Social & Video Research Engine',
    type: 'skill',
    category: 'research',
    version: '1.8.0',
    author: 'ZEZO Core',
    description: 'Scrapes YouTube transcripts, GitHub release notes, and Reddit discussions for community insights and market telemetry.',
    enabled: true,
    tags: ['YouTube Transcripts', 'Reddit Scraper', 'Whisper'],
    markdownDoc: `# 📺 Social Intelligence Engine

Extracts audio transcripts via Whisper, indexes discussion threads, and monitors ecosystem discussions.`
  },
  {
    id: 'web_scraper',
    name: 'Anti-Bot Stealth Scraper',
    type: 'skill',
    category: 'research',
    version: '2.0.1',
    author: 'ZEZO Core',
    description: 'Cloudflare-resilient web scraper extracting structured clean DOM, meta tags, and high-fidelity markdown without blocks.',
    enabled: true,
    tags: ['Anti-Bot', 'Puppeteer', 'DOM Parser'],
    markdownDoc: `# 🛡️ Anti-Bot Scraper

Headless automation with user-agent rotation and clean readability extraction.`
  },
  {
    id: 'multi_agent_collaboration',
    name: 'Multi-Agent Fleet Orchestrator',
    type: 'skill',
    category: 'orchestration',
    version: '3.0.0',
    author: 'Hamza Bukhari',
    description: 'Dynamic dispatch of named specialized subagents (Architect, Coder, Researcher, Verifier) with shared memory bus.',
    enabled: true,
    tags: ['Agent Fleet', 'Parallel Execution', 'Memory Bus'],
    markdownDoc: `# 👥 Multi-Agent Fleet Orchestrator

Manages sub-agent lifecycles, assigns discrete task matrices, and consolidates findings into the shared SQLite FTS5 memory bus.`
  },
  {
    id: 'system_diagnostics',
    name: 'Hardware Telemetry Diagnostics',
    type: 'skill',
    category: 'system',
    version: '1.5.0',
    author: 'ZEZO Core',
    description: 'Real-time CPU thermal analysis, RAM leak detection, GPU VRAM profiling, and process surveillance.',
    enabled: true,
    tags: ['Hardware', 'CPU/GPU', 'VRAM', 'Thermology'],
    markdownDoc: `# 🖥️ System Diagnostics Routine

Telemetry polling engine monitoring hardware health, orphaned background daemons, and endpoint audio devices.`
  },
  {
    id: 'test_fastapi_deploy',
    name: 'FastAPI Backend Smoke Test',
    type: 'skill',
    category: 'system',
    version: '1.2.0',
    author: 'ZEZO Core',
    description: 'Automated health verification of local and remote FastAPI microservices, WebSocket endpoints, and latency.',
    enabled: true,
    tags: ['FastAPI', 'Uvicorn', 'WebSocket Health'],
    markdownDoc: `# 🚀 FastAPI Deploy Test

Smoke-tests REST endpoints, checks WebSocket handshake latency, and inspects route registry.`
  },
  {
    id: 'figma_helper',
    name: 'Figma Token Converter',
    type: 'skill',
    category: 'design',
    version: '1.1.0',
    author: 'ZEZO Core',
    description: 'Converts Figma nodes, auto-layouts, and CSS color variables into production ReUI and Tailwind CSS classes.',
    enabled: true,
    tags: ['Figma', 'Design Tokens', 'Tailwind', 'ReUI'],
    markdownDoc: `# 📐 Figma Helper

Extracts hex palettes, converts to CSS custom properties, and generates standard component primitives.`
  },
  {
    id: 'parallel_task_management',
    name: 'Parallel Task Manager',
    type: 'skill',
    category: 'orchestration',
    version: '2.1.0',
    author: 'ZEZO Core',
    description: 'Thread-safe background process scheduler, priority queue manager, and task cancellation governor.',
    enabled: true,
    tags: ['Background Tasks', 'Thread-Safe', 'Priority Queue'],
    markdownDoc: `# ⏱️ Parallel Task Scheduler

Dispatches non-blocking async tasks with structured logs, progress percentage trackers, and timeout guards.`
  },
  {
    id: 'make_plan',
    name: 'Architecture Roadmap Planner',
    type: 'skill',
    category: 'coding',
    version: '1.3.0',
    author: 'Hamza Bukhari',
    description: 'Decomposes complex features into step-by-step technical roadmaps, dependency matrices, and safety checklists.',
    enabled: true,
    tags: ['Architecture', 'Technical Roadmap', 'ADR'],
    markdownDoc: `# 📋 Architecture Planning Engine

Generates structured implementation roadmaps in \`planning/\` adhering to clean-room boundaries and verification standards.`
  },
  {
    id: 'office_suite',
    name: 'Office Suite Workflow',
    type: 'skill',
    category: 'media',
    version: '1.0.0',
    author: 'ZEZO Core',
    description: 'Automated formatting, PDF generation, CSV tabular parsing, and office document conversions.',
    enabled: true,
    tags: ['PDF', 'CSV', 'Spreadsheet', 'Docs'],
    markdownDoc: `# 📄 Office Suite Processor

Parses office documents, extracts tabular data, and exports formatted markdown summaries.`
  }
]

export const SkillsSettingsTab: React.FC = () => {
  const [skills, setSkills] = useState<SkillItem[]>(() => {
    const saved = localStorage.getItem('zezo_skills_state')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed.filter((s: SkillItem) => s.id !== 'custom_skill_10')
        }
      } catch {}
    }
    return DEFAULT_SKILLS.filter((s: SkillItem) => s.id !== 'custom_skill_10')
  })

  // Load real skills dynamically from backend /api/skills
  useEffect(() => {
    const loadRealSkills = async () => {
      try {
        const res = await api.getSkills()
        if (res && res.skills && Array.isArray(res.skills) && res.skills.length > 0) {
          const serverSkills: SkillItem[] = res.skills
            .filter((s: any) => s.name !== 'custom_skill_10')
            .map((s: any) => ({
              id: s.name,
              name: s.display_name || s.name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
              type: 'skill' as const,
              category: (s.domain || 'coding') as any,
              version: s.version || '1.0.0',
              author: s.author || (['hamza_taste', 'antigravity_agent', 'make_plan', 'web_research_pipeline', 'multi_agent_collaboration'].includes(s.name) ? 'Hamza Bukhari' : 'ZEZO Core'),
              description: s.description || '',
              enabled: !s.disabled,
              tags: s.tags || [s.domain || 'System'],
              markdownDoc: s.instructions || `# ${s.name}\n\n${s.description || ''}`,
            }))
          setSkills(serverSkills)
          localStorage.setItem('zezo_skills_state', JSON.stringify(serverSkills))
        }
      } catch (e) {
        console.debug('Using cached skills:', e)
      }
    }
    loadRealSkills()
  }, [])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  // Selected Skill for Slide-Over Drawer
  const [activeDrawerSkill, setActiveDrawerSkill] = useState<SkillItem | null>(null)
  const [activeDrawerTab, setActiveDrawerTab] = useState<string>('preview')
  const [drawerEditedContent, setDrawerEditedContent] = useState('')
  const [isSavingDrawer, setIsSavingDrawer] = useState(false)
  const [drawerSaveSuccess, setDrawerSaveSuccess] = useState(false)

  // Save changes to localStorage
  const persistSkills = (updatedSkills: SkillItem[]) => {
    setSkills(updatedSkills)
    localStorage.setItem('zezo_skills_state', JSON.stringify(updatedSkills))
  }

  // Toggle single skill and synchronize with backend disk registry
  const handleToggleSkill = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    const target = skills.find((s) => s.id === id)
    const nextEnabled = target ? !target.enabled : true
    const updated = skills.map((s) => (s.id === id ? { ...s, enabled: nextEnabled } : s))
    persistSkills(updated)
    if (activeDrawerSkill?.id === id) {
      setActiveDrawerSkill((prev) => (prev ? { ...prev, enabled: nextEnabled } : null))
    }
    try {
      await api.updateSkillMode(id, { disabled: !nextEnabled, auto_activate: nextEnabled })
    } catch (err) {
      console.warn('Backend skill mode toggle error:', err)
    }
  }

  // Filter skills
  const filteredSkills = useMemo(() => {
    return skills.filter((item) => {
      const matchSearch =
        !searchQuery.trim() ||
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))

      const matchCategory =
        selectedCategory === 'all' || item.category === selectedCategory

      return matchSearch && matchCategory
    })
  }, [skills, searchQuery, selectedCategory])

  // Open Drawer
  const openDrawer = (skill: SkillItem) => {
    setActiveDrawerSkill(skill)
    setDrawerEditedContent(skill.markdownDoc)
    setActiveDrawerTab('preview')
    setDrawerSaveSuccess(false)
  }

  // Close Drawer
  const closeDrawer = () => {
    setActiveDrawerSkill(null)
  }

  // Save Drawer Content and persist to backend disk
  const handleSaveDrawerDoc = async () => {
    if (!activeDrawerSkill) return
    setIsSavingDrawer(true)
    const updated = skills.map((s) =>
      s.id === activeDrawerSkill.id ? { ...s, markdownDoc: drawerEditedContent } : s
    )
    persistSkills(updated)
    setActiveDrawerSkill((prev) => (prev ? { ...prev, markdownDoc: drawerEditedContent } : null))

    try {
      await api.saveSkill({
        name: activeDrawerSkill.id,
        description: activeDrawerSkill.description,
        instructions: drawerEditedContent,
        domain: activeDrawerSkill.category,
      })
    } catch (err) {
      console.warn('Backend skill save error:', err)
    }

    setIsSavingDrawer(false)
    setDrawerSaveSuccess(true)
    setTimeout(() => setDrawerSaveSuccess(false), 2000)
  }

  const getCategoryDetails = (category: string) => {
    switch (category) {
      case 'design':
        return {
          icon: Palette,
          color: '#f59e0b',
          badgeVariant: 'warning' as const,
        }
      case 'coding':
        return {
          icon: Code2,
          color: '#3b82f6',
          badgeVariant: 'default' as const,
        }
      case 'research':
        return {
          icon: Globe,
          color: '#10b981',
          badgeVariant: 'completed' as const,
        }
      case 'orchestration':
        return {
          icon: Bot,
          color: '#a855f7',
          badgeVariant: 'secondary' as const,
        }
      case 'system':
        return {
          icon: Cpu,
          color: '#06b6d4',
          badgeVariant: 'outline' as const,
        }
      default:
        return {
          icon: Workflow,
          color: 'var(--primary)',
          badgeVariant: 'default' as const,
        }
    }
  }

  return (
    <div className="space-y-4 w-full min-w-0 max-w-full relative">
      {/* ── 1. Compact Header & Batch Controls ── */}
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="min-w-0">
          <div>
            <h2 className="text-lg font-bold text-foreground tracking-tight">Skills Hub</h2>
          </div>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Click any skill to slide open its directives and configuration.
          </p>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => persistSkills(skills.map((s) => ({ ...s, enabled: true })))}
            className="h-7 px-2.5 text-[11px] gap-1 font-medium"
          >
            <Check className="w-3 h-3 text-emerald-400" />
            <span>Enable All</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => persistSkills(DEFAULT_SKILLS)}
            className="h-7 px-2.5 text-[11px] gap-1 font-medium"
          >
            <RotateCcw className="w-3 h-3 text-muted-foreground" />
            <span>Reset</span>
          </Button>
        </div>
      </div>

      {/* ── 2. Filter Pills Bar & Search Input (ReUI Card Styled) ── */}
      <Card className="p-1.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 w-full min-w-0">
        {/* Category Pills */}
        <div className="flex items-center gap-1 overflow-x-auto py-0.5 min-w-0 flex-1">
          {[
            { id: 'all', label: 'All', icon: Workflow },
            { id: 'design', label: 'Design', icon: Palette },
            { id: 'coding', label: 'Coding', icon: Code2 },
            { id: 'research', label: 'Research', icon: Globe },
            { id: 'orchestration', label: 'Fleet', icon: Bot },
            { id: 'system', label: 'System', icon: Cpu },
          ].map((cat) => {
            const Icon = cat.icon
            const isActive = selectedCategory === cat.id
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => setSelectedCategory(cat.id)}
                className={`h-6 px-2.5 rounded-md flex items-center gap-1.5 text-[11px] font-medium transition-all whitespace-nowrap shrink-0 ${
                  isActive
                    ? 'bg-[var(--primary)] text-primary-foreground font-semibold shadow-2xs'
                    : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--input)]'
                }`}
              >
                <Icon className="w-3 h-3" />
                <span>{cat.label}</span>
              </button>
            )
          })}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-44 shrink-0">
          <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)] pointer-events-none" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search skills..."
            className="h-7 pl-6 pr-2 text-xs bg-[var(--input)]/60 rounded-md"
          />
        </div>
      </Card>

      {/* ── 3. Ultra-Clean Minimal Skills Cards Grid (100% ReUI Card Primitives, 2-Columns) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full min-w-0">
        {filteredSkills.map((skill) => {
          const cat = getCategoryDetails(skill.category)
          const Icon = cat.icon
          const isDrawerOpen = activeDrawerSkill?.id === skill.id

          return (
            <Card
              key={skill.id}
              onClick={() => openDrawer(skill)}
              className={`px-3 py-2.5 transition-all duration-150 flex items-center justify-between gap-2.5 cursor-pointer group select-none ${
                isDrawerOpen
                  ? 'border-[var(--primary)] bg-[var(--primary)]/10 ring-1 ring-[var(--primary)]/40 shadow-xs'
                  : skill.enabled
                  ? 'hover:border-[var(--primary)]/40 hover:bg-[var(--input)]/40'
                  : 'opacity-60 hover:opacity-100'
              }`}
            >
              {/* Left: Icon + Skill Name & Version */}
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <div
                  className="w-7 h-7 rounded-md flex items-center justify-center shrink-0 border transition-transform group-hover:scale-105"
                  style={{
                    backgroundColor: `${cat.color}15`,
                    borderColor: `${cat.color}30`,
                    color: cat.color,
                  }}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold text-[var(--foreground)] truncate group-hover:text-[var(--primary)] transition-colors">
                    {skill.name}
                  </div>
                  <div className="text-[10px] font-mono text-[var(--muted-foreground)] capitalize mt-0.5">
                    {skill.category}
                  </div>
                </div>
              </div>

              {/* Right: Toggle Switch & Chevron Indicator */}
              <div className="shrink-0 flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                <div className="scale-75 origin-right">
                  <Switch
                    checked={skill.enabled}
                    onCheckedChange={() => handleToggleSkill(skill.id)}
                    title={skill.enabled ? 'Disable' : 'Enable'}
                  />
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-[var(--muted-foreground)]/40 group-hover:text-[var(--primary)] group-hover:translate-x-0.5 transition-all" />
              </div>
            </Card>
          )
        })}
      </div>

      {filteredSkills.length === 0 && (
        <Callout variant="default" className="py-6 text-center">
          <FileCode className="w-5 h-5 mx-auto mb-1 opacity-40" />
          <div className="text-xs font-semibold text-[var(--foreground)]">No matching skills found</div>
          <div className="text-[10px] font-mono text-[var(--muted-foreground)] mt-0.5">Try a different query or category filter.</div>
        </Callout>
      )}

      {/* ── 4. Slide-Over Side Drawer for Detailed Info & SKILL.md Editor ── */}
      {activeDrawerSkill && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <div
            onClick={closeDrawer}
            className="absolute inset-0 bg-black/80 transition-opacity duration-150"
          />

          {/* Drawer Panel */}
          <div className="relative w-full max-w-md sm:max-w-lg h-full bg-[var(--card)] border-l border-[var(--border)] shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-250 ease-out">
            {/* Drawer Header */}
            <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between gap-3 bg-[var(--input)]/30 shrink-0">
              <h3 className="text-sm font-bold text-[var(--foreground)] truncate min-w-0 flex-1">
                {activeDrawerSkill.name}
              </h3>

              <div className="flex items-center gap-2 shrink-0">
                <Switch
                  checked={activeDrawerSkill.enabled}
                  onCheckedChange={() => handleToggleSkill(activeDrawerSkill.id)}
                  title={activeDrawerSkill.enabled ? 'Disable' : 'Enable'}
                />
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={closeDrawer}
                  className="w-7 h-7 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Drawer Content */}
            <div className="flex-1 flex flex-col min-h-0 overflow-hidden p-4 space-y-3">
              {/* Quick Summary Callout */}
              <Callout variant="info" className="p-3 space-y-2">
                <p className="text-xs leading-relaxed text-[var(--foreground)]">
                  {activeDrawerSkill.description}
                </p>
                <div className="flex flex-wrap items-center gap-1 pt-1.5 border-t border-[var(--border)]/60">
                  {activeDrawerSkill.tags.map((tag, tIdx) => (
                    <Badge key={tIdx} variant="outline" size="xs" className="text-[9px] font-mono">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </Callout>

              {/* Tabs for Preview / Edit Directives */}
              <Tabs value={activeDrawerTab} onValueChange={setActiveDrawerTab} className="flex-1 flex flex-col min-h-0">
                <div className="flex items-center justify-between gap-2 pb-2 shrink-0">
                  <TabsList className="h-7 p-0.5">
                    <TabsTrigger value="preview" className="text-xs h-6 px-2.5 gap-1.5">
                      <Eye className="w-3 h-3" />
                      <span>Preview</span>
                    </TabsTrigger>
                    <TabsTrigger value="edit" className="text-xs h-6 px-2.5 gap-1.5">
                      <Edit3 className="w-3 h-3" />
                      <span>Edit Directives</span>
                    </TabsTrigger>
                  </TabsList>

                  {activeDrawerTab === 'edit' && (
                    <Button
                      size="sm"
                      onClick={handleSaveDrawerDoc}
                      disabled={isSavingDrawer}
                      className="h-6 px-2.5 text-xs gap-1 font-semibold shadow-2xs"
                    >
                      {drawerSaveSuccess ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span>Saved</span>
                        </>
                      ) : (
                        <>
                          <Save className="w-3 h-3" />
                          <span>{isSavingDrawer ? 'Saving...' : 'Save'}</span>
                        </>
                      )}
                    </Button>
                  )}
                </div>

                <TabsContent value="preview" className="flex-1 min-h-0 mt-0">
                  <ScrollArea className="h-full rounded-lg border border-[var(--border)] bg-[var(--card)] p-3">
                    <div className="text-xs text-[var(--foreground)] leading-relaxed font-mono whitespace-pre-wrap">
                      {drawerEditedContent || 'No directives specified.'}
                    </div>
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="edit" className="flex-1 flex flex-col min-h-0 mt-0">
                  <textarea
                    value={drawerEditedContent}
                    onChange={(e) => setDrawerEditedContent(e.target.value)}
                    placeholder="Enter Markdown directives..."
                    className="flex-1 w-full p-3 font-mono text-xs bg-[#0b0f14] text-[#e2e8f0] border border-[var(--border)] rounded-lg resize-none focus:outline-none focus:ring-1 focus:ring-[var(--primary)] leading-relaxed shadow-inner"
                    spellCheck={false}
                  />
                  <div className="flex items-center justify-between pt-1.5 text-[10px] font-mono text-[var(--muted-foreground)]">
                    <span>Editing {activeDrawerSkill.id}/SKILL.md</span>
                    <span>{drawerEditedContent.length} chars · {drawerEditedContent.split('\n').length} lines</span>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
