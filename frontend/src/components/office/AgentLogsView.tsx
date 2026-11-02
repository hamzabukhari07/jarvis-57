import type { RefObject } from 'react'
import { ArrowLeft, Copy, Search } from '@/lib/zezo-icons'
import type { AgentOfficeMember } from './AutonomousOfficeScreen'
import type { LogEntry } from '../../hooks/useZezoSocket'
import { Button } from '../ui/button'

interface AgentLogsViewProps {
  agent: AgentOfficeMember
  entries: LogEntry[]
  filterMode: 'agent' | 'errors'
  onFilterModeChange: (mode: 'agent' | 'errors') => void
  query: string
  onQueryChange: (query: string) => void
  autoFollow: boolean
  onToggleAutoFollow: () => void
  copied: boolean
  onCopy: () => void
  endRef: RefObject<HTMLDivElement | null>
  onBack: () => void
}

export function AgentLogsView({
  agent,
  entries,
  filterMode,
  onFilterModeChange,
  query,
  onQueryChange,
  autoFollow,
  onToggleAutoFollow,
  copied,
  onCopy,
  endRef,
  onBack,
}: AgentLogsViewProps) {
  return (
    <main className="flex h-full min-h-0 flex-col overflow-hidden bg-[var(--background)]">
      <header className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-4 sm:px-6">
        <Button variant="ghost" size="icon" onClick={onBack} aria-label="Back to agents"><ArrowLeft className="h-4 w-4" /></Button>
        <div className="min-w-0 flex-1">
          <h1 className="text-base font-semibold text-[var(--foreground)]">Logs · {agent.name}</h1>
          <p className="text-sm text-[var(--muted-foreground)]">Agent activity and system events</p>
        </div>
        <span className="text-xs text-[var(--muted-foreground)]">{entries.length} entries</span>
      </header>

      <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border)] px-4 py-3 sm:px-6">
        <label className="relative min-w-[180px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
          <input value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Search logs…" className="h-9 w-full rounded-md border border-[var(--border)] bg-[var(--card)] pl-9 pr-3 text-sm outline-none focus:border-[var(--primary)]" />
        </label>
        <div className="flex items-center rounded-md border border-[var(--border)] p-0.5">
          <Button variant={filterMode === 'agent' ? 'secondary' : 'ghost'} size="sm" onClick={() => onFilterModeChange('agent')} className="h-8">Agent</Button>
          <Button variant={filterMode === 'errors' ? 'secondary' : 'ghost'} size="sm" onClick={() => onFilterModeChange('errors')} className="h-8">Errors</Button>
        </div>
        <Button variant="outline" size="sm" onClick={onToggleAutoFollow} className="h-9">Auto-follow {autoFollow ? 'On' : 'Off'}</Button>
        <Button variant="outline" size="sm" onClick={onCopy} className="h-9 gap-2"><Copy className="h-4 w-4" />{copied ? 'Copied' : 'Copy'}</Button>
      </div>

      <section className="min-h-0 flex-1 overflow-auto p-4 sm:p-6" aria-label="Agent log entries">
        {entries.length === 0 ? (
          <div className="rounded-lg border border-dashed border-[var(--border)] px-4 py-12 text-center text-sm text-[var(--muted-foreground)]">No matching log entries.</div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-[var(--border)]">
            {entries.map((entry) => (
              <div key={entry.id} className="grid grid-cols-[100px_90px_minmax(0,1fr)] gap-3 border-b border-[var(--border)]/70 px-4 py-3 font-mono text-xs last:border-0">
                <span className="text-[var(--muted-foreground)]">{entry.time}</span>
                <span className={String(entry.level || entry.type).toUpperCase().includes('ERR') ? 'text-destructive' : 'text-[var(--primary)]'}>{entry.level || entry.type || 'INFO'}</span>
                <span className="break-words text-[var(--foreground)]">{entry.text}</span>
              </div>
            ))}
            <div ref={endRef} />
          </div>
        )}
      </section>
    </main>
  )
}
