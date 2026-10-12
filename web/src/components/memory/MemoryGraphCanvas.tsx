import React, { useRef, useEffect, useState, useMemo, useCallback } from 'react'
import * as d3Force from 'd3-force'
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RefreshCw,
  Search,
  Sparkles,
} from 'lucide-react'
import { Badge } from '../reui/badge'
import { Button } from '../ui/button'
import { Input } from '../ui/input'

export interface GraphNode extends d3Force.SimulationNodeDatum {
  id: string
  label: string
  category: string
  file: string
  snippet: string
  color: string
  size: number
  tags: string[]
  // D3 force simulation attributes
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number | null
  fy?: number | null
}

export interface GraphLink extends d3Force.SimulationLinkDatum<GraphNode> {
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
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)

  const [searchQuery, setSearchQuery] = useState('')

  // Pan and Zoom transform states
  const transformRef = useRef<{ x: number; y: number; k: number }>({ x: 0, y: 0, k: 1 })
  const isDraggingCanvasRef = useRef(false)
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 })
  const draggedNodeRef = useRef<GraphNode | null>(null)
  const hoveredNodeRef = useRef<GraphNode | null>(null)

  // Simulation ref
  const simulationRef = useRef<d3Force.Simulation<GraphNode, GraphLink> | null>(null)
  const simNodesRef = useRef<GraphNode[]>([])
  const simLinksRef = useRef<GraphLink[]>([])

  // Filtered nodes based on search
  const activeNodeIds = useMemo(() => {
    const q = searchQuery.toLowerCase().trim()
    return new Set(
      nodes
        .filter((n) => {
          if (!q) return true
          return (
            n.label.toLowerCase().includes(q) ||
            n.snippet.toLowerCase().includes(q) ||
            n.tags.some((t) => t.toLowerCase().includes(q))
          )
        })
        .map((n) => n.id)
    )
  }, [nodes, searchQuery])

  // Initialize and run D3 force simulation
  useEffect(() => {
    if (!canvasRef.current || nodes.length === 0) return

    const canvas = canvasRef.current
    const width = canvas.width || 800
    const height = canvas.height || 600

    // Clone deep nodes and links for simulation mutate
    const simNodes: GraphNode[] = nodes.map((d) => ({
      ...d,
      x: d.x ?? (width / 2 + (Math.random() - 0.5) * 300),
      y: d.y ?? (height / 2 + (Math.random() - 0.5) * 300),
    }))

    const simLinks: GraphLink[] = links.map((d) => ({
      source: typeof d.source === 'object' ? (d.source as GraphNode).id : d.source,
      target: typeof d.target === 'object' ? (d.target as GraphNode).id : d.target,
      value: d.value ?? 1,
    }))

    simNodesRef.current = simNodes
    simLinksRef.current = simLinks

    // Setup force simulation
    const simulation = d3Force
      .forceSimulation<GraphNode>(simNodes)
      .force(
        'link',
        d3Force
          .forceLink<GraphNode, GraphLink>(simLinks)
          .id((d) => d.id)
          .distance(110)
          .strength(0.6)
      )
      .force('charge', d3Force.forceManyBody().strength(-240).distanceMax(500))
      .force('center', d3Force.forceCenter(width / 2, height / 2).strength(0.12))
      .force('collision', d3Force.forceCollide<GraphNode>().radius((d) => (d.size || 16) + 18))
      .alpha(1)
      .alphaDecay(0.022)

    simulationRef.current = simulation

    return () => {
      simulation.stop()
    }
  }, [nodes, links])

  // Canvas render loop
  useEffect(() => {
    let animId: number
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const render = () => {
      const width = canvas.width
      const height = canvas.height
      const transform = transformRef.current

      ctx.clearRect(0, 0, width, height)

      ctx.save()
      // Apply pan & zoom
      ctx.translate(transform.x, transform.y)
      ctx.scale(transform.k, transform.k)

      // ── 1. Draw Organic Glowing Links ──
      simLinksRef.current.forEach((link) => {
        const source = link.source as GraphNode
        const target = link.target as GraphNode
        if (!source || !target || source.x == null || target.x == null) return

        const isSourceActive = activeNodeIds.has(source.id)
        const isTargetActive = activeNodeIds.has(target.id)
        const isConnectedToSelected =
          selectedNodeId && (source.id === selectedNodeId || target.id === selectedNodeId)

        ctx.beginPath()
        ctx.moveTo(source.x, source.y!)
        ctx.lineTo(target.x, target.y!)

        if (isConnectedToSelected) {
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.85)'
          ctx.lineWidth = 2.2
          ctx.shadowColor = 'rgba(56, 189, 248, 0.9)'
          ctx.shadowBlur = 8
        } else if (isSourceActive && isTargetActive) {
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.16)'
          ctx.lineWidth = 1.2
          ctx.shadowBlur = 0
        } else {
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)'
          ctx.lineWidth = 0.8
          ctx.shadowBlur = 0
        }
        ctx.stroke()
        ctx.shadowBlur = 0
      })

      // ── 2. Draw Obsidian Bouncy Nodes ──
      simNodesRef.current.forEach((node) => {
        if (node.x == null || node.y == null) return

        const isSelected = node.id === selectedNodeId
        const isHovered = hoveredNodeRef.current?.id === node.id
        const isActive = activeNodeIds.has(node.id)
        const baseRadius = node.size || 16
        const radius = isSelected ? baseRadius * 1.35 : isHovered ? baseRadius * 1.2 : baseRadius

        // Glow halo for selected / hovered
        if (isSelected || isHovered) {
          ctx.beginPath()
          ctx.arc(node.x, node.y, radius + 8, 0, Math.PI * 2)
          ctx.fillStyle = isSelected
            ? 'rgba(56, 189, 248, 0.28)'
            : 'rgba(255, 255, 255, 0.15)'
          ctx.fill()
        }

        // Main Node Body
        ctx.beginPath()
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2)

        if (isActive) {
          ctx.fillStyle = node.color || '#38bdf8'
          ctx.shadowColor = node.color || '#38bdf8'
          ctx.shadowBlur = isSelected ? 16 : isHovered ? 12 : 6
        } else {
          ctx.fillStyle = '#334155'
          ctx.shadowBlur = 0
        }

        ctx.fill()
        ctx.shadowBlur = 0

        // Subtle dark inner core for depth
        ctx.beginPath()
        ctx.arc(node.x, node.y, radius * 0.45, 0, Math.PI * 2)
        ctx.fillStyle = 'rgba(10, 10, 15, 0.45)'
        ctx.fill()

        // Border ring
        ctx.beginPath()
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2)
        ctx.strokeStyle = isSelected
          ? '#ffffff'
          : isActive
          ? 'rgba(255, 255, 255, 0.5)'
          : 'rgba(255, 255, 255, 0.1)'
        ctx.lineWidth = isSelected ? 2.5 : 1.2
        ctx.stroke()

        // Node Label
        if (isActive || isSelected || isHovered || transform.k > 0.8) {
          ctx.font = `${isSelected ? 'bold 12px' : '11px'} -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
          ctx.fillStyle = isSelected ? '#ffffff' : isActive ? 'rgba(255, 255, 255, 0.88)' : 'rgba(255, 255, 255, 0.35)'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'top'
          ctx.fillText(node.label, node.x, node.y + radius + 6)
        }
      })

      ctx.restore()
      animId = requestAnimationFrame(render)
    }

    animId = requestAnimationFrame(render)
    return () => cancelAnimationFrame(animId)
  }, [selectedNodeId, activeNodeIds])

  // Handle Resize
  useEffect(() => {
    const updateSize = () => {
      if (!containerRef.current || !canvasRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      canvasRef.current.width = rect.width
      canvasRef.current.height = rect.height
      if (transformRef.current.x === 0 && transformRef.current.y === 0) {
        transformRef.current = { x: rect.width / 2, y: rect.height / 2, k: 0.95 }
      }
    }

    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  // Coordinate conversion helper (Screen to Canvas World)
  const screenToWorld = useCallback((clientX: number, clientY: number) => {
    if (!canvasRef.current) return { x: 0, y: 0 }
    const rect = canvasRef.current.getBoundingClientRect()
    const screenX = clientX - rect.left
    const screenY = clientY - rect.top
    const t = transformRef.current
    return {
      x: (screenX - t.x) / t.k,
      y: (screenY - t.y) / t.k,
    }
  }, [])

  // Find node under cursor
  const findNodeAt = useCallback(
    (worldX: number, worldY: number): GraphNode | null => {
      for (const node of simNodesRef.current) {
        if (node.x == null || node.y == null) continue
        const dist = Math.hypot(node.x - worldX, node.y - worldY)
        if (dist <= (node.size || 16) + 8) {
          return node
        }
      }
      return null
    },
    []
  )

  // Mouse Handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const { x, y } = screenToWorld(e.clientX, e.clientY)
    const node = findNodeAt(x, y)

    if (node) {
      draggedNodeRef.current = node
      node.fx = node.x
      node.fy = node.y
      if (simulationRef.current) {
        simulationRef.current.alphaTarget(0.3).restart()
      }
    } else {
      isDraggingCanvasRef.current = true
      dragStartRef.current = { x: e.clientX, y: e.clientY }
    }
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const { x, y } = screenToWorld(e.clientX, e.clientY)
    hoveredNodeRef.current = findNodeAt(x, y)

    if (draggedNodeRef.current) {
      draggedNodeRef.current.fx = x
      draggedNodeRef.current.fy = y
    } else if (isDraggingCanvasRef.current) {
      const dx = e.clientX - dragStartRef.current.x
      const dy = e.clientY - dragStartRef.current.y
      dragStartRef.current = { x: e.clientX, y: e.clientY }
      transformRef.current.x += dx
      transformRef.current.y += dy
    }
  }

  const handleMouseUp = () => {
    if (draggedNodeRef.current) {
      draggedNodeRef.current.fx = null
      draggedNodeRef.current.fy = null
      draggedNodeRef.current = null
      if (simulationRef.current) {
        simulationRef.current.alphaTarget(0)
      }
    }
    isDraggingCanvasRef.current = false
  }

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const { x, y } = screenToWorld(e.clientX, e.clientY)
    const node = findNodeAt(x, y)
    if (node) {
      onSelectNode(node)
    } else {
      onSelectNode(null)
    }
  }

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89
    const newK = Math.max(0.2, Math.min(3.5, transformRef.current.k * zoomFactor))

    if (!canvasRef.current) return
    const rect = canvasRef.current.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top

    // Zoom toward cursor
    transformRef.current.x = mouseX - (mouseX - transformRef.current.x) * (newK / transformRef.current.k)
    transformRef.current.y = mouseY - (mouseY - transformRef.current.y) * (newK / transformRef.current.k)
    transformRef.current.k = newK
  }

  const handleResetZoom = () => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    transformRef.current = { x: rect.width / 2, y: rect.height / 2, k: 0.95 }
    if (simulationRef.current) simulationRef.current.alpha(0.6).restart()
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full h-[520px] md:h-[580px] rounded-2xl bg-[#08080a] border border-border/80 overflow-hidden shadow-2xl flex flex-col select-none"
    >
      {/* ── Top Floating HUD & Filter Bar ── */}
      <div className="absolute top-3 left-3 right-3 z-10 flex flex-wrap items-center justify-between gap-2.5 pointer-events-none">
        {/* Left: Clean Search Bar */}
        <div className="flex items-center gap-2 pointer-events-auto">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted-foreground pointer-events-none" />
            <Input
              placeholder="Filter memory graph..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 pr-3 text-xs w-56 md:w-72 bg-card border-border/80 rounded-xl shadow-xs"
            />
          </div>
        </div>

        {/* Right: Controls & Node Count */}
        <div className="flex items-center gap-1.5 bg-card border border-border/80 p-1 rounded-xl pointer-events-auto">
          <Badge variant="outline" className="text-[10px] font-mono h-6 px-2 text-cyan-400 border-cyan-500/30 bg-cyan-500/10 gap-1">
            <Sparkles className="w-2.5 h-2.5" />
            <span>{nodes.length} Nodes</span>
          </Badge>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              transformRef.current.k = Math.min(3.5, transformRef.current.k * 1.25)
            }}
            className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              transformRef.current.k = Math.max(0.2, transformRef.current.k * 0.8)
            }}
            className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleResetZoom}
            className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
            title="Reset Canvas Position"
          >
            <Maximize2 className="w-3.5 h-3.5" />
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
        </div>
      </div>

      {/* ── HTML5 2D Physics Canvas ── */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onClick={handleClick}
        onWheel={handleWheel}
        className="flex-1 w-full h-full cursor-grab active:cursor-grabbing"
      />

      {/* ── Bottom Subtle Hint ── */}
      <div className="absolute bottom-2.5 left-4 z-10 pointer-events-none flex items-center gap-3 text-[10px] font-mono text-muted-foreground/60">
        <span>Drag nodes • Scroll to zoom • Click node to inspect Markdown</span>
      </div>
    </div>
  )
}
