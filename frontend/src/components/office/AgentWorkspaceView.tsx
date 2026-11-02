import type { ReactNode } from 'react'
import { ArrowLeft, FileText, Pencil, X } from '@/lib/zezo-icons'
import type { AgentOfficeMember } from './AutonomousOfficeScreen'
import type { AgentWorkspaceTab } from './AgentRosterTable'
import { Button } from '../ui/button'
import { Badge } from '../reui/badge'

interface AgentWorkspaceViewProps {
  agent: AgentOfficeMember
  activeTab: AgentWorkspaceTab
  onTabChange: (tab: AgentWorkspaceTab) => void
  onBack: () => void
  children: ReactNode
}

const tabs: { id: AgentWorkspaceTab; label: string; icon: ReactNode }[] = [
  { id: 'edit', label: 'Edit', icon: <Pencil className="h-4 w-4" /> },
  { id: 'files', label: 'Files', icon: <FileText className="h-4 w-4" /> },
]

export function AgentWorkspaceView({ agent, activeTab, onTabChange, onBack, children }: AgentWorkspaceViewProps) {
  return (
    <main className="flex h-full min-h-0 flex-col overflow-hidden bg-[var(--background)]">
      <header className="flex min-h-16 items-center gap-3 border-b border-[var(--border)] px-4 py-3 sm:px-6">
        <Button variant="ghost" size="icon" onClick={onBack} aria-label="Back to agents" className="shrink-0">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h1 className="truncate text-base font-semibold text-[var(--foreground)]">{agent.name}</h1>
            <Badge variant={agent.badgeVariant}>{agent.status.replaceAll('_', ' ')}</Badge>
          </div>
          <p className="truncate text-sm text-[var(--muted-foreground)]">{agent.role}</p>
        </div>
        <Button variant="ghost" size="icon" onClick={onBack} aria-label="Close agent workspace" className="shrink-0">
          <X className="h-4 w-4" />
        </Button>
      </header>

      <nav aria-label="Agent workspace" className="flex shrink-0 items-center gap-1 border-b border-[var(--border)] px-4 sm:px-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            aria-current={activeTab === tab.id ? 'page' : undefined}
            onClick={() => onTabChange(tab.id)}
            className={`-mb-px inline-flex h-11 items-center gap-2 border-b-2 px-3 text-sm transition-colors ${activeTab === tab.id ? 'border-[var(--primary)] text-[var(--foreground)]' : 'border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]'}`}
          >
            {tab.icon}{tab.label}
          </button>
        ))}
      </nav>

      <section className="flex min-h-0 flex-1 overflow-hidden p-3 sm:p-5">{children}</section>
    </main>
  )
}
