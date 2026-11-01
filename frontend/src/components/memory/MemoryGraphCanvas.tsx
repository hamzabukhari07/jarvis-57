import React, { useRef, useEffect, useState, useMemo, useCallback } from 'react'
import ForceGraph3D from '3d-force-graph'
import SpriteText from 'three-spritetext'
import * as THREE from 'three'
import {
  RefreshCw,
  Search,
  Sparkles,
  Clock,
  X,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react'
import { Badge } from '../reui/badge'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { ConfirmDialog } from '../reui/confirm-dialog'
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
  turn_count?: number
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
  __sprite?: any
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
  const [autoRotateSpeed, setAutoRotateSpeed] = useState(0.4)
  const [particleSpeed, setParticleSpeed] = useState(0.006)
  const [particleCount, setParticleCount] = useState(2)
  const [customNodeSize, setCustomNodeSize] = useState(4.5)
  const [chargeStrength, setChargeStrength] = useState(-75)
  const [linkDistance, setLinkDistance] = useState(85)
  const [nodeMotion, setNodeMotion] = useState(true)
  const nodeSize = customNodeSize

  // ReUI Delete Confirmation State for Timeline View
  const [nodeToDelete, setNodeToDelete] = useState<GraphNode | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const selectedNodeIdRef = useRef(selectedNodeId)
  selectedNodeIdRef.current = selectedNodeId

  const searchQueryRef = useRef(searchQuery)
  searchQueryRef.current = searchQuery

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

  // Filter nodes & links by timeRange (search query is used for visual dimming, preserving 3D galaxy structure)
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
    return result
  }, [nodes, timeRange])

  // For timeline view, we filter nodes by both time and search query
  const timelineFilteredNodes = useMemo(() => {
    let result = effectiveNodes
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim()
      result = result.filter(
        (n) =>
          n.label?.toLowerCase().includes(q) ||
          n.id.toLowerCase().includes(q) ||
          n.snippet?.toLowerCase().includes(q) ||
          n.tags?.some((t) => t.toLowerCase().includes(q))
      )
    }
    return result
  }, [effectiveNodes, searchQuery])

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

  // Helper: check if a node matches current search query
  const checkNodeMatchesSearch = useCallback((node: any, query: string): boolean => {
    if (!query.trim()) return true
    const q = query.toLowerCase().trim()
    return Boolean(
      node.label?.toLowerCase().includes(q) ||
        node.id?.toLowerCase().includes(q) ||
        node.snippet?.toLowerCase().includes(q) ||
        node.tags?.some((t: string) => t.toLowerCase().includes(q))
    )
  }, [])

  // --- INITIALIZE 3D FORCE GRAPH (KNOWLEDGE GALAXY AESTHETIC) ---
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
        .backgroundColor('#05050d')
        .showNavInfo(false)
        .nodeRelSize(nodeSize)
        .enableNodeDrag(true)
        .onNodeDrag(handleNodeDrag)
        .onNodeDragEnd(handleNodeDragEnd)
        .linkDirectionalParticles(particleCount)
        .linkDirectionalParticleSpeed(particleSpeed)
        .linkDirectionalParticleWidth(1.2)
        .linkDirectionalParticleColor(() => '#818cf8')
        .nodeVal((node: any) => {
          const degree = nodeDegrees.get(node.id) || 0
          return Math.max(2.5, Math.min(8.5, 2.5 + Math.sqrt(degree) * 0.9))
        })
        .nodeColor((node: any) => {
          const query = searchQueryRef.current
          const isMatch = checkNodeMatchesSearch(node, query)

          if (!isMatch) {
            return 'rgba(255, 255, 255, 0.08)'
          }

          if (node.id === selectedNodeIdRef.current) return '#f59e0b'
          if (hoverNodeRef.current) {
            if (highlightNodesRef.current.has(node.id)) {
              return node.color || (node.category === 'tag' ? '#c084fc' : '#38bdf8')
            }
            return 'rgba(255, 255, 255, 0.15)'
          }
          if (node.color) return node.color
          if (node.category === 'tag') return '#a78bfa'
          return '#38bdf8'
        })
        .nodeThreeObject((node: any) => {
          if (!node.__sprite) {
            const SpriteCls = (SpriteText as any).default || SpriteText
            const sprite = new SpriteCls(node.label || node.id)
            sprite.textHeight = 2.8
            sprite.padding = 2.5
            sprite.color = node.category === 'tag' ? '#c084fc' : '#e2e8f0'
            sprite.backgroundColor = 'rgba(10, 10, 20, 0.88)'
            sprite.borderColor = 'rgba(129, 140, 248, 0.35)'
            sprite.borderWidth = 0.6
            sprite.borderRadius = 4
            sprite.material.depthWrite = false
            sprite.material.transparent = true
            sprite.material.opacity = 1.0
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
          if (hId && (sId === hId || tId === hId)) return '#818cf8'
          if (selId && (sId === selId || tId === selId)) return '#f59e0b'
          return 'rgba(120, 120, 255, 0.35)'
        })
        .linkWidth((link: any) => {
          const sId = typeof link.source === 'object' ? link.source.id : link.source
          const tId = typeof link.target === 'object' ? link.target.id : link.target
          const hId = hoverNodeRef.current?.id
          const selId = selectedNodeIdRef.current
          if ((hId && (sId === hId || tId === hId)) || (selId && (sId === selId || tId === selId))) return 2.2
          return 0.9
        })
        .onNodeClick((node: any) => {
          onSelectNode(node)
          if (node && typeof node.x === 'number' && typeof node.y === 'number' && typeof node.z === 'number') {
            const dist = 70
            const r = Math.hypot(node.x, node.y, node.z) || 1
            const ratio = 1 + dist / r
            Graph.cameraPosition(
              { x: node.x * ratio, y: node.y * ratio, z: node.z * ratio },
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

      // --- ADD 1,200 STAR CELESTIAL PARTICLE FIELD (KNOWLEDGE GALAXY DEPTH) ---
      const scene = Graph.scene?.()
      const ThreeLib = (window as any).THREE || THREE
      if (scene && ThreeLib) {
        const starGeo = new ThreeLib.BufferGeometry()
        const count = 1200
        const positions = new Float32Array(count * 3)
        for (let i = 0; i < count; i++) {
          const r = 700 + Math.random() * 1300
          const theta = Math.random() * Math.PI * 2
          const phi = Math.acos(2 * Math.random() - 1)
          positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
          positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
          positions[i * 3 + 2] = r * Math.cos(phi)
        }
        starGeo.setAttribute('position', new ThreeLib.BufferAttribute(positions, 3))
        const starsMaterial = new ThreeLib.PointsMaterial({
          color: 0xc7d2fe,
          size: 1.8,
          transparent: true,
          opacity: 0.65,
        })
        const starPoints = new ThreeLib.Points(starGeo, starsMaterial)
        scene.add(starPoints)
      }

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

  // --- TWEAK 2: REACTIVE 3D SEARCH DIMMING ---
  // Dynamically update sprite text opacity and refresh node colors without re-instantiating WebGL scene
  useEffect(() => {
    if (viewMode !== 'graph' || !graphInstanceRef.current) return

    const query = searchQuery.trim().toLowerCase()
    const graphData = graphInstanceRef.current.graphData?.()
    if (graphData && Array.isArray(graphData.nodes)) {
      graphData.nodes.forEach((n: any) => {
        const isMatch = checkNodeMatchesSearch(n, query)
        if (n.__sprite && n.__sprite.material) {
          n.__sprite.material.transparent = true
          n.__sprite.material.opacity = isMatch ? 1.0 : 0.08
        }
      })
    }

    // Trigger re-evaluation of nodeColor accessor
    try {
      graphInstanceRef.current.nodeColor(graphInstanceRef.current.nodeColor())
    } catch {}
  }, [searchQuery, viewMode, checkNodeMatchesSearch])

  // Handle timeline note deletion with ReUI ConfirmDialog
  const handleConfirmDeleteNote = async () => {
    if (!nodeToDelete) return
    setIsDeleting(true)
    try {
      await api.deleteMemoryNote(nodeToDelete.file || nodeToDelete.id)
      setNodeToDelete(null)
      onRefresh()
    } catch (err) {
      console.error('Failed to delete memory note:', err)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div
      className={`flex flex-col w-full bg-[#05050d] text-foreground overflow-hidden ${
        isFullscreen ? 'fixed inset-0 z-50 h-screen rounded-none' : 'h-full flex-1'
      }`}
    >
      {/* Top Floating HUD Controls */}
      <div className="flex items-center justify-between p-3 border-b border-[rgba(120,120,255,0.18)] bg-[#0a0a16]/85 backdrop-blur-xl shrink-0 flex-wrap gap-2 z-20">
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex items-center bg-[#101026]/90 p-0.5 rounded-xl border border-[rgba(120,120,255,0.2)]">
            <button
              type="button"
              onClick={() => setViewMode('graph')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all font-mono ${
                viewMode === 'graph'
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              3D Galaxy
            </button>
            <button
              type="button"
              onClick={() => setViewMode('timeline')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all font-mono ${
                viewMode === 'timeline'
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Timeline Feed
            </button>
          </div>

          {/* Search box */}
          <div className="relative w-64 md:w-72">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
            <Input
              placeholder="Search galaxy notes or directives..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 text-xs pl-8 pr-8 bg-[#101026]/90 border-[rgba(120,120,255,0.25)] rounded-xl placeholder:text-muted-foreground/60 font-mono focus:border-primary"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Right action controls */}
        <div className="flex items-center gap-2">
          {viewMode === 'graph' && (
            <div className="flex items-center gap-1 bg-[#101026]/80 border border-[rgba(120,120,255,0.2)] p-0.5 rounded-xl">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleZoomIn}
                className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleZoomOut}
                className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleToggleFullscreen}
                className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen Galaxy'}
              >
                {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setShowAnimControls((v) => !v)}
                className={`h-7 w-7 p-0 text-muted-foreground hover:text-foreground ${
                  showAnimControls ? 'text-primary' : ''
                }`}
                title="Galaxy Dynamics & Physics"
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
            className="h-8 px-2.5 text-xs gap-1.5 bg-[#101026]/80 border-[rgba(120,120,255,0.25)] hover:bg-[rgba(120,120,255,0.15)] font-mono"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </Button>
          <Badge
            variant="secondary"
            size="sm"
            className="font-mono text-xs bg-[rgba(120,120,255,0.12)] border border-[rgba(120,120,255,0.25)] text-foreground"
          >
            {timelineFilteredNodes.length} / {nodes.length} STARS
          </Badge>
        </div>
      </div>

      {/* Sub-toolbar: Time Filter Range */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[rgba(120,120,255,0.12)] bg-[#0a0a16]/70 backdrop-blur-md shrink-0 text-xs flex-wrap gap-2 z-10">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-1 font-semibold">
            <Clock className="w-3 h-3 text-primary" />
            Time:
          </span>
          {(['all', '24h', '7d', '30d'] as const).map((range) => (
            <button
              key={range}
              type="button"
              onClick={() => setTimeRange(range)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-mono transition-colors ${
                timeRange === range
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'bg-[#101026]/70 text-muted-foreground hover:text-foreground border border-[rgba(120,120,255,0.2)]'
              }`}
            >
              {range === 'all' ? 'All Time' : range === '24h' ? 'Past 24h' : range === '7d' ? 'Past 7 Days' : 'Past 30 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* Main View Area: 3D Force Graph or Timeline Feed */}
      <div className="flex-1 min-h-0 relative bg-[#05050d] overflow-hidden">
        <div
          ref={canvasAreaRef}
          className={`absolute inset-0 w-full h-full cursor-grab active:cursor-grabbing bg-[#05050d] ${
            viewMode === 'graph' ? 'block' : 'hidden'
          }`}
        />
        {viewMode === 'graph' && showAnimControls && (
          <div className="absolute bottom-3 left-3 z-30 bg-[#0c0c1c]/95 border border-[rgba(120,120,255,0.25)] backdrop-blur-xl rounded-2xl p-3 w-64 text-xs text-foreground shadow-2xl space-y-2.5 max-h-[70vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-mono">Auto-rotate</span>
              <input
                type="range"
                min={0}
                max={2}
                step={0.1}
                value={autoRotateSpeed}
                onChange={(e) => setAutoRotateSpeed(Number(e.target.value))}
                className="w-28 accent-primary"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-mono">Particle flow</span>
              <input
                type="range"
                min={0}
                max={0.02}
                step={0.001}
                value={particleSpeed}
                onChange={(e) => setParticleSpeed(Number(e.target.value))}
                className="w-28 accent-primary"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-mono">Particle count</span>
              <input
                type="range"
                min={0}
                max={6}
                step={1}
                value={particleCount}
                onChange={(e) => setParticleCount(Number(e.target.value))}
                className="w-28 accent-primary"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-mono">Node size</span>
              <input
                type="range"
                min={1}
                max={8}
                step={0.5}
                value={customNodeSize}
                onChange={(e) => setCustomNodeSize(Number(e.target.value))}
                className="w-28 accent-primary"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-mono">Charge</span>
              <input
                type="range"
                min={-200}
                max={0}
                step={5}
                value={chargeStrength}
                onChange={(e) => {
                  const val = Number(e.target.value)
                  setChargeStrength(val)
                  try {
                    graphInstanceRef.current?.d3Force('charge')?.strength(val)
                    graphInstanceRef.current?.d3ReheatSimulation?.(0.3)
                  } catch {}
                }}
                className="w-28 accent-primary"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-mono">Link distance</span>
              <input
                type="range"
                min={30}
                max={200}
                step={5}
                value={linkDistance}
                onChange={(e) => {
                  const val = Number(e.target.value)
                  setLinkDistance(val)
                  try {
                    graphInstanceRef.current?.d3Force('link')?.distance(val)
                    graphInstanceRef.current?.d3ReheatSimulation?.(0.3)
                  } catch {}
                }}
                className="w-28 accent-primary"
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground font-mono">Node motion</span>
              <button
                type="button"
                onClick={() => handleToggleNodeMotion(!nodeMotion)}
                className={`px-2 py-0.5 rounded-md text-[11px] font-mono border ${
                  nodeMotion
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-[#101026] text-muted-foreground border-[rgba(120,120,255,0.2)]'
                }`}
              >
                {nodeMotion ? 'On' : 'Off'}
              </button>
            </div>
          </div>
        )}

        {/* Timeline Feed View */}
        {viewMode === 'timeline' && (
          <div className="absolute inset-0 overflow-y-auto p-4 space-y-3 bg-[#05050d] z-10">
            {timelineFilteredNodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-center text-muted-foreground">
                <Sparkles className="w-8 h-8 opacity-40 mb-2 text-primary" />
                <div className="text-xs font-semibold text-foreground font-mono">No galaxy memories matched filter</div>
                <div className="text-[10px] font-mono mt-1">Try switching time range or modifying your search query.</div>
              </div>
            ) : (
              timelineFilteredNodes
                .slice()
                .sort((a, b) => {
                  const ta = getNodeTimestamp(a)
                  const tb = getNodeTimestamp(b)
                  return tb - ta
                })
                .map((node) => {
                  // Filter out internal system metadata
                  const displayTags = (node.tags || []).filter((t: string) => {
                    const lower = String(t).toLowerCase()
                    return !lower.endsWith('_turns') && lower !== 'conversation' && lower !== 'memory'
                  })

                  // Turn count resolution
                  const turnCount =
                    typeof node.turn_count === 'number' && node.turn_count > 0
                      ? node.turn_count
                      : (() => {
                          for (const t of node.tags || []) {
                            const m = String(t).match(/^(\d+)_turns$/i)
                            if (m) return parseInt(m[1], 10)
                          }
                          return null
                        })()

                  return (
                    <div
                      key={node.id}
                      onClick={() => onSelectNode(node)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer bg-[#0a0a16]/90 hover:border-primary/60 group relative ${
                        selectedNodeId === node.id
                          ? 'border-primary ring-1 ring-primary/40 bg-primary/10'
                          : 'border-[rgba(120,120,255,0.18)]'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <div className="flex items-center gap-2 truncate">
                          <span
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: node.color || '#38bdf8' }}
                          />
                          <span className="text-xs font-bold text-foreground tracking-tight font-mono truncate">
                            {node.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {formatNodeDateTime(node)}
                            {turnCount !== null ? ` • ${turnCount} ${turnCount === 1 ? 'turn' : 'turns'}` : ''}
                          </span>
                          <button
                            type="button"
                            title="Delete memory note"
                            onClick={(e) => {
                              e.stopPropagation()
                              setNodeToDelete(node)
                            }}
                            className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors opacity-60 group-hover:opacity-100"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                      {node.snippet && (
                        <p className="text-xs text-muted-foreground line-clamp-2 mt-1 font-sans leading-relaxed">
                          {node.snippet}
                        </p>
                      )}
                      {displayTags.length > 0 && (
                        <div className="flex items-center gap-1 mt-2 flex-wrap">
                          {displayTags.map((t, idx) => (
                            <span
                              key={idx}
                              className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[rgba(120,120,255,0.08)] text-muted-foreground border border-[rgba(120,120,255,0.2)]"
                            >
                              #{t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })
            )}
          </div>
        )}
      </div>

      {/* ReUI Confirmation Dialog for Timeline Note Deletion */}
      <ConfirmDialog
        open={Boolean(nodeToDelete)}
        onOpenChange={(open) => {
          if (!open) setNodeToDelete(null)
        }}
        title={`Delete Memory "${nodeToDelete?.label || ''}"?`}
        description="Permanently delete this memory note and its recorded turns from ZEZO Brain?"
        warningText="This action will permanently delete the note from the markdown vault and purge any associated conversation turns from SQLite so it will never reappear."
        confirmText="Delete Permanently"
        cancelText="Cancel"
        variant="destructive"
        isLoading={isDeleting}
        onConfirm={handleConfirmDeleteNote}
      />
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
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  if (node.date) return node.date
  return 'Saved note'
}
