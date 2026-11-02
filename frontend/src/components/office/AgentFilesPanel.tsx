import { useEffect, useState } from 'react'
import { Database, FileText, FolderOpen, Save, ShieldCheck } from '@/lib/zezo-icons'
import type { AgentOfficeMember, CorePersonaFileItem, CorePersonaFileKey } from './AutonomousOfficeScreen'
import { Frame, FramePanel } from '../reui/frame'
import { Card, CardContent } from '../reui/card'
import { Badge } from '../reui/badge'
import { Button } from '../ui/button'
import { ScrollArea } from '../ui/scroll-area'
import { Switch } from '../ui/switch'

interface AgentFilesPanelProps {
  agent: AgentOfficeMember
  files: CorePersonaFileItem[]
  toggles: Partial<Record<CorePersonaFileKey, boolean>>
  getContent: (fileKey: CorePersonaFileKey) => string
  onToggle: (fileKey: CorePersonaFileKey, checked: boolean) => void
  onSave: (fileKey: CorePersonaFileKey, content: string) => void
  onOpenExplorer: () => void
}

export function AgentFilesPanel({ agent, files, toggles, getContent, onToggle, onSave, onOpenExplorer }: AgentFilesPanelProps) {
  const [selectedFile, setSelectedFile] = useState<CorePersonaFileKey>('SOUL.md')
  const [content, setContent] = useState(() => getContent('SOUL.md'))

  useEffect(() => {
    setContent(getContent(selectedFile))
  }, [agent.id, selectedFile])

  const selectFile = (fileKey: CorePersonaFileKey) => {
    setSelectedFile(fileKey)
    setContent(getContent(fileKey))
  }

  return (
    <Frame className="h-full min-h-0 w-full overflow-hidden border-[var(--border)]">
      <FramePanel className="flex h-full min-h-0 flex-col overflow-hidden border-[var(--border)] bg-[var(--card)] p-0">
        <div className="flex min-h-0 flex-1 flex-col md:flex-row">
          <aside className="flex w-full shrink-0 flex-col gap-3 overflow-hidden border-b border-[var(--border)] bg-[var(--input)]/15 p-3 md:w-72 md:border-b-0 md:border-r">
            <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">Core Persona Files</div>
            <ScrollArea className="min-h-0 flex-1 pr-1">
              <div className="flex flex-col gap-2">
                {files.map((file) => {
                  const active = selectedFile === file.id
                  return (
                    <Card key={file.id} onClick={() => selectFile(file.id)} className={`cursor-pointer transition-colors ${active ? 'border-[var(--primary)] bg-[var(--primary)]/10' : 'border-[var(--border)] bg-[var(--card)] hover:bg-[var(--input)]/50'}`}>
                      <CardContent className="flex items-center justify-between gap-3 p-3">
                        <div className="flex min-w-0 items-start gap-2.5">
                          {file.id === 'AGENTS.md' ? <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[var(--muted-foreground)]" /> : file.id === 'MEMORY.md' ? <Database className="mt-0.5 h-4 w-4 shrink-0 text-[var(--muted-foreground)]" /> : <FileText className="mt-0.5 h-4 w-4 shrink-0 text-[var(--muted-foreground)]" />}
                          <div className="min-w-0">
                            <div className="truncate text-sm font-medium text-[var(--foreground)]">{file.name}</div>
                            <div className="truncate text-xs text-[var(--muted-foreground)]">{file.desc}</div>
                          </div>
                        </div>
                        <div onClick={(event) => event.stopPropagation()} className="shrink-0">
                          <Switch checked={toggles[file.id] ?? true} onCheckedChange={(checked) => onToggle(file.id, checked)} aria-label={`Enable ${file.name}`} />
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </ScrollArea>
            <Button variant="outline" size="sm" onClick={onOpenExplorer} className="h-9 shrink-0 gap-2"><FolderOpen className="h-4 w-4" />Open workspace in Explorer</Button>
          </aside>

          <section className="flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-hidden p-3 sm:p-4">
            <div className="flex shrink-0 items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
              <div className="flex min-w-0 items-center gap-2">
                <h2 className="text-sm font-semibold text-[var(--foreground)]">{selectedFile}</h2>
                <Badge variant="outline" className="max-w-[50vw] truncate text-xs text-[var(--muted-foreground)]">
                  {selectedFile === 'SOUL.md' ? 'config/agent_ids.json' : selectedFile === 'AGENTS.md' ? 'AGENTS.md · root guidelines' : selectedFile === 'PROFILE.md' ? 'Agent identity specification' : 'memory/zezo_brain.db'}
                </Badge>
              </div>
              <span className="shrink-0 text-xs text-[var(--muted-foreground)]">{content.length} chars</span>
            </div>
            <textarea
              value={content}
              onChange={(event) => setContent(event.target.value)}
              aria-label={`Edit ${selectedFile}`}
              className="min-h-[240px] flex-1 resize-none rounded-md border border-[var(--border)] bg-[var(--input)]/25 p-4 font-mono text-sm leading-relaxed text-[var(--foreground)] outline-none focus:border-[var(--primary)]"
            />
            <div className="flex shrink-0 justify-end border-t border-[var(--border)] pt-3">
              <Button onClick={() => onSave(selectedFile, content)} className="h-9 gap-2"><Save className="h-4 w-4" />Save File</Button>
            </div>
          </section>
        </div>
      </FramePanel>
    </Frame>
  )
}
