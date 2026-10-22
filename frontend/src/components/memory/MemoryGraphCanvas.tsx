import React, { useRef, useEffect, useState, useMemo, useCallback } from 'react'
import ForceGraph3D from '3d-force-graph'
import SpriteText from 'three-spritetext'
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  Focus,
  RefreshCw,
  Search,
  Sparkles,
  SlidersHorizontal,
  Clock,
  Calendar,
  Layers,
  ArrowUpDown,
  X,
  Tag,
} from 'lucide-react'
import { Badge } from '../reui/badge'
import { Button } from '../ui/button'
import { Input } from '../ui/input'

// --- TYPES ---
export interface GraphNode {
  id: string
  label: string
  category: string
  file: string
  snippet: string
  color: string
  size: number
  tags: string[]
  updated?: string | number
  date?: string
  timestamp?: number
  x?: number
  y?: number
  z?: number
  vx?: number
  vy?: number
  vz?: number
  fx?: number
  fy?: number
  fz?: number
}

export interface GraphLink {
  source: string | GraphNode
  target: string | GraphNode
  value?: number
}

interface MemoryGraphCanvasProps {
  nodes: GraphNode[]
  links: GraphLink[]
  selectedNodeId: string | null
  onSelectNode: (node: GraphNode | null) => void
  onRefresh: () => void
  isLoading?: boolean
}

function getNodeTimestamp(node: GraphNode): number {
  if (node.timestamp && node.timestamp > 0) {
    return node.timestamp > 1e11 ? node.timestamp : node.timestamp * 1000
  }
  if (node.date) {
    const parsed = Date.parse(node.date.replace(' ', 'T'))
    if (!isNaN(parsed) && parsed > 0) return parsed
  }
  const match = (node.id + ' ' + (node.file || '')).match(/conv_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/)
  if (match) {
    const [, y, m, d, h, mi, s] = match
    return new Date(Number(y), Number(m) - 1, Number(d), Number(h), Number(mi), Number(s)).getTime()
  }
  if (typeof node.updated === 'number' && node.updated > 0) {
    return node.updated > 1e11 ? node.updated : node.updated * 1000
  }
  if (typeof node.updated === 'string' && node.updated) {
    const parsed = Date.parse(node.updated)
    if (!isNaN(parsed) && parsed > 0) return parsed
  }
  return 0
}

function formatNodeDateTime(node: GraphNode): string {
  const ts = getNodeTimestamp(node)
  if (ts > 0) {
    const d = new Date(ts)
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  if (node.date) return node.date
  return 'Saved note'
}

function formatRelativeTime(ts: number): string {
  if (!ts) return ''
  const diffSec = Math.floor((Date.now() - ts) / 1000)
  if (diffSec < 60) return 'just now'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`
  return `${Math.floor(diffSec / 604800)}w ago`
}

export const MemoryGraphCanvas: React.FC<MemoryGraphCanvasProps> = ({
  nodes,
  links,
  selectedNodeId,
  onSelectNode,
  onRefresh,
  isLoading,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const canvasAreaRef = useRef<HTMLDivElement | null>(null)
  const graphInstanceRef = useRef<any>(null)

  // Dimensions
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({ width: 0, height: 0 })
  const [viewMode, setViewMode] = useState<'graph' | 'timeline'>('graph')

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('')
  const [datePreset, setDatePreset] = useState<'all' | '24h' | '7d' | '30d' | 'custom'>('all')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc')
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null)

  // Controls
  const [showAnimControls, setShowAnimControls] = useState(false)
  const [autoRotateSpeed, setAutoRotateSpeed] = useState(0.5)
  const [particleSpeed, setParticleSpeed] = useState(0.006)
  const [chargeStrength, setChargeStrength] = useState(-90)
  const [linkDistance, setLinkDistance] = useState(85)
  const [nodeSize, setNodeSize] = useState(3.5)
  const [particleCount] = useState(2)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Track size
  useEffect(() => {
    const target = canvasAreaRef.current || containerRef.current
    if (!target) return

    const updateSize = () => {
      const el = canvasAreaRef.current || containerRef.current
      if (el) {
        const { clientWidth, clientHeight } = el
        if (clientWidth > 0 && clientHeight > 0) {
          setDimensions({ width: clientWidth, height: clientHeight })
        }
      }
    }
    updateSize()

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          setDimensions({ width: Math.floor(width), height: Math.floor(height) })
        }
      }
    })
    ro.observe(target)
    return () => ro.disconnect()
  }, [viewMode])

  useEffect(() => {
    if (nodes.length === 0 && onRefresh) {
      onRefresh()
    }
  }, [nodes.length, onRefresh])

  // Category counts
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    nodes.forEach((n) => {
      const cat = (n.category || 'knowledge').toLowerCase()
      counts[cat] = (counts[cat] || 0) + 1
    })
    return counts
  }, [nodes])

  // Filtered nodes
  const effectiveNodes = useMemo(() => {
    return nodes.filter((n) => {
      const cat = (n.category || 'knowledge').toLowerCase()
      if (categoryFilter !== 'all' && cat !== categoryFilter) return false

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase()
        const matchLabel = n.label?.toLowerCase().includes(q)
        const matchSnippet = n.snippet?.toLowerCase().includes(q)
        const matchFile = n.file?.toLowerCase().includes(q)
        const matchTag = n.tags?.some((t) => t.toLowerCase().includes(q))
        if (!matchLabel && !matchSnippet && !matchFile && !matchTag) return false
      }

      if (datePreset !== 'all') {
        const ts = getNodeTimestamp(n)
        if (!ts) return false
        const now = Date.now()
        if (datePreset === '24h' && now - ts > 86400000) return false
        if (datePreset === '7d' && now - ts > 7 * 86400000) return false
        if (datePreset === '30d' && now - ts > 30 * 86400000) return false
        if (datePreset === 'custom') {
          if (startDate && ts < new Date(startDate).getTime()) return false
          if (endDate && ts > new Date(endDate).getTime() + 86400000) return false
        }
      }
      return true
    })
  }, [nodes, categoryFilter, searchQuery, datePreset, startDate, endDate])

  const effectiveNodeIdSet = useMemo(() => new Set(effectiveNodes.map((n) => n.id)), [effectiveNodes])

  const effectiveLinks = useMemo(() => {
    return links.filter((l) => {
      const sId = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source
      const tId = typeof l.target === 'object' ? (l.target as GraphNode).id : l.target
      return effectiveNodeIdSet.has(sId) && effectiveNodeIdSet.has(tId)
    })
  }, [links, effectiveNodeIdSet])

  const timelineNodes = useMemo(() => {
    return [...effectiveNodes].sort((a, b) => {
      const tsA = getNodeTimestamp(a)
      const tsB = getNodeTimestamp(b)
      return sortOrder === 'desc' ? tsB - tsA : tsA - tsB
    })
  }, [effectiveNodes, sortOrder])

  const { adjacencyMap, nodeDegrees } = useMemo(() => {
    const adj = new Map<string, Set<string>>()
    const deg = new Map<string, number>()

    effectiveNodes.forEach((n) => {
      adj.set(n.id, new Set())
      deg.set(n.id, 0)
    })

    effectiveLinks.forEach((l) => {
      const sId = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source
      const tId = typeof l.target === 'object' ? (l.target as GraphNode).id : l.target
      if (sId && tId && adj.has(sId) && adj.has(tId)) {
        adj.get(sId)!.add(tId)
        adj.get(tId)!.add(sId)
        deg.set(sId, (deg.get(sId) || 0) + 1)
        deg.set(tId, (deg.get(tId) || 0) + 1)
      }
    })

    return { adjacencyMap: adj, nodeDegrees: deg }
  }, [effectiveNodes, effectiveLinks])

  const highlightNodes = useMemo(() => {
    const set = new Set<string>()
    if (hoverNode) {
      set.add(hoverNode.id)
      const neighbors = adjacencyMap.get(hoverNode.id)
      if (neighbors) {
        neighbors.forEach((nId) => set.add(nId))
      }
    }
    return set
  }, [hoverNode, adjacencyMap])

  // --- INITIALIZE & RESIZE 3D FORCE GRAPH ---
  useEffect(() => {
    if (viewMode !== 'graph' || !canvasAreaRef.current || dimensions.width === 0 || dimensions.height === 0) return

    if (graphInstanceRef.current) {
      try {
        graphInstanceRef.current.width(dimensions.width).height(dimensions.height)
      } catch (e) {}
      return
    }

    canvasAreaRef.current.innerHTML = ''

    try {
      const GraphCreator = (ForceGraph3D as any).default || ForceGraph3D
      const Graph = GraphCreator(canvasAreaRef.current, { controlType: 'orbit' })
        .width(dimensions.width)
        .height(dimensions.height)
        .backgroundColor('#08090d')
        .showNavInfo(false)
        .nodeRelSize(nodeSize)
        .nodeVal((node: any) => {
          const degree = nodeDegrees.get(node.id) || 0
          return Math.max(2, Math.min(8, 2 + Math.sqrt(degree) * 0.9))
        })
        .nodeColor((node: any) => {
          if (node.id === selectedNodeId) return '#f59e0b'
          if (hoverNode) {
            if (highlightNodes.has(node.id)) {
              return node.color || (node.category === 'tag' ? '#c084fc' : '#38bdf8')
            }
            return 'rgba(255, 255, 255, 0.12)'
          }
          if (node.color) return node.color
          if (node.category === 'tag') return '#a78bfa'
          return '#38bdf8'
        })
        .nodeThreeObject((node: any) => {
          const SpriteCls = (SpriteText as any).default || SpriteText
          const sprite = new SpriteCls(node.label || node.id)
          sprite.color = node.id === selectedNodeId ? '#f59e0b' : node.category === 'tag' ? '#c084fc' : '#e2e8f0'
          sprite.textHeight = 3.2
          sprite.padding = 2
          sprite.backgroundColor = 'rgba(12, 14, 21, 0.85)'
          sprite.borderColor = 'rgba(56, 189, 248, 0.3)'
          sprite.borderWidth = 0.5
          sprite.borderRadius = 3
          return sprite
        })
        .nodeThreeObjectExtend(true)
        .linkColor((link: any) => {
          const sId = typeof link.source === 'object' ? link.source.id : link.source
          const tId = typeof link.target === 'object' ? link.target.id : link.target
          if (hoverNode && (sId === hoverNode.id || tId === hoverNode.id)) return '#38bdf8'
          if (selectedNodeId && (sId === selectedNodeId || tId === selectedNodeId)) return '#f59e0b'
          return 'rgba(56, 189, 248, 0.25)'
        })
        .linkWidth((link: any) => {
          const sId = typeof link.source === 'object' ? link.source.id : link.source
          const tId = typeof link.target === 'object' ? link.target.id : link.target
          if (hoverNode && (sId === hoverNode.id || tId === hoverNode.id)) return 2
          return 1
        })
        .linkDirectionalParticles(particleCount)
        .linkDirectionalParticleSpeed(particleSpeed)
        .linkDirectionalParticleWidth(2)
        .linkDirectionalParticleColor(() => '#38bdf8')
        .onNodeClick((node: any) => {
          onSelectNode(node as GraphNode)
          Graph.cameraPosition(
            { x: node.x * 1.5, y: node.y * 1.5, z: (node.z || 0) + 100 },
            node,
            1000
          )
        })
        .onNodeHover((node: any) => {
          setHoverNode((node || null) as GraphNode | null)
        })
        .onBackgroundClick(() => onSelectNode(null))

      // Apply D3 forces
      if (Graph.d3Force) {
        Graph.d3Force('charge')?.strength(chargeStrength)
        Graph.d3Force('link')?.distance(linkDistance)
      }

      // Auto rotate controls
      try {
        const controls = Graph.controls()
        if (controls) {
          controls.autoRotate = true
          controls.autoRotateSpeed = autoRotateSpeed
        }
      } catch (e) {
        // ignore
      }

      // Set initial graph data
      Graph.graphData({
        nodes: effectiveNodes,
        links: effectiveLinks,
      })

      graphInstanceRef.current = Graph
    } catch (err) {
      console.error('Failed to initialize 3D force graph:', err)
    }

    return () => {}
  }, [viewMode, dimensions.width, dimensions.height])

  // Cleanup graph instance when switching away from graph view
  useEffect(() => {
    if (viewMode !== 'graph') {
      try {
        graphInstanceRef.current?._destructor?.()
        graphInstanceRef.current = null
      } catch (e) {}
    }
  }, [viewMode])

  // --- SEPARATE EFFECTS FOR DYNAMIC UPDATES (NO RE-CREATION) ---
  useEffect(() => {
    if (graphInstanceRef.current && dimensions.width > 0 && dimensions.height > 0) {
      graphInstanceRef.current.width(dimensions.width).height(dimensions.height)
    }
  }, [dimensions.width, dimensions.height])

  useEffect(() => {
    if (graphInstanceRef.current) {
      graphInstanceRef.current.graphData({
        nodes: effectiveNodes,
        links: effectiveLinks,
      })
      if (effectiveNodes.length > 0) {
        setTimeout(() => {
          try {
            graphInstanceRef.current?.zoomToFit?.(500, 40)
          } catch (e) {}
        }, 150)
      }
    }
  }, [effectiveNodes, effectiveLinks])

  useEffect(() => {
    if (graphInstanceRef.current) {
      graphInstanceRef.current.refresh()
    }
  }, [selectedNodeId, hoverNode, highlightNodes])

  const handleResetView = useCallback(() => {
    if (graphInstanceRef.current) {
      graphInstanceRef.current.zoomToFit(600, 40)
    }
  }, [])

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((v) => !v)
  }, [])

  const handleZoomIn = useCallback(() => {
    if (graphInstanceRef.current) {
      const cam = graphInstanceRef.current.camera()
      if (cam) {
        graphInstanceRef.current.cameraPosition(
          { x: cam.position.x * 0.7, y: cam.position.y * 0.7, z: cam.position.z * 0.7 },
          undefined,
          350
        )
      }
    }
  }, [])

  const handleZoomOut = useCallback(() => {
    if (graphInstanceRef.current) {
      const cam = graphInstanceRef.current.camera()
      if (cam) {
        graphInstanceRef.current.cameraPosition(
          { x: cam.position.x * 1.4, y: cam.position.y * 1.4, z: cam.position.z * 1.4 },
          undefined,
          350
        )
      }
    }
  }, [])

  // ESC exits fullscreen
  useEffect(() => {
    if (!isFullscreen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsFullscreen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isFullscreen])

  const hasActiveFilters = datePreset !== 'all' || startDate !== '' || endDate !== '' || categoryFilter !== 'all' || searchQuery !== ''

  const handleResetFilters = () => {
    setDatePreset('all')
    setStartDate('')
    setEndDate('')
    setCategoryFilter('all')
    setSearchQuery('')
  }

  return (
    <div
      ref={containerRef}
      className={`relative w-full ${
        isFullscreen ? 'fixed inset-0 z-50 h-screen rounded-none' : 'h-full flex-1 min-h-[440px]'
      } rounded-2xl bg-[#08090d] border border-border/50 overflow-hidden shadow-2xl flex flex-col select-none`}
    >
      {/* ── UNIFIED HEADER & CONTROLS TOOLBAR ── */}
      <div className="shrink-0 bg-[#0c0e15]/95 border-b border-border/70 p-3 md:p-3.5 space-y-2.5 z-20 backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-2.5">
          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex items-center bg-[#151824] border border-border/80 rounded-xl p-0.5 shadow-inner">
              <button
                type="button"
                onClick={() => setViewMode('graph')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  viewMode === 'graph'
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
                }`}
                title="Interactive 3D Knowledge Graph"
              >
                <Layers className="w-3.5 h-3.5" />
                <span>3D Graph</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('timeline')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  viewMode === 'timeline'
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
                }`}
                title="Chronological Timeline Feed of Conversations & Notes"
              >
                <Clock className="w-3.5 h-3.5" />
                <span>Timeline Feed</span>
              </button>
            </div>

            {/* Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground pointer-events-none" />
              <Input
                placeholder="Search notes, directives, or #tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 pl-8 pr-7 text-xs w-48 sm:w-64 bg-[#151824] border-border/80 rounded-xl shadow-xs focus:ring-1 focus:ring-primary"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <Badge variant="outline" className="text-[10px] font-mono h-7 px-2.5 text-primary border-primary/30 bg-primary/10 gap-1.5">
              <Sparkles className="w-2.5 h-2.5" />
              <span>
                {effectiveNodes.length} / {nodes.length} Notes
              </span>
            </Badge>

            {viewMode === 'timeline' && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setSortOrder((v) => (v === 'desc' ? 'asc' : 'desc'))}
                className="h-7 px-2 text-xs font-mono text-muted-foreground hover:text-foreground gap-1 bg-[#151824] border border-border/80"
              >
                <ArrowUpDown className="w-3 h-3" />
                <span>{sortOrder === 'desc' ? 'Newest' : 'Oldest'}</span>
              </Button>
            )}

            {viewMode === 'graph' && (
              <>
                <Button type="button" variant="ghost" size="sm" onClick={handleZoomIn} className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground bg-[#151824] border border-border/80" title="Zoom In">
                  <ZoomIn className="w-3.5 h-3.5" />
                </Button>
                <Button type="button" variant="ghost" size="sm" onClick={handleZoomOut} className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground bg-[#151824] border border-border/80" title="Zoom Out">
                  <ZoomOut className="w-3.5 h-3.5" />
                </Button>
                <Button type="button" variant="ghost" size="sm" onClick={handleResetView} className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground bg-[#151824] border border-border/80" title="Fit to Screen">
                  <Focus className="w-3.5 h-3.5" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAnimControls((v) => !v)}
                  className={`h-7 w-7 p-0 text-muted-foreground hover:text-foreground bg-[#151824] border border-border/80 ${showAnimControls ? 'text-primary border-primary/50' : ''}`}
                  title="Graph Physics Controls"
                >
                  <SlidersHorizontal className="w-3.5 h-3.5" />
                </Button>
              </>
            )}

            <Button type="button" variant="ghost" size="sm" onClick={handleToggleFullscreen} className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground bg-[#151824] border border-border/80" title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}>
              {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </Button>

            <Button type="button" variant="ghost" size="sm" onClick={onRefresh} className={`h-7 w-7 p-0 text-muted-foreground hover:text-foreground bg-[#151824] border border-border/80 ${isLoading ? 'animate-spin' : ''}`} title="Refresh Vault Graph">
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {/* Row 2: Filters */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/40 text-xs">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-mono text-muted-foreground flex items-center gap-1 mr-1">
              <Calendar className="w-3 h-3 text-primary" />
              <span>Time:</span>
            </span>
            {(
              [
                { id: 'all', label: 'All Time' },
                { id: '24h', label: 'Past 24h' },
                { id: '7d', label: 'Past 7 Days' },
                { id: '30d', label: 'Past 30 Days' },
              ] as const
            ).map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => setDatePreset(preset.id)}
                className={`px-2 py-0.5 rounded-md text-[11px] font-mono transition-all border ${
                  datePreset === preset.id
                    ? 'bg-primary/20 text-primary border-primary/50 font-semibold'
                    : 'bg-[#151824] text-muted-foreground border-border/70 hover:text-foreground'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-mono text-muted-foreground mr-1">Category:</span>
            <button
              type="button"
              onClick={() => setCategoryFilter('all')}
              className={`px-2 py-0.5 rounded-md text-[11px] font-mono transition-all border ${
                categoryFilter === 'all'
                  ? 'bg-primary/20 text-primary border-primary/50 font-semibold'
                  : 'bg-[#151824] text-muted-foreground border-border/70 hover:text-foreground'
              }`}
            >
              All ({nodes.length})
            </button>
            {Object.entries(categoryCounts).map(([cat, count]) => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategoryFilter(cat)}
                className={`px-2 py-0.5 rounded-md text-[11px] font-mono capitalize transition-all border ${
                  categoryFilter === cat
                    ? 'bg-primary/20 text-primary border-primary/50 font-semibold'
                    : 'bg-[#151824] text-muted-foreground border-border/70 hover:text-foreground'
                }`}
              >
                {cat} ({count})
              </button>
            ))}

            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="px-2 py-0.5 rounded-md text-[11px] font-mono text-red-400 hover:text-red-300 bg-red-500/10 border border-red-500/30 flex items-center gap-1 ml-1"
                title="Clear all active filters"
              >
                <X className="w-2.5 h-2.5" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── MAIN CONTENT AREA ── */}
      <div className="flex-1 w-full min-h-0 relative overflow-hidden bg-[#08090d]">
        <div ref={canvasAreaRef} className={`absolute inset-0 w-full h-full ${viewMode === 'graph' ? 'block' : 'hidden'}`} />
        {viewMode === 'timeline' && (
          <div className="w-full h-full overflow-y-auto p-4 md:p-6 space-y-3">
            {timelineNodes.length === 0 ? (
              <div className="h-64 flex flex-col items-center justify-center text-muted-foreground gap-2">
                <Clock className="w-8 h-8 text-muted-foreground/40" />
                <p className="text-sm font-medium">No conversation turns or notes found for this time range.</p>
                {hasActiveFilters && (
                  <Button type="button" variant="outline" size="sm" onClick={handleResetFilters} className="mt-2 text-xs">
                    Clear Filters
                  </Button>
                )}
              </div>
            ) : (
              <div className="max-w-4xl mx-auto space-y-3">
                {timelineNodes.map((node) => {
                  const isSelected = selectedNodeId === node.id
                  const formattedDate = formatNodeDateTime(node)
                  const ts = getNodeTimestamp(node)
                  const relTime = formatRelativeTime(ts)

                  return (
                    <div
                      key={node.id}
                      onClick={() => onSelectNode(node)}
                      className={`group cursor-pointer rounded-xl border p-4 transition-all duration-150 ${
                        isSelected
                          ? 'bg-[#151926] border-primary shadow-lg ring-1 ring-primary/40'
                          : 'bg-[#0f111a]/80 border-border/70 hover:border-primary/50 hover:bg-[#131622] hover:shadow-md'
                      }`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 capitalize">
                            {node.category || 'knowledge'}
                          </span>
                          <span className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">
                            {node.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] font-mono text-muted-foreground">
                          {relTime && <span className="text-primary/80">{relTime}</span>}
                          <span>{formattedDate}</span>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2 font-mono bg-[#08090d]/60 p-2.5 rounded-lg border border-border/40">
                        {node.snippet || node.file || 'No snippet available.'}
                      </p>
                      {node.tags && node.tags.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 mt-2.5 pt-2 border-t border-border/40">
                          <Tag className="w-2.5 h-2.5 text-muted-foreground/60" />
                          {node.tags.map((tag) => (
                            <span
                              key={tag}
                              className="text-[10px] font-mono text-muted-foreground/80 bg-[#161826] px-1.5 py-0.5 rounded border border-border/50"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Animation Controls Panel */}
      {showAnimControls && viewMode === 'graph' && (
        <div className="absolute bottom-3 left-3 z-30 bg-[#11131a]/95 border border-border/80 rounded-xl p-3 w-64 text-xs text-foreground shadow-xl space-y-2.5 max-h-[70vh] overflow-y-auto backdrop-blur-md">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Auto-rotate</span>
            <input
              type="range"
              min={0}
              max={2}
              step={0.1}
              value={autoRotateSpeed}
              onChange={(e) => setAutoRotateSpeed(Number(e.target.value))}
              className="w-28"
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Particle flow</span>
            <input
              type="range"
              min={0}
              max={0.02}
              step={0.001}
              value={particleSpeed}
              onChange={(e) => setParticleSpeed(Number(e.target.value))}
              className="w-28"
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Node size</span>
            <input
              type="range"
              min={1}
              max={8}
              step={0.5}
              value={nodeSize}
              onChange={(e) => setNodeSize(Number(e.target.value))}
              className="w-28"
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Charge</span>
            <input
              type="range"
              min={-200}
              max={0}
              step={5}
              value={chargeStrength}
              onChange={(e) => setChargeStrength(Number(e.target.value))}
              className="w-28"
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Link distance</span>
            <input
              type="range"
              min={30}
              max={200}
              step={5}
              value={linkDistance}
              onChange={(e) => setLinkDistance(Number(e.target.value))}
              className="w-28"
            />
          </div>
        </div>
      )}
    </div>
  )
}
