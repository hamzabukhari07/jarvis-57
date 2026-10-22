import React, { useMemo } from 'react'
import {
 ReactFlow,
 Background,
 Controls,
 MiniMap,
 type Node,
 type Edge,
 Position,
 Handle,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Zap } from 'lucide-react'
import type { AgentProfile } from '../../types/zezo'

interface CanvasViewProps {
 agents: AgentProfile[]
 onSelectAgent: (agent: AgentProfile) => void
}

// Custom Node component with Forma OS Theme
const AgentNode = ({ data }: { data: { agent: AgentProfile; onSelect: () => void } }) => {
 const { agent, onSelect } = data
 return (
 <div
 onClick={onSelect}
 className="p-3.5 rounded-xl border border-white/10 bg-[#121110]/95 hover:border-[#e4e0d8] transition-all cursor-pointer min-w-[220px]"
 >
 <Handle type="target" position={Position.Top} className="w-2.5 h-2.5 bg-[#e4e0d8]" />
 <div className="flex items-center gap-2.5">
 <div
 className="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs text-[#121110] "
 style={{ backgroundColor: agent.color || '#e4e0d8' }}
 >
 {agent.avatar_pixel || agent.displayName?.[0] || agent.name[0]}
 </div>
 <div>
 <div className="font-semibold text-xs text-[#e4e0d8]">{agent.displayName || agent.name}</div>
 <div className="text-[10px] text-[#9a948a] font-mono">{agent.role}</div>
 </div>
 </div>

 <div className="mt-2.5 pt-2 border-t border-white/5 text-[10px] font-mono text-[#9a948a] flex items-center justify-between">
 <span className="text-[#e2d8ca]">{agent.default_tool.replace('_run', '')}</span>
 <span className="text-[#d8d2c8] truncate max-w-[110px]">{agent.model_id}</span>
 </div>
 <Handle type="source" position={Position.Bottom} className="w-2.5 h-2.5 bg-[#e4e0d8]" />
 </div>
 )
}

const nodeTypes = {
 agentNode: AgentNode,
}

export const CanvasView: React.FC<CanvasViewProps> = ({ agents, onSelectAgent }) => {
 // Generate workflow nodes & edges
 const { nodes, edges } = useMemo(() => {
 const orchestratorNode: Node = {
 id: 'orchestrator',
 type: 'default',
 position: { x: 350, y: 50 },
 data: {
 label: (
 <div className="flex items-center gap-2 p-1 text-xs font-semibold text-[#e4e0d8]">
 <Zap className="w-3.5 h-3.5 text-[#e2d8ca]" />
 <span>ZEZO Central Orchestrator</span>
 </div>
 ),
 },
 style: {
 background: '#1a1918',
 color: '#e4e0d8',
 border: '1px solid rgba(255, 255, 255, 0.15)',
 borderRadius: '12px',
 padding: '8px 12px',
 },
 }

 const agentNodes: Node[] = agents.map((agent, index) => {
 const col = index % 3
 const row = Math.floor(index / 3)
 return {
 id: agent.id,
 type: 'agentNode',
 position: { x: 100 + col * 260, y: 180 + row * 160 },
 data: {
 agent,
 onSelect: () => onSelectAgent(agent),
 },
 }
 })

 const generatedEdges: Edge[] = agents.map((agent) => ({
 id: `e-orch-${agent.id}`,
 source: 'orchestrator',
 target: agent.id,
 animated: true,
 style: { stroke: '#d1ccc3', strokeWidth: 1.5 },
 }))

 return {
 nodes: [orchestratorNode, ...agentNodes],
 edges: generatedEdges,
 }
 }, [agents, onSelectAgent])

 return (
 <div className="w-full h-full bg-[#000000]">
 <ReactFlow
 nodes={nodes}
 edges={edges}
 nodeTypes={nodeTypes}
 fitView
 className="bg-[#000000]"
 >
 <Background color="#1f1e1d" gap={20} size={1} />
 <Controls className="bg-[#121110] border border-white/10 text-[#e4e0d8] rounded-lg fill-[#e4e0d8]" />
 <MiniMap
 nodeColor="#e4e0d8"
 maskColor="rgba(0, 0, 0, 0.85)"
 className="bg-[#121110] border border-white/10 rounded-lg overflow-hidden"
 />
 </ReactFlow>
 </div>
 )
}
