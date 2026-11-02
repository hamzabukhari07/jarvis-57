import React, { useMemo, useState } from 'react'
import { Activity, Eye, FileText, MessageSquare, Pencil, Plus, Search, Trash2 } from '@/lib/zezo-icons'
import type { AgentOfficeMember } from './AutonomousOfficeScreen'
import { Button } from '../ui/button'
import { Badge } from '../reui/badge'
import { Blobatar } from 'blobatar/react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select'

export type AgentWorkspaceTab = 'edit' | 'chat' | 'files'

interface AgentRosterTableProps {
  agents: AgentOfficeMember[]
  selectedAgentId: string
  onSelectAgent: (agentId: string) => void
  onOpenWorkspace: (agent: AgentOfficeMember, tab: AgentWorkspaceTab) => void
  onOpenLogs: (agent: AgentOfficeMember) => void
  onDelete: (agent: AgentOfficeMember) => void
  onAddAgent: () => void
}

const statusClass = (status: AgentOfficeMember['status']) => {
  if (status === 'WORKING' || status === 'IN_MEETING') return 'text-emerald-500'
  if (status === 'IDLE') return 'text-muted-foreground'
  return 'text-amber-500'
}

export function AgentRosterTable({
  agents,
  selectedAgentId,
  onSelectAgent,
  onOpenWorkspace,
  onOpenLogs,
  onDelete,
  onAddAgent,
}: AgentRosterTableProps) {
  const [expandedAgentId, setExpandedAgentId] = useState<string | null>(null)
  const [detailAgent, setDetailAgent] = useState<AgentOfficeMember | null>(null)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  const filteredAgents = useMemo(() => agents.filter((agent) => {
    const searchText = `${agent.name} ${agent.role} ${agent.specialty}`.toLowerCase()
    return searchText.includes(query.trim().toLowerCase()) &&
      (statusFilter === 'all' || agent.status.toLowerCase() === statusFilter)
  }), [agents, query, statusFilter])

  const toggleRow = (agent: AgentOfficeMember) => {
    onSelectAgent(agent.id)
    setExpandedAgentId((current) => current === agent.id ? null : agent.id)
  }

  return (
    <main className="flex h-full min-h-0 flex-col overflow-hidden bg-[var(--background)]">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] px-5 py-4">
        <div>
          <h1 className="text-lg font-semibold text-[var(--foreground)]">Agents</h1>
          <p className="mt-0.5 text-sm text-[var(--muted-foreground)]">Manage your agents and their current work.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={onAddAgent} className="h-9 gap-2">
            <Plus className="h-4 w-4" /> Add Agent
          </Button>
        </div>
      </header>

      <section className="flex min-h-0 flex-1 flex-col p-5">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <label className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search agents…"
              className="h-10 w-full rounded-md border border-[var(--border)] bg-[var(--card)] pl-9 pr-3 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)]"
            />
          </label>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger aria-label="Filter agents by status" className="h-10 w-[180px] bg-[var(--card)] text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="working">Working</SelectItem>
              <SelectItem value="idle">Idle</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-xs text-[var(--muted-foreground)]">{filteredAgents.length} agents</span>
        </div>

        <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-[var(--border)] bg-[var(--card)]">
          <table className="w-full min-w-[760px] border-collapse text-left">
            <thead className="sticky top-0 z-10 bg-[var(--muted)]/80">
              <tr className="border-b border-[var(--border)] text-[11px] font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
                <th className="px-4 py-3">Agent</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Current task</th>
                <th className="w-16 px-3 py-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody>
              {filteredAgents.map((agent) => {
                const expanded = expandedAgentId === agent.id
                const selected = selectedAgentId === agent.id
                return (
                  <FragmentRow
                    key={agent.id}
                    agent={agent}
                    expanded={expanded}
                    selected={selected}
                    onToggle={() => toggleRow(agent)}
                    onView={() => setDetailAgent(agent)}
                    onOpenWorkspace={onOpenWorkspace}
                    onOpenLogs={onOpenLogs}
                    onDelete={onDelete}
                  />
                )
              })}
              {filteredAgents.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-12 text-center text-sm text-[var(--muted-foreground)]">No agents match this search.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {detailAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onMouseDown={(event) => event.target === event.currentTarget && setDetailAgent(null)}>
          <section role="dialog" aria-modal="true" aria-labelledby="agent-detail-title" className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 text-[var(--foreground)]">
            <div className="flex items-start gap-3">
              <div className="h-12 w-12 shrink-0 overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--input)] p-1">
                <Blobatar name={detailAgent.name} size={40} animate="hover" className="h-full w-full object-contain" />
              </div>
              <div className="min-w-0 flex-1">
                <h2 id="agent-detail-title" className="font-semibold">{detailAgent.name}</h2>
                <p className="text-sm text-[var(--muted-foreground)]">{detailAgent.role}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setDetailAgent(null)} aria-label="Close agent details">×</Button>
            </div>
            <div className="mt-4 space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3"><span className="text-[var(--muted-foreground)]">Status</span><Badge variant={detailAgent.badgeVariant}>{detailAgent.status.replaceAll('_', ' ')}</Badge></div>
              <div className="flex items-start justify-between gap-3"><span className="text-[var(--muted-foreground)]">Specialty</span><span className="max-w-[70%] text-right">{detailAgent.specialty || '—'}</span></div>
              <div className="flex items-center justify-between gap-3"><span className="text-[var(--muted-foreground)]">Engine · Model</span><span className="text-right">{detailAgent.engine} · {detailAgent.model}</span></div>
              <div className="flex items-start justify-between gap-3"><span className="text-[var(--muted-foreground)]">Workspace</span><span className="max-w-[70%] break-all text-right">{detailAgent.workspace === 'repo_active' ? 'Active project folder' : detailAgent.workspace}</span></div>
            </div>
          </section>
        </div>
      )}
    </main>
  )
}

function FragmentRow({
  agent,
  expanded,
  selected,
  onToggle,
  onView,
  onOpenWorkspace,
  onOpenLogs,
  onDelete,
}: {
  agent: AgentOfficeMember
  expanded: boolean
  selected: boolean
  onToggle: () => void
  onView: () => void
  onOpenWorkspace: (agent: AgentOfficeMember, tab: AgentWorkspaceTab) => void
  onOpenLogs: (agent: AgentOfficeMember) => void
  onDelete: (agent: AgentOfficeMember) => void
}) {
  return (
    <>
      <tr
        tabIndex={0}
        aria-expanded={expanded}
        onClick={onToggle}
        onKeyDown={(event) => (event.key === 'Enter' || event.key === ' ') && (event.preventDefault(), onToggle())}
        className={`cursor-pointer border-b border-[var(--border)]/70 outline-none hover:bg-[var(--muted)]/40 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--ring)] ${selected ? 'bg-[var(--muted)]/25' : ''}`}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 shrink-0 overflow-hidden rounded-md border border-[var(--border)] bg-[var(--input)] p-0.5"><Blobatar name={agent.name} size={32} animate="hover" className="h-full w-full object-contain" /></div>
            <div className="min-w-0"><div className="truncate text-sm font-medium text-[var(--foreground)]">{agent.name}</div><div className="truncate text-xs text-[var(--muted-foreground)]">{agent.engine}</div></div>
          </div>
        </td>
        <td className="max-w-[220px] truncate px-4 py-3 text-sm text-[var(--muted-foreground)]">{agent.role}</td>
        <td className="px-4 py-3"><span className={`inline-flex items-center gap-2 text-xs ${statusClass(agent.status)}`}><span className="h-2 w-2 rounded-full bg-current" />{agent.status.replaceAll('_', ' ')}</span></td>
        <td className="max-w-[300px] truncate px-4 py-3 text-sm text-[var(--muted-foreground)]">{agent.currentTask || 'No current task'}</td>
        <td className="px-3 py-3 text-right"><Button variant="ghost" size="icon" aria-label={`View ${agent.name} details`} title="View agent details" onClick={(event) => { event.stopPropagation(); onView() }} className="h-8 w-8"><Eye className="h-4 w-4" /></Button></td>
      </tr>
      {expanded && (
        <tr className="border-b border-[var(--border)] bg-[var(--muted)]/15">
          <td colSpan={5} className="px-4 py-3">
            <div className="flex flex-wrap items-center gap-2 pl-12">
              <ActionButton label="Edit" icon={<Pencil className="h-4 w-4" />} onClick={() => onOpenWorkspace(agent, 'edit')} />
              <ActionButton label="Chat" icon={<MessageSquare className="h-4 w-4" />} onClick={() => onOpenWorkspace(agent, 'chat')} />
              <ActionButton label="Delete" icon={<Trash2 className="h-4 w-4" />} onClick={() => onDelete(agent)} destructive disabled={agent.id === 'MICHAEL'} />
              <ActionButton label="Logs" icon={<Activity className="h-4 w-4" />} onClick={() => onOpenLogs(agent)} />
              <ActionButton label="Files" icon={<FileText className="h-4 w-4" />} onClick={() => onOpenWorkspace(agent, 'files')} />
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function ActionButton({ label, icon, onClick, destructive = false, disabled = false }: { label: string; icon: React.ReactNode; onClick: () => void; destructive?: boolean; disabled?: boolean }) {
  return (
    <Button
      variant="outline"
      size="sm"
      disabled={disabled}
      title={disabled ? 'The lead agent cannot be removed' : undefined}
      onClick={(event) => { event.stopPropagation(); onClick() }}
      className={destructive ? 'h-9 gap-2 border-destructive/40 text-destructive hover:bg-destructive/10' : 'h-9 gap-2'}
    >
      {icon}{label}
    </Button>
  )
}
