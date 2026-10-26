import React, { useRef, useEffect, useState, useMemo, useCallback } from 'react'
import ForceGraph3D from '3d-force-graph'
import SpriteText from 'three-spritetext'
import {
  RefreshCw,
  Search,
  Sparkles,
  Clock,
  X,
  ZoomIn,
  ZoomOut,
  Focus,
  Maximize2,
  Minimize2,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react'
import { Badge } from '../reui/badge'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { api } from '../../lib/api'

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

export const MemoryGraphCanvas: React.FC<MemoryGraphCanvasProps> = ({
  nodes,
  links,
  selectedNodeId,
  onSelectNode,
  onRefresh,
  isLoading = false,
}) => {
  const canvasAreaRef = useRef<HTMLDivElement>(null)
  const graphInstanceRef = useRef<any>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const [searchQuery, setSearchQuery] = useState('')
  const [timeRange, setTimeRange] = useState<'all' | '24h' | '7d' | '30d'>('all')
  const [viewMode, setViewMode] = useState<'graph' | 'timeline'>('graph')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showAnimControls, setShowAnimControls] = useState(false)
  const [autoRotateSpeed, setAutoRotateSpeed] = useState(0.6)
  const [particleSpeed, setParticleSpeed] = useState(0.005)
  const [particleCount, setParticleCount] = useState(2)
  const [customNodeSize, setCustomNodeSize] = useState(4)
  const [chargeStrength, setChargeStrength] = useState(-70)
  const [linkDistance, setLinkDistance] = useState(90)
  const [nodeMotion, setNodeMotion] = useState(true)
  const nodeSize = customNodeSize

  const selectedNodeIdRef = useRef(selectedNodeId)
  selectedNodeIdRef.current = selectedNodeId

  const hoverNodeRef = useRef<GraphNode | null>(null)

  const highlightNodesRef = useRef<Set<string>>(new Set())
  const adjacencyMapRef = useRef<Map<string, Set<string>>>(new Map())

  // Zoom & view handlers
  const handleZoomIn = useCallback(() => {
    if (graphInstanceRef.current) {
      const cam = graphInstanceRef.current.camera?.()
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
      const cam = graphInstanceRef.current.camera?.()
      if (cam) {
        graphInstanceRef.current.cameraPosition(
          { x: cam.position.x * 1.4, y: cam.position.y * 1.4, z: cam.position.z * 1.4 },
          undefined,
          350
        )
      }
    }
  }, [])

  const handleResetView = useCallback(() => {
    if (graphInstanceRef.current) {
      graphInstanceRef.current.zoomToFit(600, 40)
    }
  }, [])

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((v) => !v)
  }, [])

  // Drag handlers with jelly spring-back
  const dragStartRef = useRef<Map<string, { x: number; y: number; z: number }>>(new Map())
  const handleNodeDrag = useCallback((node: any) => {
    if (!dragStartRef.current.has(node.id)) {
      dragStartRef.current.set(node.id, { x: node.x, y: node.y, z: node.z })
    }
  }, [])
  const handleNodeDragEnd = useCallback((node: any) => {
    const start = dragStartRef.current.get(node.id)
    node.fx = undefined
    node.fy = undefined
    node.fz = undefined
    if (start) {
      node.vx = (start.x - node.x) * 0.18
      node.vy = (start.y - node.y) * 0.18
      node.vz = (start.z - node.z) * 0.18
      dragStartRef.current.delete(node.id)
    }
    try {
      graphInstanceRef.current?.d3ReheatSimulation?.(0.5)
    } catch {}
  }, [])

  const handleToggleNodeMotion = useCallback((on: boolean) => {
    setNodeMotion(on)
    try {
      if (on) graphInstanceRef.current?.d3ReheatSimulation?.(0.3)
      else graphInstanceRef.current?.d3ReheatSimulation?.(0)
    } catch {}
  }, [])

  // Auto-rotate effect
  useEffect(() => {
    try {
      const controls = graphInstanceRef.current?.controls?.()
      if (controls) {
        controls.autoRotate = true
        controls.autoRotateSpeed = autoRotateSpeed
      }
    } catch {}
  }, [autoRotateSpeed])

  // Update particles and node size dynamically
  useEffect(() => {
    if (graphInstanceRef.current) {
      graphInstanceRef.current
        .nodeRelSize(customNodeSize)
        .linkDirectionalParticles(particleCount)
        .linkDirectionalParticleSpeed(particleSpeed)
    }
  }, [customNodeSize, particleCount, particleSpeed])

  // Resize observer for canvas area
  useEffect(() => {
    if (!canvasAreaRef.current) return
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          setDimensions({ width, height })
          if (graphInstanceRef.current) {
            graphInstanceRef.current.width(width).height(height)
          }
        }
      }
    })
    observer.observe(canvasAreaRef.current)
    return () => observer.disconnect()
  }, [])

  // Filter nodes & links
  const effectiveNodes = useMemo(() => {
    let result = nodes
    if (timeRange !== 'all') {
      const now = Date.now()
      const limits: Record<string, number> = {
        '24h': 24 * 3600 * 1000,
        '7d': 7 * 24 * 3600 * 1000,
        '30d': 30 * 24 * 3600 * 1000,
      }
      const limit = limits[timeRange]
      result = result.filter((n) => {
        const ts = getNodeTimestamp(n)
        return ts > 0 && now - ts <= limit
      })
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (n) =>
          n.label?.toLowerCase().includes(q) ||
          n.id.toLowerCase().includes(q) ||
          n.snippet?.toLowerCase().includes(q) ||
          n.tags?.some((t) => t.toLowerCase().includes(q))
      )
    }
    return result
  }, [nodes, timeRange, searchQuery])

  const effectiveNodeIds = useMemo(() => new Set(effectiveNodes.map((n) => n.id)), [effectiveNodes])

  const effectiveLinks = useMemo(() => {
    return links.filter((l) => {
      const sId = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source
      const tId = typeof l.target === 'object' ? (l.target as GraphNode).id : l.target
      return effectiveNodeIds.has(sId as string) && effectiveNodeIds.has(tId as string)
    })
  }, [links, effectiveNodeIds])

  // Compute node degrees
  const nodeDegrees = useMemo(() => {
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

    adjacencyMapRef.current = adj
    return deg
  }, [effectiveNodes, effectiveLinks])

  // --- INITIALIZE 3D FORCE GRAPH ---
  useEffect(() => {
    if (viewMode !== 'graph' || !canvasAreaRef.current) return
    if (graphInstanceRef.current) return

    canvasAreaRef.current.innerHTML = ''

    const initialWidth = dimensions.width || canvasAreaRef.current.clientWidth || 800
    const initialHeight = dimensions.height || canvasAreaRef.current.clientHeight || 600

    try {
      const GraphCreator = (ForceGraph3D as any).default || ForceGraph3D
      let Graph: any
      try {
        Graph = new GraphCreator(canvasAreaRef.current, { controlType: 'orbit' })
      } catch (e) {
        Graph = GraphCreator({ controlType: 'orbit' })(canvasAreaRef.current)
      }

      Graph
        .width(initialWidth)
        .height(initialHeight)
        .backgroundColor('#000000')
        .showNavInfo(false)
        .nodeRelSize(nodeSize)
        .enableNodeDrag(true)
        .onNodeDrag(handleNodeDrag)
        .onNodeDragEnd(handleNodeDragEnd)
        .linkDirectionalParticles(particleCount)
        .linkDirectionalParticleSpeed(particleSpeed)
        .linkDirectionalParticleWidth(1.5)
        .linkDirectionalParticleColor(() => '#38bdf8')
        .nodeVal((node: any) => {
          const degree = nodeDegrees.get(node.id) || 0
          return Math.max(2, Math.min(8, 2 + Math.sqrt(degree) * 0.9))
        })
        .nodeColor((node: any) => {
          if (node.id === selectedNodeIdRef.current) return '#f59e0b'
          if (hoverNodeRef.current) {
            if (highlightNodesRef.current.has(node.id)) {
              return node.color || (node.category === 'tag' ? '#c084fc' : '#38bdf8')
            }
            return 'rgba(255, 255, 255, 0.12)'
          }
          if (node.color) return node.color
          if (node.category === 'tag') return '#a78bfa'
          return '#38bdf8'
        })
        .nodeThreeObject((node: any) => {
          if (!node.__sprite) {
            const SpriteCls = (SpriteText as any).default || SpriteText
            const sprite = new SpriteCls(node.label || node.id)
            sprite.textHeight = 3.0
            sprite.padding = 2
            sprite.color = node.category === 'tag' ? '#c084fc' : '#e2e8f0'
            sprite.backgroundColor = 'rgba(12, 14, 21, 0.85)'
            sprite.borderColor = 'rgba(56, 189, 248, 0.3)'
            sprite.borderWidth = 0.5
            sprite.borderRadius = 3
            sprite.material.depthWrite = false
            node.__sprite = sprite
          }
          return node.__sprite
        })
        .nodeThreeObjectExtend(true)
        .linkColor((link: any) => {
          const sId = typeof link.source === 'object' ? link.source.id : link.source
          const tId = typeof link.target === 'object' ? link.target.id : link.target
          const hId = hoverNodeRef.current?.id
          const selId = selectedNodeIdRef.current
          if (hId && (sId === hId || tId === hId)) return '#38bdf8'
          if (selId && (sId === selId || tId === selId)) return '#f59e0b'
          return 'rgba(56, 189, 248, 0.25)'
        })
        .linkWidth((link: any) => {
          const sId = typeof link.source === 'object' ? link.source.id : link.source
          const tId = typeof link.target === 'object' ? link.target.id : link.target
          const hId = hoverNodeRef.current?.id
          const selId = selectedNodeIdRef.current
          if ((hId && (sId === hId || tId === hId)) || (selId && (sId === selId || tId === selId))) return 2.5
          return 1
        })
        .onNodeClick((node: any) => {
          onSelectNode(node)
          if (node && typeof node.x === 'number' && typeof node.y === 'number' && typeof node.z === 'number') {
            const distance = 40
            const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z)
            Graph.cameraPosition(
              { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
              { x: node.x, y: node.y, z: node.z },
              1000
            )
          }
        })
        .onNodeHover((node: any) => {
          hoverNodeRef.current = node || null
          const highlight = new Set<string>()
          if (node) {
            highlight.add(node.id)
            const neighbors = adjacencyMapRef.current.get(node.id)
            if (neighbors) {
              neighbors.forEach((nId) => highlight.add(nId))
            }
          }
          highlightNodesRef.current = highlight
        })

      Graph.graphData({ nodes: effectiveNodes, links: effectiveLinks })
      graphInstanceRef.current = Graph
    } catch (err) {
      console.error('Failed to initialize 3D force graph:', err)
    }

    return () => {
      if (graphInstanceRef.current && typeof graphInstanceRef.current._destructor === 'function') {
        try {
          graphInstanceRef.current._destructor()
        } catch {}
      }
      graphInstanceRef.current = null
      if (canvasAreaRef.current) {
        canvasAreaRef.current.innerHTML = ''
      }
    }
  }, [viewMode])

  // Update graph data when effectiveNodes or effectiveLinks change
  useEffect(() => {
    if (viewMode === 'graph' && graphInstanceRef.current) {
      graphInstanceRef.current.graphData({ nodes: effectiveNodes, links: effectiveLinks })
    }
  }, [effectiveNodes, effectiveLinks, viewMode])

  return (
    <div className={`flex flex-col w-full bg-[var(--background)] text-[var(--foreground)] overflow-hidden ${isFullscreen ? 'fixed inset-0 z-50 h-screen rounded-none' : 'h-full flex-1'}`}>
      {/* Top Controls Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-[var(--border)] bg-[var(--card)]/90 backdrop-blur-md shrink-0 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex items-center bg-[var(--input)]/80 p-0.5 rounded-lg border border-[var(--border)]">
            <button
              type="button"
              onClick={() => setViewMode('graph')}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                viewMode === 'graph'
                  ? 'bg-[var(--primary)] text-[var(--primary-foreground)] shadow-xs'
                  : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
              }`}
            >
              3D Graph
            </button>
            <button
              type="button"
              onClick={() => setViewMode('timeline')}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                viewMode === 'timeline'
                  ? 'bg-[var(--primary)] text-[var(--primary-foreground)] shadow-xs'
                  : 'text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
              }`}
            >
              Timeline Feed
            </button>
          </div>

          {/* Search box */}
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)] pointer-events-none" />
            <Input
              placeholder="Search notes, directives, or tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 text-xs pl-8 bg-[var(--input)]/60 border-[var(--border)] rounded-lg placeholder:text-[var(--muted-foreground)]/60"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Right action controls */}
        <div className="flex items-center gap-2">
          {viewMode === 'graph' && (
            <div className="flex items-center gap-1 bg-[var(--input)]/60 border border-[var(--border)] p-0.5 rounded-lg">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleZoomIn}
                className="h-7 w-7 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleZoomOut}
                className="h-7 w-7 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleResetView}
                className="h-7 w-7 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                title="Fit to Screen (Center)"
              >
                <Focus className="w-3.5 h-3.5" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleToggleFullscreen}
                className="h-7 w-7 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
              >
                {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setShowAnimControls((v) => !v)}
                className={`h-7 w-7 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)] ${showAnimControls ? 'text-[var(--primary)]' : ''}`}
                title="Animation & Physics Controls"
              >
                <SlidersHorizontal className="w-3.5 h-3.5" />
              </Button>
            </div>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isLoading}
            className="h-8 px-2.5 text-xs gap-1.5 bg-[var(--input)]/60 border-[var(--border)] hover:bg-[var(--secondary)]"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </Button>
          <Badge variant="secondary" size="sm" className="font-mono text-xs">
            {effectiveNodes.length} / {nodes.length} NOTES
          </Badge>
        </div>
      </div>

      {/* Sub-toolbar: Time Filter Range */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border)] bg-[var(--card)]/80 backdrop-blur-md shrink-0 text-xs flex-wrap gap-2">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--muted-foreground)] flex items-center gap-1 font-semibold">
            <Clock className="w-3 h-3 text-[var(--accent)]" />
            Time:
          </span>
          {(['all', '24h', '7d', '30d'] as const).map((range) => (
            <button
              key={range}
              type="button"
              onClick={() => setTimeRange(range)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                timeRange === range
                  ? 'bg-[var(--primary)] text-[var(--primary-foreground)]'
                  : 'bg-[var(--input)]/60 text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-[var(--border)]'
              }`}
            >
              {range === 'all' ? 'All Time' : range === '24h' ? 'Past 24h' : range === '7d' ? 'Past 7 Days' : 'Past 30 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* Main View Area: 3D Force Graph or Timeline Feed */}
      <div className="flex-1 min-h-0 relative bg-[var(--background)] overflow-hidden">
        <div
          ref={canvasAreaRef}
          className={`absolute inset-0 w-full h-full cursor-grab active:cursor-grabbing bg-[var(--background)] ${
            viewMode === 'graph' ? 'block' : 'hidden'
          }`}
        />
        {viewMode === 'graph' && showAnimControls && (
          <div className="absolute bottom-3 left-3 z-20 bg-[var(--card)]/95 border border-[var(--border)] rounded-xl p-3 w-64 text-xs text-[var(--foreground)] shadow-lg space-y-2.5 max-h-[70vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <span className="text-[var(--muted-foreground)]">Auto-rotate</span>
              <input type="range" min={0} max={2} step={0.1} value={autoRotateSpeed} onChange={(e) => setAutoRotateSpeed(Number(e.target.value))} className="w-28 accent-[var(--primary)]" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--muted-foreground)]">Particle flow</span>
              <input type="range" min={0} max={0.02} step={0.001} value={particleSpeed} onChange={(e) => setParticleSpeed(Number(e.target.value))} className="w-28 accent-[var(--primary)]" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--muted-foreground)]">Particle count</span>
              <input type="range" min={0} max={6} step={1} value={particleCount} onChange={(e) => setParticleCount(Number(e.target.value))} className="w-28 accent-[var(--primary)]" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--muted-foreground)]">Node size</span>
              <input type="range" min={1} max={8} step={0.5} value={customNodeSize} onChange={(e) => setCustomNodeSize(Number(e.target.value))} className="w-28 accent-[var(--primary)]" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--muted-foreground)]">Charge</span>
              <input type="range" min={-200} max={0} step={5} value={chargeStrength} onChange={(e) => {
                const val = Number(e.target.value)
                setChargeStrength(val)
                try { graphInstanceRef.current?.d3Force('charge')?.strength(val); graphInstanceRef.current?.d3ReheatSimulation?.(0.3) } catch {}
              }} className="w-28 accent-[var(--primary)]" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--muted-foreground)]">Link distance</span>
              <input type="range" min={30} max={200} step={5} value={linkDistance} onChange={(e) => {
                const val = Number(e.target.value)
                setLinkDistance(val)
                try { graphInstanceRef.current?.d3Force('link')?.distance(val); graphInstanceRef.current?.d3ReheatSimulation?.(0.3) } catch {}
              }} className="w-28 accent-[var(--primary)]" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--muted-foreground)]">Node motion</span>
              <button
                type="button"
                onClick={() => handleToggleNodeMotion(!nodeMotion)}
                className={`px-2 py-0.5 rounded-md text-[11px] font-medium border ${
                  nodeMotion ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]' : 'bg-[var(--input)] text-[var(--muted-foreground)] border-[var(--border)]'
                }`}
              >
                {nodeMotion ? 'On' : 'Off'}
              </button>
            </div>
          </div>
        )}
        {viewMode === 'timeline' && (
          <div className="absolute inset-0 overflow-y-auto p-4 space-y-3 bg-[var(--background)] z-10">
            {effectiveNodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-center text-[var(--muted-foreground)]">
                <Sparkles className="w-8 h-8 opacity-30 mb-2" />
                <div className="text-xs font-semibold text-[var(--foreground)]">No memories matched filter</div>
                <div className="text-[10px] font-mono mt-1">Try switching time range or search query.</div>
              </div>
            ) : (
              effectiveNodes
                .slice()
                .sort((a, b) => {
                  const ta = getNodeTimestamp(a)
                  const tb = getNodeTimestamp(b)
                  return tb - ta
                })
                .map((node) => (
                  <div
                    key={node.id}
                    onClick={() => onSelectNode(node)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer bg-[var(--card)] hover:border-[var(--primary)] group relative ${
                      selectedNodeId === node.id ? 'border-[var(--primary)] ring-1 ring-[var(--primary)]/40 bg-[var(--primary)]/10' : 'border-[var(--border)]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-xs font-bold text-[var(--foreground)] tracking-tight">{node.label}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-[var(--muted-foreground)]">
                          {formatNodeDateTime(node)}
                        </span>
                        <button
                          type="button"
                          title="Delete memory note"
                          onClick={async (e) => {
                            e.stopPropagation()
                            if (window.confirm(`Are you sure you want to delete memory "${node.label}"?`)) {
                              try {
                                await api.deleteMemoryNote(node.file || node.id)
                                onRefresh()
                              } catch (err) {
                                console.error('Failed to delete memory note:', err)
                              }
                            }
                          }}
                          className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors opacity-60 group-hover:opacity-100"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    {node.snippet && (
                      <p className="text-xs text-[var(--muted-foreground)] line-clamp-2 mt-1 font-mono leading-relaxed">
                        {node.snippet}
                      </p>
                    )}
                    {node.tags && node.tags.length > 0 && (
                      <div className="flex items-center gap-1 mt-2 flex-wrap">
                        {node.tags.map((t, idx) => (
                          <span
                            key={idx}
                            className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[var(--input)] text-[var(--muted-foreground)] border border-[var(--border)]"
                          >
                            #{t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
            )}
          </div>
        )}
      </div>
    </div>
  )
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
