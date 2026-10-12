import React, { useState, useEffect } from 'react'
import {
  MessageSquare,
  Edit3,
  FolderGit2,
  Play,
  Cpu,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react'
import type { AgentProfile } from '../../types/zezo'
import { api } from '../../lib/api'

interface AgentInspectorProps {
  agent: AgentProfile | null
  onClose: () => void
  onOpenChat: (agent: AgentProfile) => void
  onDispatchTask: (agent: AgentProfile, prompt: string) => void
}

export const AgentInspector: React.FC<AgentInspectorProps> = ({
  agent,
  onClose,
  onOpenChat,
  onDispatchTask,
}) => {
  if (!agent) return null

  const [isControlsOpen, setIsControlsOpen] = useState(false)
  const [quickPrompt, setQuickPrompt] = useState('')
  const [displayName, setDisplayName] = useState(agent.displayName || agent.name)
  const [defaultTool, setDefaultTool] = useState(agent.default_tool)
  const [modelId, setModelId] = useState(agent.model_id)
  const [worktree, setWorktree] = useState(agent.worktree_branch || '')
  const [riskTier, setRiskTier] = useState(agent.risk_tier || 'autonomous')
  const [isSaving, setIsSaving] = useState(false)
  const [modelsList, setModelsList] = useState<string[]>([])

  useEffect(() => {
    setDisplayName(agent.displayName || agent.name)
    setDefaultTool(agent.default_tool)
    setModelId(agent.model_id)
    setWorktree(agent.worktree_branch || '')
    setRiskTier(agent.risk_tier || 'autonomous')
  }, [agent])

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await api.getModels()
        if (res && res.models) {
          setModelsList(res.models.map((m: any) => m.id))
        }
      } catch {}
    }
    fetchModels()
  }, [])

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await api.updateAgent(agent.id, {
        displayName,
        default_tool: defaultTool,
        model_id: modelId,
        worktree_branch: worktree,
        risk_tier: riskTier,
      })
      agent.displayName = displayName
      agent.default_tool = defaultTool
      agent.model_id = modelId
      agent.worktree_branch = worktree
      agent.risk_tier = riskTier
      setIsControlsOpen(false)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <aside className="w-96 border-l border-white/10 bg-[#121110] flex flex-col h-full select-none text-[#e4e0d8]">
      {/* Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm text-[#121110] shadow-sm shrink-0"
            style={{ backgroundColor: agent.color || '#e4e0d8' }}
          >
            {agent.avatar_pixel || agent.displayName?.[0] || agent.name[0]}
          </div>
          <div>
            <div className="font-semibold text-xs text-[#e4e0d8]">
              {agent.displayName || agent.name}
            </div>
            <div className="text-[10px] text-[#9a948a] uppercase font-mono">
              {agent.engine} · {agent.id}
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-[#9a948a] hover:text-[#e4e0d8] hover:bg-white/5 transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Top Action Buttons [CHAT] [EDIT] [FILES] */}
        <div>
          <label className="text-[11px] font-semibold uppercase tracking-wider text-[#9a948a] mb-2 block">
            Agent Actions
          </label>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => onOpenChat(agent)}
              className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-[#e4e0d8] hover:bg-white text-[#121110] font-semibold text-xs shadow-sm transition-all cursor-pointer"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Chat</span>
            </button>
            <button
              onClick={() => setIsControlsOpen(true)}
              className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-[#1a1918] hover:bg-white/10 text-[#e4e0d8] font-medium text-xs border border-white/10 transition-all cursor-pointer"
            >
              <Edit3 className="w-3.5 h-3.5 text-[#e2d8ca]" />
              <span>Configure</span>
            </button>
            <button
              onClick={() => alert(`Active worktree: ${worktree}`)}
              className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-[#1a1918] hover:bg-white/10 text-[#e4e0d8] font-medium text-xs border border-white/10 transition-all cursor-pointer"
            >
              <FolderGit2 className="w-3.5 h-3.5 text-[#e2d8ca]" />
              <span>Worktree</span>
            </button>
          </div>
        </div>

        {/* Quick Task Dispatcher */}
        <div className="p-3 rounded-xl bg-[#1a1918]/80 border border-white/10">
          <label className="text-[11px] font-semibold uppercase tracking-wider text-[#9a948a] mb-1.5 block">
            Direct Task Dispatch
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={quickPrompt}
              onChange={(e) => setQuickPrompt(e.target.value)}
              placeholder="e.g. Audit auth route for leaks..."
              className="flex-1 bg-[#121110] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-[#e4e0d8] placeholder:text-[#9a948a] focus:outline-hidden focus:border-[#e4e0d8]"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && quickPrompt.trim()) {
                  onDispatchTask(agent, quickPrompt.trim())
                  setQuickPrompt('')
                }
              }}
            />
            <button
              onClick={() => {
                if (quickPrompt.trim()) {
                  onDispatchTask(agent, quickPrompt.trim())
                  setQuickPrompt('')
                }
              }}
              className="px-3 py-1.5 bg-[#1a1918] hover:bg-white/10 border border-white/10 text-[#e4e0d8] rounded-lg text-xs font-medium flex items-center gap-1 transition-all cursor-pointer"
            >
              <Play className="w-3 h-3 text-[#e2d8ca]" />
            </button>
          </div>
        </div>

        {/* Collapsible AGENT ENVIRONMENT & CONTROLS Drawer */}
        <div className="border border-white/10 rounded-xl bg-[#1a1918]/60 overflow-hidden">
          <button
            onClick={() => setIsControlsOpen(!isControlsOpen)}
            className="w-full p-3 flex items-center justify-between text-left hover:bg-white/5 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-[#e2d8ca]" />
              <span className="text-xs font-semibold uppercase tracking-wider text-[#e4e0d8]">
                Agent Environment & Controls
              </span>
            </div>
            {isControlsOpen ? (
              <ChevronUp className="w-4 h-4 text-[#9a948a]" />
            ) : (
              <ChevronDown className="w-4 h-4 text-[#9a948a]" />
            )}
          </button>

          {isControlsOpen && (
            <div className="p-3 pt-1 space-y-3.5 border-t border-white/5">
              {/* Display Name */}
              <div>
                <label className="text-[11px] text-[#9a948a] mb-1 block">Display Name</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full bg-[#121110] border border-white/10 rounded-md px-2.5 py-1.5 text-xs text-[#e4e0d8] focus:outline-hidden focus:border-[#e4e0d8]"
                />
              </div>

              {/* Execution Engine / Tool */}
              <div>
                <label className="text-[11px] text-[#9a948a] mb-1 block">Execution Engine</label>
                <select
                  value={defaultTool}
                  onChange={(e) => setDefaultTool(e.target.value)}
                  className="w-full bg-[#121110] border border-white/10 rounded-md px-2.5 py-1.5 text-xs text-[#e4e0d8] focus:outline-hidden focus:border-[#e4e0d8]"
                >
                  <option value="antigravity_run">Antigravity Synthesis (antigravity_run)</option>
                  <option value="opencode_run">Opencode Autonomous (opencode_run)</option>
                  <option value="kilo_run">Kilo Code Refactoring (kilo_run)</option>
                  <option value="code_helper">Inline Code Helper (code_helper)</option>
                  <option value="dev_agent">Dev Read-Only Agent (dev_agent)</option>
                </select>
              </div>

              {/* Model Selector */}
              <div>
                <label className="text-[11px] text-[#9a948a] mb-1 block">Active LLM Model</label>
                <select
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  className="w-full bg-[#121110] border border-white/10 rounded-md px-2.5 py-1.5 text-xs text-[#e4e0d8] focus:outline-hidden focus:border-[#e4e0d8] font-mono"
                >
                  {modelsList.length > 0 ? (
                    modelsList.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                      <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                      <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (Groq)</option>
                      <option value="qwen-2.5-coder-32b">qwen-2.5-coder-32b (Groq)</option>
                    </>
                  )}
                </select>
              </div>

              {/* Worktree / Branch */}
              <div>
                <label className="text-[11px] text-[#9a948a] mb-1 block">Isolated Worktree</label>
                <input
                  type="text"
                  value={worktree}
                  onChange={(e) => setWorktree(e.target.value)}
                  placeholder="e.g. branch-auth-refactor"
                  className="w-full bg-[#121110] border border-white/10 rounded-md px-2.5 py-1.5 text-xs text-[#e4e0d8] focus:outline-hidden focus:border-[#e4e0d8] font-mono"
                />
              </div>

              {/* Risk Tier */}
              <div>
                <label className="text-[11px] text-[#9a948a] mb-1 block">Safety Governance Tier</label>
                <select
                  value={riskTier}
                  onChange={(e) => setRiskTier(e.target.value)}
                  className="w-full bg-[#121110] border border-white/10 rounded-md px-2.5 py-1.5 text-xs text-[#e4e0d8] focus:outline-hidden focus:border-[#e4e0d8]"
                >
                  <option value="autonomous">Tier 1: Autonomous (Auto-executes safe changes)</option>
                  <option value="supervised">Tier 2: Supervised (Confirms file overwrites)</option>
                  <option value="strict">Tier 3: Strict (Requires manual token approval)</option>
                </select>
              </div>

              {/* Save Button */}
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="w-full py-2 bg-[#e4e0d8] hover:bg-white text-[#121110] rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>{isSaving ? 'Saving Changes...' : 'Save Agent Configuration'}</span>
              </button>
            </div>
          )}
        </div>

        {/* Live Agent Logs */}
        <div>
          <label className="text-[11px] font-semibold uppercase tracking-wider text-[#9a948a] mb-2 block">
            Activity Log
          </label>
          <div className="bg-[#121110] border border-white/10 rounded-lg p-2.5 font-mono text-[11px] text-[#9a948a] h-36 overflow-y-auto space-y-1">
            {agent.logs && agent.logs.length > 0 ? (
              agent.logs.map((log, i) => <div key={i}>› {log}</div>)
            ) : (
              <div className="text-[#5a544c] italic">No recent background events.</div>
            )}
          </div>
        </div>
      </div>
    </aside>
  )
}
