import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { Card } from '../reui/card'
import { Badge } from '../reui/badge'
import { Callout } from '../reui/callout'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Switch } from '../ui/switch'
import {
  Compass,
  Globe,
  Search,
  BookOpen,
  MousePointer,
  Layout,
  SlidersHorizontal,
  Rocket,
  FolderTree,
  FileCode,
  Code2,
  Bell,
  CloudSun,
  Plane,
  Video,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Wrench,
  Sparkles,
  Layers,
  Monitor,
  Radio,
} from 'lucide-react'
import { api } from '../../lib/api'
import { cn } from '../../lib/utils'

export type ToolCategoryId =
  | 'research'
  | 'browser'
  | 'desktop'
  | 'files'
  | 'lifestyle'

export interface ToolDefinition {
  id: string
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  category: ToolCategoryId
}

export interface CategoryDefinition {
  id: ToolCategoryId
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
}

const CATEGORIES: CategoryDefinition[] = [
  {
    id: 'research',
    title: 'Research & Intelligence',
    description: 'Deep social extraction, transcripts, repos, and multi-source intelligence reports',
    icon: Radio,
  },
  {
    id: 'browser',
    title: 'Browser & Web Automation',
    description: 'Automated web browsing, DOM inspection, live queries, and document retrieval',
    icon: Globe,
  },
  {
    id: 'desktop',
    title: 'Desktop & System Control',
    description: 'Native mouse input, window management, system hardware, and app execution',
    icon: Monitor,
  },
  {
    id: 'files',
    title: 'Files & Coding Helpers',
    description: 'Local workspace file manipulation, batch processing, and code snippets',
    icon: FileCode,
  },
  {
    id: 'lifestyle',
    title: 'Lifestyle & Utilities',
    description: 'Productivity schedules, weather forecasts, flight availability, and media streams',
    icon: Sparkles,
  },
]

const TOOLS: ToolDefinition[] = [
  // 1. Research & Intelligence
  {
    id: 'agent_reach',
    title: 'Deep Social & Media Research',
    description:
      'Extract YouTube transcripts, Reddit threads, Twitter/X, GitHub repos, TikTok/Instagram audio, and cross-platform reports',
    icon: Compass,
    category: 'research',
  },

  // 2. Browser & Web Automation
  {
    id: 'browser_control',
    title: 'Browser Automation',
    description: 'Playwright automated browser, clicks, forms',
    icon: Globe,
    category: 'browser',
  },
  {
    id: 'web_search',
    title: 'Web Search',
    description: 'DuckDuckGo live internet search',
    icon: Search,
    category: 'browser',
  },
  {
    id: 'web_read_page',
    title: 'Web Page Reader',
    description: 'Web page DOM scraping and reading',
    icon: BookOpen,
    category: 'browser',
  },

  // 3. Desktop & System Control
  {
    id: 'computer_control',
    title: 'Desktop Automation',
    description: 'Native mouse clicks, typing, screen coordinates',
    icon: MousePointer,
    category: 'desktop',
  },
  {
    id: 'desktop_control',
    title: 'Window Manager',
    description: 'Window focus, minimize, maximize, resize',
    icon: Layout,
    category: 'desktop',
  },
  {
    id: 'computer_settings',
    title: 'System Settings',
    description: 'OS volume, brightness, Wi-Fi, bluetooth control',
    icon: SlidersHorizontal,
    category: 'desktop',
  },
  {
    id: 'open_app',
    title: 'App Launcher',
    description: 'Launch local desktop applications',
    icon: Rocket,
    category: 'desktop',
  },

  // 4. Files & Coding Helpers
  {
    id: 'file_controller',
    title: 'File Controller',
    description: 'Read, write, create, list local directory files',
    icon: FolderTree,
    category: 'files',
  },
  {
    id: 'file_processor',
    title: 'Batch File Processor',
    description: 'Bulk file analysis and transformations',
    icon: Layers,
    category: 'files',
  },
  {
    id: 'quick_snippet',
    title: 'Quick Snippets',
    description: 'Save, recall, and search code snippets',
    icon: Code2,
    category: 'files',
  },

  // 5. Lifestyle & Utilities
  {
    id: 'reminder',
    title: 'Smart Reminders',
    description: 'Set alarms, countdowns, and system reminders',
    icon: Bell,
    category: 'lifestyle',
  },
  {
    id: 'weather_report',
    title: 'Weather Forecast',
    description: 'Live atmospheric metrics and forecasts',
    icon: CloudSun,
    category: 'lifestyle',
  },
  {
    id: 'flight_finder',
    title: 'Flight Finder',
    description: 'Search flight availability and airline schedules',
    icon: Plane,
    category: 'lifestyle',
  },
  {
    id: 'youtube_video',
    title: 'YouTube Player',
    description: 'Search and stream YouTube audio/video',
    icon: Video,
    category: 'lifestyle',
  },
]

const STORAGE_KEY = 'zezo_tools_state'

function getInitialToolStates(): Record<string, boolean> {
  const defaults: Record<string, boolean> = {}
  TOOLS.forEach((t) => {
    defaults[t.id] = true
  })
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return { ...defaults, ...parsed }
    }
  } catch {
    // fallback to all enabled
  }
  return defaults
}

export function ToolsSettingsTab() {
  const [toolStates, setToolStates] = useState<Record<string, boolean>>(getInitialToolStates)
  const [loading, setLoading] = useState<boolean>(true)
  const [refreshing, setRefreshing] = useState<boolean>(false)
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [collapsedCategories, setCollapsedCategories] = useState<Record<ToolCategoryId, boolean>>({
    research: false,
    browser: false,
    desktop: false,
    files: false,
    lifestyle: false,
  })
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const showToast = useCallback((message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type })
    setTimeout(() => {
      setToast((cur) => (cur?.message === message ? null : cur))
    }, 3000)
  }, [])

  // Fetch live state from GET /api/tools
  const fetchToolsState = useCallback(
    async (isManualRefresh = false) => {
      if (isManualRefresh) setRefreshing(true)
      else setLoading(true)

      try {
        const res = await api.getTools()
        if (res && res.data) {
          const allowedList: Array<{ tool?: string; name?: string }> = res.data.allowed_tools || []
          const filteredList: Array<{ tool?: string; name?: string; reason?: string }> =
            res.data.filtered_tools || []

          const updated: Record<string, boolean> = { ...toolStates }

          // Mark allowed tools
          allowedList.forEach((item) => {
            const id = item.tool || item.name
            if (id) updated[id] = true
          })

          // Mark explicitly disabled tools
          filteredList.forEach((item) => {
            const id = item.tool || item.name
            if (id && item.reason === 'tool_disabled') {
              updated[id] = false
            }
          })

          setToolStates(updated)
          try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
          } catch {
            // ignore localStorage quota
          }
        }
        if (isManualRefresh) {
          showToast('Tools registry refreshed successfully.', 'success')
        }
      } catch (err: any) {
        console.warn('Could not fetch tools from /api/tools, using cached/local states:', err)
        if (isManualRefresh) {
          showToast('Failed to refresh from backend. Using local state.', 'error')
        }
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [showToast, toolStates]
  )

  useEffect(() => {
    fetchToolsState()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Optimistic Toggle Handler
  const handleToggle = async (toolId: string, nextChecked: boolean) => {
    // 1. Optimistic local state update
    const nextStates = { ...toolStates, [toolId]: nextChecked }
    setToolStates(nextStates)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextStates))
    } catch {
      // ignore
    }

    const tool = TOOLS.find((t) => t.id === toolId)
    const toolTitle = tool?.title || toolId

    // 2. Dispatch POST /api/tools/{name}/toggle
    try {
      await api.toggleTool(toolId, nextChecked)
      showToast(`${toolTitle} ${nextChecked ? 'enabled' : 'disabled'}.`, 'success')
    } catch (err: any) {
      console.warn(`Backend toggle call for ${toolId} failed:`, err)
      // Keep optimistic state but inform the user gracefully
      showToast(
        `${toolTitle} ${nextChecked ? 'enabled' : 'disabled'} locally (${err?.message || 'Server toggle pending'}).`,
        'success'
      )
    }
  }

  // Toggle Category Collapsed
  const toggleCategoryCollapse = (catId: ToolCategoryId) => {
    setCollapsedCategories((prev) => ({
      ...prev,
      [catId]: !prev[catId],
    }))
  }

  // Bulk actions
  const setAllCategoryTools = async (catId: ToolCategoryId, enable: boolean) => {
    const categoryTools = TOOLS.filter((t) => t.category === catId)
    const updated = { ...toolStates }
    categoryTools.forEach((t) => {
      updated[t.id] = enable
    })
    setToolStates(updated)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
    } catch {
      // ignore
    }

    // Dispatch background toggles
    await Promise.allSettled(categoryTools.map((t) => api.toggleTool(t.id, enable)))
    showToast(`All ${catId} tools ${enable ? 'enabled' : 'disabled'}.`, 'success')
  }

  const toggleAllCollapse = (collapsed: boolean) => {
    setCollapsedCategories({
      research: collapsed,
      browser: collapsed,
      desktop: collapsed,
      files: collapsed,
      lifestyle: collapsed,
    })
  }

  // Filtered tools by search query
  const filteredTools = useMemo(() => {
    if (!searchQuery.trim()) return TOOLS
    const q = searchQuery.toLowerCase().trim()
    return TOOLS.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.id.toLowerCase().includes(q)
    )
  }, [searchQuery])

  // Count active stats
  const stats = useMemo(() => {
    let active = 0
    let disabled = 0
    TOOLS.forEach((t) => {
      if (toolStates[t.id] ?? true) active++
      else disabled++
    })
    return { total: TOOLS.length, active, disabled }
  }, [toolStates])

  const areAllCollapsed = useMemo(() => {
    return Object.values(collapsedCategories).every(Boolean)
  }, [collapsedCategories])

  return (
    <div className="space-y-6">
      {/* ──────────────── HEADER ──────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-foreground tracking-tight">Tools Management</h2>
            <Badge variant="outline" className="font-mono text-[10px] px-2 py-0.5">
              {stats.active}/{stats.total} Active
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Configure, inspect, and toggle the 15 system tools across 5 specialized autonomous categories.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => toggleAllCollapse(!areAllCollapsed)}
            className="text-xs h-8 border-border hover:bg-muted"
          >
            {areAllCollapsed ? (
              <>
                <ChevronDown className="w-3.5 h-3.5 mr-1" />
                Expand All
              </>
            ) : (
              <>
                <ChevronUp className="w-3.5 h-3.5 mr-1" />
                Collapse All
              </>
            )}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchToolsState(true)}
            disabled={refreshing || loading}
            className="text-xs h-8 border-border hover:bg-muted"
            title="Refresh tool status from backend"
          >
            <RefreshCw className={cn('w-3.5 h-3.5 mr-1', refreshing && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </div>

      {/* ──────────────── CALLOUT BANNER ──────────────── */}
      <Callout variant="info" className="text-xs">
        <Wrench className="w-4 h-4 text-primary" />
        <div>
          <span className="font-semibold text-foreground">Live Gemini Function Calling:</span> Enabled
          tools are automatically injected into the Live WebSocket session and agent tool declarations.
          Toggling a tool immediately reflects in subsequent voice and task requests.
        </div>
      </Callout>

      {/* ──────────────── SEARCH & STATS BAR ──────────────── */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-lg bg-card border border-border">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search tools by title, slug, or capability..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-8 text-xs bg-background/50 border-border"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className="text-muted-foreground text-[11px]">System Status:</span>
          <Badge variant="success" size="sm" className="font-mono text-[10px]">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            {stats.active} Enabled
          </Badge>
          {stats.disabled > 0 && (
            <Badge variant="outline" size="sm" className="font-mono text-[10px] text-muted-foreground">
              <XCircle className="w-3 h-3 mr-1" />
              {stats.disabled} Disabled
            </Badge>
          )}
        </div>
      </div>

      {/* ──────────────── TOAST NOTIFICATION ──────────────── */}
      {toast && (
        <div
          className={cn(
            'p-3 rounded-md border text-xs flex items-center justify-between transition-all animate-in fade-in slide-in-from-top-1',
            toast.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-red-500/10 border-red-500/30 text-red-400'
          )}
        >
          <span>{toast.message}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setToast(null)}
            className="h-5 px-1.5 text-[11px] hover:bg-transparent"
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* ──────────────── CATEGORIES ACCORDION ──────────────── */}
      <div className="space-y-4">
        {CATEGORIES.map((cat) => {
          const categoryTools = filteredTools.filter((t) => t.category === cat.id)
          if (searchQuery.trim() && categoryTools.length === 0) return null

          const isCollapsed = collapsedCategories[cat.id]
          const activeInCategory = categoryTools.filter((t) => toolStates[t.id] ?? true).length
          const CategoryIcon = cat.icon

          return (
            <div
              key={cat.id}
              className="rounded-xl border border-border bg-card/60 backdrop-blur-xs overflow-hidden transition-all duration-200"
            >
              {/* Category Header */}
              <div
                onClick={() => toggleCategoryCollapse(cat.id)}
                className="flex items-center justify-between p-4 cursor-pointer select-none bg-muted/20 hover:bg-muted/40 transition-colors border-b border-border/40"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                    <CategoryIcon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-foreground tracking-tight">
                        {cat.title}
                      </span>
                      <Badge
                        variant={
                          activeInCategory === categoryTools.length
                            ? 'success'
                            : activeInCategory > 0
                            ? 'warning'
                            : 'secondary'
                        }
                        size="xs"
                        className="font-mono text-[9px]"
                      >
                        {activeInCategory}/{categoryTools.length} Active
                      </Badge>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">
                      {cat.description}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setAllCategoryTools(cat.id, true)}
                    className="h-7 text-[10px] text-muted-foreground hover:text-foreground px-2"
                  >
                    Enable All
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setAllCategoryTools(cat.id, false)}
                    className="h-7 text-[10px] text-muted-foreground hover:text-foreground px-2"
                  >
                    Disable All
                  </Button>
                  <div
                    onClick={() => toggleCategoryCollapse(cat.id)}
                    className="p-1 text-muted-foreground hover:text-foreground cursor-pointer"
                  >
                    {isCollapsed ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronUp className="w-4 h-4" />
                    )}
                  </div>
                </div>
              </div>

              {/* Category Content: Tool Cards Grid */}
              {!isCollapsed && (
                <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                  {categoryTools.map((tool) => {
                    const isEnabled = toolStates[tool.id] ?? true
                    const ToolIcon = tool.icon

                    return (
                      <Card
                        key={tool.id}
                        className={cn(
                          'p-3.5 transition-all duration-150 border flex flex-col justify-between',
                          isEnabled
                            ? 'bg-card border-border/80 hover:border-primary/40 shadow-xs'
                            : 'bg-muted/10 border-border/40 opacity-75'
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3 flex-1 min-w-0">
                            <div
                              className={cn(
                                'w-9 h-9 rounded-lg flex items-center justify-center shrink-0 border transition-colors',
                                isEnabled
                                  ? 'bg-primary/10 text-primary border-primary/25'
                                  : 'bg-muted text-muted-foreground border-border'
                              )}
                            >
                              <ToolIcon className="w-4 h-4" />
                            </div>

                            <div className="flex-1 min-w-0 space-y-1">
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <h4 className="font-semibold text-xs text-foreground tracking-tight truncate">
                                  {tool.title}
                                </h4>
                                <code className="text-[9px] text-muted-foreground font-mono bg-muted/60 px-1 py-0.2 rounded border border-border/40">
                                  {tool.id}
                                </code>
                              </div>

                              <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                                {tool.description}
                              </p>
                            </div>
                          </div>

                          {/* Toggle Switch & Status Pill */}
                          <div className="flex flex-col items-end gap-1.5 shrink-0 pt-0.5">
                            <Switch
                              checked={isEnabled}
                              onCheckedChange={(checked) => handleToggle(tool.id, checked)}
                              aria-label={`Toggle ${tool.title}`}
                            />
                            <Badge
                              variant={isEnabled ? 'success' : 'outline'}
                              size="xs"
                              className={cn(
                                'font-mono text-[8px] px-1 py-0',
                                !isEnabled && 'text-muted-foreground border-border/60'
                              )}
                            >
                              {isEnabled ? 'ACTIVE' : 'OFF'}
                            </Badge>
                          </div>
                        </div>
                      </Card>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}

        {filteredTools.length === 0 && (
          <div className="p-8 text-center rounded-xl border border-dashed border-border bg-card/40 space-y-2">
            <Search className="w-6 h-6 text-muted-foreground mx-auto" />
            <p className="text-xs text-foreground font-medium">No tools match "{searchQuery}"</p>
            <p className="text-[11px] text-muted-foreground">
              Try searching for a different keyword like "browser", "search", or "desktop".
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSearchQuery('')}
              className="text-xs h-7 mt-2"
            >
              Clear Search
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
export default ToolsSettingsTab
