import React from 'react'
import { Plus, Layers, Terminal } from 'lucide-react'
import type { AgentProfile } from '../../types/zezo'

interface FleetRosterProps {
  agents: AgentProfile[]
  selectedAgentId: string | null
  onSelectAgent: (agent: AgentProfile) => void
  onAddNewAgent: () => void
}

export const FleetRoster: React.FC<FleetRosterProps> = ({
  agents,
  selectedAgentId,
  onSelectAgent,
  onAddNewAgent,
}) => {
  return (
    <div className="w-80 border-r border-white/10 bg-[#121110] flex flex-col h-full select-none text-[#e4e0d8]">
      {/* Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-[#e2d8ca]" />
          <span className="font-semibold text-xs uppercase tracking-wider text-[#e4e0d8]">
            Active Fleet ({agents.length})
          </span>
        </div>
        <button
          onClick={onAddNewAgent}
          className="p-1 rounded-md bg-[#1a1918] border border-white/10 hover:border-white/20 text-[#d8d2c8] hover:text-white transition-all cursor-pointer"
          title="Deploy New Agent to Fleet"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Roster List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {agents.map((agent) => {
          const isSelected = agent.id === selectedAgentId
          return (
            <div
              key={agent.id}
              onClick={() => onSelectAgent(agent)}
              className={`p-3 rounded-xl border cursor-pointer transition-all ${
                isSelected
                  ? 'bg-[#1a1918] border-[#e4e0d8] shadow-sm'
                  : 'bg-[#1a1918]/60 border-white/10 hover:bg-[#1a1918] hover:border-white/20'
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs text-[#121110] shadow-sm shrink-0"
                  style={{ backgroundColor: agent.color || '#e4e0d8' }}
                >
                  {agent.avatar_pixel || agent.displayName?.[0] || agent.name[0]}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-xs text-[#e4e0d8] truncate">
                      {agent.displayName || agent.name}
                    </span>
                    <span className="text-[10px] font-mono text-[#9a948a] uppercase bg-white/5 px-1.5 py-0.5 rounded border border-white/10">
                      {agent.engine}
                    </span>
                  </div>
                  <div className="text-[11px] text-[#9a948a] truncate mt-0.5">
                    {agent.specialty}
                  </div>
                </div>
              </div>

              {/* Status and Active Model Tag */}
              <div className="mt-2.5 pt-2 border-t border-white/5 flex items-center justify-between text-[10px] text-[#9a948a] font-mono">
                <div className="flex items-center gap-1.5 truncate mr-2">
                  <Terminal className="w-3 h-3 text-[#e2d8ca]" />
                  <span className="truncate">{agent.model_id}</span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span className="uppercase text-emerald-400 font-semibold">{agent.status || 'READY'}</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
