import React, { useRef, useEffect, useState, useMemo, useCallback } from 'react'
import * as d3 from 'd3-force'
import * as d3f3 from 'd3-force-3d'
import ForceGraph3D from 'react-force-graph-3d'
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

export const MemoryGraphCanvas: React.FC<MemoryGraphCanvasProps> = ({
  nodes,
  links,
  selectedNodeId,
  onSelectNode,
  onRefresh,
  isLoading,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const fgRef = useRef<any>(null)

  // Explicit container dimensions via ResizeObserver for precise WebGL centering
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({ width: 0, height: 0 })

  // Search & Interaction states
  const [searchQuery, setSearchQuery] = useState('')
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null)

  // Animation controls
  const [showAnimControls, setShowAnimControls] = useState(false)
  const [autoRotateSpeed, setAutoRotateSpeed] = useState(0.6)
  const [particleSpeed, setParticleSpeed] = useState(0.005)
  const [nodeMotion, setNodeMotion] = useState(true)

  // Graph tuning controls
  const [chargeStrength, setChargeStrength] = useState(-70)
  const [linkDistance, setLinkDistance] = useState(90)
  const [radialRadius, setRadialRadius] = useState(150)
  const [nodeSize, setNodeSize] = useState(3)
  const [particleCount, setParticleCount] = useState(2)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Track container dimensions accurately
  useEffect(() => {
    if (!containerRef.current) return
    const updateSize = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current
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
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  // Auto-refresh when mounted with empty nodes
  useEffect(() => {
    if (nodes.length === 0 && onRefresh) {
      onRefresh()
    }
  }, [nodes.length, onRefresh])

  // ── 1. Adjacency Map & Degree Centrality ──
  const { adjacencyMap, nodeDegrees } = useMemo(() => {
    const adj = new Map<string, Set<string>>()
    const deg = new Map<string, number>()

    nodes.forEach((n) => {
      adj.set(n.id, new Set())
      deg.set(n.id, 0)
    })

    links.forEach((l) => {
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
  }, [nodes, links])

  // ── 2. Hover Spotlight Neighborhood ──
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

  // ── 3. Active Nodes & Links ──
  const effectiveNodes = nodes

  const effectiveNodeIdSet = useMemo(() => new Set(effectiveNodes.map((n) => n.id)), [effectiveNodes])

  const effectiveLinks = useMemo(() => {
    return links.filter((l) => {
      const sId = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source
      const tId = typeof l.target === 'object' ? (l.target as GraphNode).id : l.target
      return effectiveNodeIdSet.has(sId) && effectiveNodeIdSet.has(tId)
    })
  }, [links, effectiveNodeIdSet])

  // ── 4. Search Filter Set ──
  const searchMatchIds = useMemo(() => {
    const q = searchQuery.toLowerCase().trim()
    if (!q) return null
    return new Set(
      effectiveNodes
        .filter(
          (n) =>
            n.label.toLowerCase().includes(q) ||
            n.snippet.toLowerCase().includes(q) ||
            n.tags.some((t) => t.toLowerCase().includes(q))
        )
        .map((n) => n.id)
    )
  }, [effectiveNodes, searchQuery])

  // ── 5. Auto-Center Graph on Load & Spatial Dispersion ──
  useEffect(() => {
    if (!fgRef.current || effectiveNodes.length === 0 || dimensions.width === 0) return
    if (fgRef.current.d3Force) {
      // Smooth Physics: Repulsion kam kiya, Link distance barhayi
      fgRef.current.d3Force('charge')?.strength(chargeStrength) 
      fgRef.current.d3Force('link')?.distance(linkDistance)
      
      // D3 Collision Force
      fgRef.current.d3Force('collide', d3.forceCollide((node: any) => {
         const degree = nodeDegrees.get(node.id) || 0
         return Math.max(1.5, Math.min(6, 1.5 + Math.sqrt(degree) * 0.8)) * 2.5; 
      }))

      // Orbit/Circle shape
      fgRef.current.d3Force('radial', (d3f3 as any).forceRadial(radialRadius).strength(0.06))
    }
    const timer = setTimeout(() => {
      if (fgRef.current) {
        fgRef.current.zoomToFit(600, 40)
        // Slow auto-rotate for orbit feel
        try {
          const controls = fgRef.current.controls()
          if (controls) {
            controls.autoRotate = true
            controls.autoRotateSpeed = autoRotateSpeed
          }
        } catch (e) {
          // ignore
        }
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [dimensions.width, dimensions.height, effectiveNodes.length, nodeDegrees, chargeStrength, linkDistance, radialRadius, autoRotateSpeed])

  const handleResetView = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(600, 40)
    }
  }, [])

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((v) => !v)
  }, [])

  // Jelly spring-back on drag end
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
      fgRef.current?.d3ReheatSimulation?.(0.5)
    } catch {
      // ignore
    }
  }, [])

  const handleZoomIn = useCallback(() => {
    if (fgRef.current) {
      const cam = fgRef.current.camera()
      if (cam) {
        fgRef.current.cameraPosition(
          { x: cam.position.x * 0.7, y: cam.position.y * 0.7, z: cam.position.z * 0.7 },
          undefined,
          350
        )
      }
    }
  }, [])

  const handleZoomOut = useCallback(() => {
    if (fgRef.current) {
      const cam = fgRef.current.camera()
      if (cam) {
        fgRef.current.cameraPosition(
          { x: cam.position.x * 1.4, y: cam.position.y * 1.4, z: cam.position.z * 1.4 },
          undefined,
          350
        )
      }
    }
  }, [])

  // Throttled hover handler to avoid full re-renders on every mouse move
  const lastHoverUpdateRef = useRef(0)
  const pendingHoverRef = useRef<GraphNode | null | undefined>(undefined)
  const hoverTimerRef = useRef<number | null>(null)

  const handleNodeHover = useCallback((node: any) => {
    const next = (node || null) as GraphNode | null
    const now = performance.now()
    if (now - lastHoverUpdateRef.current >= 100) {
      lastHoverUpdateRef.current = now
      setHoverNode(next)
    } else {
      pendingHoverRef.current = next
      if (hoverTimerRef.current === null) {
        const delay = 100 - (now - lastHoverUpdateRef.current)
        hoverTimerRef.current = window.setTimeout(() => {
          hoverTimerRef.current = null
          lastHoverUpdateRef.current = performance.now()
          setHoverNode(pendingHoverRef.current as GraphNode | null)
          pendingHoverRef.current = undefined
        }, delay)
      }
    }
  }, [])

  // Cleanup hover timer on unmount
  useEffect(() => {
    return () => {
      if (hoverTimerRef.current !== null) {
        window.clearTimeout(hoverTimerRef.current)
        hoverTimerRef.current = null
      }
    }
  }, [])

  const graphData = useMemo(() => ({ nodes: effectiveNodes, links: effectiveLinks }), [effectiveNodes, effectiveLinks])

  const getNodeVal = useCallback((node: any) => {
    const degree = nodeDegrees.get(node.id) || 0
    return Math.max(1.5, Math.min(6, 1.5 + Math.sqrt(degree) * 0.8))
  }, [nodeDegrees])

  const getNodeLabel = useCallback((node: any) => `${node.label} (${node.category || 'note'})`, [])
  // ── Animation Control Effects ──
  useEffect(() => {
    try {
      const controls = fgRef.current?.controls?.()
      if (controls) controls.autoRotateSpeed = autoRotateSpeed
    } catch {
      // ignore
    }
  }, [autoRotateSpeed])

  const handleToggleNodeMotion = useCallback((on: boolean) => {
    setNodeMotion(on)
    try {
      if (on) fgRef.current?.d3ReheatSimulation?.(0.3)
      else fgRef.current?.d3ReheatSimulation?.(0)
    } catch {
      // ignore
    }
  }, [])

  // ── 6. Node Click & Focus in 3D Orbit ──
  const handleNodeClick = useCallback(
    (node: any) => {
      const graphNode = node as GraphNode
      onSelectNode(graphNode)
      if (fgRef.current && graphNode.x != null && graphNode.y != null && graphNode.z != null) {
        const distance = 80
        const hyp = Math.max(0.1, Math.hypot(graphNode.x, graphNode.y, graphNode.z))
        const distRatio = 1 + distance / hyp
        fgRef.current.cameraPosition(
          { x: graphNode.x * distRatio, y: graphNode.y * distRatio, z: graphNode.z * distRatio },
          graphNode,
          800
        )
      }
    },
    [onSelectNode]
  )

  // ── 7. Clean Refined Node Colors & Sizing ──
  const getNodeColor = useCallback(
    (node: GraphNode) => {
      // 1. Selected node always Amber
      if (node.id === selectedNodeId) return '#f59e0b' 
      
      // 2. Hover Spotlight
      if (hoverNode) {
        if (highlightNodes.has(node.id)) {
          return node.color || (node.category === 'tag' ? '#c084fc' : '#38bdf8') 
        }
        return 'rgba(255, 255, 255, 0.15)' 
      }
      
      // 3. Search Highlighting (Check this BEFORE defaulting to tag colors)
      if (searchMatchIds !== null) {
        return searchMatchIds.has(node.id) ? '#38bdf8' : 'rgba(255, 255, 255, 0.12)'
      }

      // 4. Selection Spotlight
      if (selectedNodeId && !hoverNode && searchMatchIds === null) {
        if (node.id === selectedNodeId) return '#f59e0b'
        const neighbors = adjacencyMap.get(selectedNodeId)
        if (neighbors && neighbors.has(node.id)) {
          return node.color || (node.category === 'tag' ? '#c084fc' : '#38bdf8')
        }
        return 'rgba(255, 255, 255, 0.2)'
      }

      // 5. Category / Vault Colors (Only if not searching)
      if (node.color) return node.color
      if (node.category === 'tag') return '#a78bfa' 
      
      // 5. Default Note Color
      return '#94a3b8' 
    },
    [selectedNodeId, hoverNode, highlightNodes, searchMatchIds, adjacencyMap]
  )

  // ── 8. Clean Hairline Links (Zero Particles) ──
  const getLinkColor = useCallback(
    (link: any) => {
      const sId = typeof link.source === 'object' ? link.source.id : link.source
      const tId = typeof link.target === 'object' ? link.target.id : link.target

      if (hoverNode) {
        if (sId === hoverNode.id || tId === hoverNode.id) {
          return '#38bdf8' // Active link glow
        }
        return 'rgba(255, 255, 255, 0.08)' // Dim background links
      }

      if (selectedNodeId && (sId === selectedNodeId || tId === selectedNodeId)) {
        return '#f59e0b'
      }

      if (selectedNodeId) {
        return 'rgba(255, 255, 255, 0.06)' // Dim non-connected links when a node is selected
      }

      return 'rgba(255, 255, 255, 0.5)'
    },
    [hoverNode, selectedNodeId]
  )

  const getLinkWidth = useCallback(
    (link: any) => {
      const sId = typeof link.source === 'object' ? link.source.id : link.source
      const tId = typeof link.target === 'object' ? link.target.id : link.target

      if (hoverNode && (sId === hoverNode.id || tId === hoverNode.id)) {
        return 1.6
      }
      if (selectedNodeId && (sId === selectedNodeId || tId === selectedNodeId)) {
        return 2.0
      }
      return 1.2
    },
    [hoverNode, selectedNodeId]
  )

  // ESC exits pseudo-fullscreen
  useEffect(() => {
    if (!isFullscreen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsFullscreen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isFullscreen])

  return (
    <div
      ref={containerRef}
      className={`relative w-full ${isFullscreen ? 'fixed inset-0 z-50 h-screen rounded-none' : 'h-full flex-1 min-h-[420px]'} rounded-2xl bg-[#08090d] border border-border/40 overflow-hidden shadow-2xl flex flex-col select-none`}
    >
      {/* ── Top Floating Navigation & Mode Toolbar ── */}
      <div className="absolute top-3.5 left-3.5 right-3.5 z-10 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        <div className="flex items-center gap-2 pointer-events-auto">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground pointer-events-none" />
            <Input
              placeholder="Search notes or #tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 pr-3 text-xs w-52 md:w-72 bg-[#11131a] border-border/80 rounded-xl shadow-xs focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        <div className="flex items-center gap-1.5 bg-[#11131a] border border-border/80 p-1 rounded-xl pointer-events-auto shadow-sm">
          <Badge variant="outline" className="text-[10px] font-mono h-6 px-2 text-primary border-primary/30 bg-primary/10 gap-1">
            <Sparkles className="w-2.5 h-2.5" />
            <span>{effectiveNodes.length} Nodes</span>
          </Badge>

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
            onClick={handleResetView}
            className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
            title="Fit to Screen (Center)"
          >
            <Focus className="w-3.5 h-3.5" />
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleToggleFullscreen}
            className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            className={`h-7 w-7 p-0 text-muted-foreground hover:text-foreground ${isLoading ? 'animate-spin' : ''}`}
            title="Recalculate Graph"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowAnimControls((v) => !v)}
            className={`h-7 w-7 p-0 text-muted-foreground hover:text-foreground ${showAnimControls ? 'text-primary' : ''}`}
            title="Animation Controls"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* ── PRE-BUILT 3D ORBIT FORCE GRAPH (react-force-graph-3d) ── */}
      <div className="flex-1 w-full h-full">
        {dimensions.width > 0 && dimensions.height > 0 && (
          <ForceGraph3D
            ref={fgRef}
            width={dimensions.width}
            height={dimensions.height}
            graphData={graphData}
            backgroundColor="#08090d"
            controlType="orbit"
            showNavInfo={false}
            
            // Clean, small, elegant spheres (not bloated)
            nodeRelSize={nodeSize}
            nodeResolution={20}
            nodeOpacity={1}
            nodeColor={getNodeColor}
            nodeVal={getNodeVal}
            nodeLabel={getNodeLabel}

            // Hairline clean links, ZERO particles
            linkColor={getLinkColor}
            linkWidth={getLinkWidth}
            linkDirectionalParticles={particleCount}
            linkDirectionalParticleSpeed={particleSpeed}
            linkDirectionalParticleWidth={1.5}
            linkDirectionalParticleColor={() => '#38bdf8'}
            linkResolution={4}

            // 3D Orbit & Interaction Controls
            enableNodeDrag={true}
            onNodeClick={handleNodeClick}
            onNodeHover={handleNodeHover}
            onNodeDrag={handleNodeDrag}
            onNodeDragEnd={handleNodeDragEnd}
            onBackgroundClick={() => onSelectNode(null)}
            
            // Performance & calm settling + continuous slow motion
            warmupTicks={60}
            cooldownTicks={Infinity}
            cooldownTime={Infinity}
            d3AlphaDecay={0.02}
            d3AlphaMin={0.001}
          />
        )}
      </div>

      {/* Animation Controls Panel */}
      {showAnimControls && (
        <div className="absolute bottom-3 left-3 z-20 bg-[#11131a]/95 border border-border/80 rounded-xl p-3 w-64 text-xs text-foreground shadow-lg space-y-2.5 max-h-[70vh] overflow-y-auto">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Auto-rotate</span>
            <input type="range" min={0} max={2} step={0.1} value={autoRotateSpeed} onChange={(e) => setAutoRotateSpeed(Number(e.target.value))} className="w-28" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Particle flow</span>
            <input type="range" min={0} max={0.02} step={0.001} value={particleSpeed} onChange={(e) => setParticleSpeed(Number(e.target.value))} className="w-28" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Particle count</span>
            <input type="range" min={0} max={6} step={1} value={particleCount} onChange={(e) => setParticleCount(Number(e.target.value))} className="w-28" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Node size</span>
            <input type="range" min={1} max={8} step={0.5} value={nodeSize} onChange={(e) => setNodeSize(Number(e.target.value))} className="w-28" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Charge</span>
            <input type="range" min={-200} max={0} step={5} value={chargeStrength} onChange={(e) => setChargeStrength(Number(e.target.value))} className="w-28" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Link distance</span>
            <input type="range" min={30} max={200} step={5} value={linkDistance} onChange={(e) => setLinkDistance(Number(e.target.value))} className="w-28" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Orbit radius</span>
            <input type="range" min={50} max={300} step={10} value={radialRadius} onChange={(e) => setRadialRadius(Number(e.target.value))} className="w-28" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Node motion</span>
            <button
              type="button"
              onClick={() => handleToggleNodeMotion(!nodeMotion)}
              className={`px-2 py-0.5 rounded-md text-[11px] font-medium border ${
                nodeMotion ? 'bg-primary text-primary-foreground border-primary' : 'bg-muted text-muted-foreground border-border'
              }`}
            >
              {nodeMotion ? 'On' : 'Off'}
            </button>
          </div>
        </div>
      )}

      {/* Loading / Empty State */}
      {effectiveNodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 pointer-events-none text-muted-foreground bg-[#08090d]/85">
          {isLoading ? (
            <>
              <RefreshCw className="w-5 h-5 animate-spin text-primary" />
              <span className="text-xs font-mono">Loading memory graph…</span>
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5 text-primary/60" />
              <span className="text-xs font-mono">No memory nodes yet. Add a note to begin.</span>
            </>
          )}
        </div>
      )}
    </div>
  )
}
