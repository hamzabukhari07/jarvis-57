import React, { useState, useEffect, useRef } from 'react'
import {
 Plus,
 Search,
 MessageSquare,
 Trash2,
 FolderOpen,
 FileText,
} from '@/lib/zezo-icons'
import {
 AssistantRuntimeProvider,
 useLocalRuntime,
 type ThreadMessageLike,
} from '@assistant-ui/react'
import { AgentChatThread } from './AgentChatThread'
import { Frame } from '../reui/frame'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import {
 Select,
 SelectContent,
 SelectItem,
 SelectTrigger,
 SelectValue,
} from '../ui/select'
import type { AgentOfficeMember } from './AutonomousOfficeScreen'
import { ENGINE_MODELS_MAP } from './AutonomousOfficeScreen'
import { api } from '../../lib/api'
import { cn } from '@/lib/utils'
import { Blobatar } from 'blobatar/react'

const ACTIVE_PROJECT_PATH = 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57'

export interface ChatThreadItem {
 id: string
 title: string
 preview: string
 updatedAt: string
 messageCount: number
 tag: string
 messages?: ThreadMessageLike[]
}

interface AgentDirectChatViewProps {
 agent: AgentOfficeMember
 agents: AgentOfficeMember[]
 onSelectAgent: (agentId: string) => void
 onUpdateAgent?: (updated: Partial<AgentOfficeMember>) => void
 onUpdateAgentStatus?: (agentId: string, status: AgentOfficeMember['status'], speech?: string) => void
}

export const AgentDirectChatView: React.FC<AgentDirectChatViewProps> = ({
 agent,
 agents,
 onSelectAgent,
 onUpdateAgent,
 onUpdateAgentStatus,
}) => {
 // Real persisted chat threads for this specific agent (no fake/canned mock items)
 const [threads, setThreads] = useState<ChatThreadItem[]>(() => {
 try {
 const saved = localStorage.getItem(`zezo_agent_threads_${agent.id}`)
 if (saved) {
 const parsed = JSON.parse(saved)
 if (Array.isArray(parsed) && parsed.length > 0) {
  // Filter out any legacy dummy initialized threads
  return parsed
   .filter(
    (t: ChatThreadItem) =>
     !t.id.endsWith('-init') &&
     t.title !== `Chat with ${agent.name}` &&
     (t.messageCount || 0) > 0
   )
   .map((t: any) => ({
    ...t,
    messages: (t.messages || []).map((m: any) =>
     m.role === 'user' ? { id: m.id, role: 'user', content: m.content } : m
    ),
   }))
 }
 }
 } catch {
 // Clean slate
 }
 return []
 })

 const [activeThreadId, setActiveThreadId] = useState<string>(() => {
 return threads[0]?.id || `thread-${agent.id}-${Date.now()}`
 })
 const [searchQuery, setSearchQuery] = useState<string>('')
 const [workspaceFiles, setWorkspaceFiles] = useState<Array<{ name: string; path?: string; type?: string }>>([])
 const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; size: string; type: string; path?: string }>>([])
 const fileInputRef = useRef<HTMLInputElement>(null)

 // Persist real threads per agent
 useEffect(() => {
 try {
 localStorage.setItem(`zezo_agent_threads_${agent.id}`, JSON.stringify(threads))
 } catch (e) {
 console.warn('Failed to persist agent threads:', e)
 }
 }, [threads, agent.id])

 // Create New Real Thread Handler
 const handleCreateNewThread = () => {
 const newId = `thread-${agent.id}-${Date.now()}`
 setActiveThreadId(newId)
 }

 // Filter threads by search query
 const filteredThreads = threads.filter(
 (t) =>
 t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
 t.tag.toLowerCase().includes(searchQuery.toLowerCase()) ||
 t.preview.toLowerCase().includes(searchQuery.toLowerCase())
 )

 const [currentWorkspace, setCurrentWorkspace] = useState(agent.workspace === 'repo_active' ? ACTIVE_PROJECT_PATH : agent.workspace || '')

 useEffect(() => {
  setCurrentWorkspace(agent.workspace === 'repo_active' ? ACTIVE_PROJECT_PATH : agent.workspace || '')
 }, [agent.workspace])

 useEffect(() => {
  let active = true
  api.getAttachments().then((items) => {
   if (active) setWorkspaceFiles(items.map((item: any) => ({ name: item.name || 'File', path: item.path, type: item.is_folder ? 'Folder' : item.file_type || 'File' })))
  }).catch(() => {})
  return () => { active = false }
 }, [agent.id])

 const handleBrowseWorkspace = async () => {
  try {
   const result = await api.pickAgentFolder(currentWorkspace)
   if (result.success && result.path) {
    setCurrentWorkspace(result.path)
    onUpdateAgent?.({ workspace: result.path })
   }
  } catch (err) {
   console.error('Failed to select agent workspace folder:', err)
  }
 }

 const handleFileUpload = async (files: FileList | null) => {
  if (!files?.length) return
  const selectedFiles = Array.from(files).filter((file) => {
   const path = ((file as any).webkitRelativePath || file.name).replace(/\\/g, '/')
   return !['/node_modules/', '/.git/', '/.venv/', '/dist/', '/.next/', '/__pycache__/'].some((part) => path.includes(part))
  })
  if (!selectedFiles.length) return
  const formData = new FormData()
  selectedFiles.slice(0, 200).forEach((file) => formData.append('files', file, (file as any).webkitRelativePath || file.name))
  try {
   const response = await api.uploadFiles(formData)
   const entries = (response.files || []).map((file: any) => ({
    name: file.name || 'File',
    size: typeof file.size === 'number' ? `${(file.size / 1024).toFixed(1)} KB` : file.size || '0 KB',
    type: file.is_folder ? 'FOLDER' : (file.file_type || 'FILE').toUpperCase(),
    path: file.path,
   }))
   setUploadedFiles((previous) => [...entries, ...previous.filter((item) => !entries.some((entry: any) => (entry.path || entry.name) === (item.path || item.name)))])
   setWorkspaceFiles((previous) => [...entries, ...previous.filter((item: any) => !entries.some((entry: any) => (entry.path || entry.name) === (item.path || item.name)))])
  } catch (error) {
   console.error('Agent chat file upload failed:', error)
  } finally {
   if (fileInputRef.current) fileInputRef.current.value = ''
  }
 }

 // Available models for active engine
 const engineLabels: Record<string, string> = {
  opencode_run: 'OpenCode', kilo_run: 'Kilo Code', antigravity_run: 'Antigravity', groq: 'Groq',
 }
 const engineLabel = engineLabels[agent.engine] || agent.engine || 'Not set'
 const modelLabel = ENGINE_MODELS_MAP[agent.engine]?.find((model) => model.id === agent.model)?.label || agent.model || 'Default model'
 const modelOptions = ENGINE_MODELS_MAP[agent.engine] || []
 const handleEngineChange = (engine: string) => {
  const firstModel = ENGINE_MODELS_MAP[engine]?.[0]?.id
  onUpdateAgent?.({ engine, model: firstModel || agent.model })
 }

 const activeThread = threads.find((thread) => thread.id === activeThreadId)
 const handleConversationComplete = (userText: string, replyText: string, savedMessages: ThreadMessageLike[]) => {
  const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  setThreads((prev) => {
   const existing = prev.find((thread) => thread.id === activeThreadId)
   const next: ChatThreadItem = {
    id: activeThreadId,
    title: existing?.title || userText.slice(0, 32) + (userText.length > 32 ? '...' : ''),
    preview: replyText.slice(0, 60) + (replyText.length > 60 ? '...' : ''),
    updatedAt: now,
    messageCount: (existing?.messageCount || 0) + 2,
    tag: (agent.engine || 'opencode').split('_')[0].toUpperCase(),
    messages: [...(existing?.messages || []), ...savedMessages],
   }
   return [next, ...prev.filter((thread) => thread.id !== activeThreadId)]
  })
 }

 return (
 <Frame className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_270px] overflow-hidden bg-[var(--background)]">
  <aside className="flex min-h-0 flex-col border-b border-[var(--border)] bg-[var(--card)]/50 md:border-b-0 md:border-r">
   <div className="flex flex-col gap-3 border-b border-[var(--border)] p-3">
    <Button variant="default" size="sm" onClick={handleCreateNewThread} className="h-9 w-full justify-start gap-2 text-sm"><Plus className="h-4 w-4" />New Chat</Button>
    <label className="relative">
     <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--muted-foreground)]" />
     <Input aria-label="Search chats" placeholder="Search chats" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} className="h-9 pl-8 text-sm" />
    </label>
   </div>
   <div className="min-h-0 flex-1 overflow-y-auto p-2">
    <div className="px-2 py-2 text-[11px] font-medium text-[var(--muted-foreground)]">Recent chats</div>
    {filteredThreads.length === 0 ? (
     <div className="px-3 py-8 text-center text-xs text-[var(--muted-foreground)]">Your chats with {agent.name} will appear here.</div>
    ) : filteredThreads.map((thread) => {
     const isActive = thread.id === activeThreadId
     return <div key={thread.id} role="button" tabIndex={0} onClick={() => setActiveThreadId(thread.id)} onKeyDown={(event) => (event.key === 'Enter' || event.key === ' ') && setActiveThreadId(thread.id)} className={cn('group flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2.5 text-left', isActive ? 'bg-[var(--secondary)] text-[var(--foreground)]' : 'text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/60 hover:text-[var(--foreground)]')}>
      <MessageSquare className="h-4 w-4 shrink-0" />
      <span className="min-w-0 flex-1 truncate text-xs">{thread.title}</span>
      <button type="button" aria-label={`Delete ${thread.title}`} onClick={(event) => { event.stopPropagation(); const remaining = threads.filter((item) => item.id !== thread.id); setThreads(remaining); if (activeThreadId === thread.id) setActiveThreadId(remaining[0]?.id || `thread-${agent.id}-${Date.now()}`) }} className="rounded p-1 opacity-0 hover:bg-[var(--destructive)]/15 hover:text-[var(--destructive)] group-hover:opacity-100"><Trash2 className="h-3.5 w-3.5" /></button>
     </div>
    })}
   </div>
  </aside>

  <main className="flex min-h-0 min-w-0 flex-col overflow-hidden bg-[var(--background)]">
   <header className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 border-b border-[var(--border)] px-4 py-3 sm:px-5">
    <Select value={agent.id} onValueChange={onSelectAgent}>
     <SelectTrigger aria-label="Select agent" className="h-11 w-auto min-w-[140px] max-w-[220px] shrink-0 justify-start gap-2 border-[var(--border)] bg-[var(--card)] px-2.5 text-sm font-semibold shadow-none hover:bg-[var(--secondary)]">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-full border border-[var(--border)] bg-[var(--background)]"><Blobatar name={agent.name} size={26} className="h-full w-full object-contain" /></span>
      <SelectValue className="min-w-0 max-w-[150px] flex-none truncate" placeholder="Choose agent" />
     </SelectTrigger>
     <SelectContent>{agents.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}</SelectContent>
    </Select>
    <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-4 gap-y-2 text-xs text-[var(--muted-foreground)]">
     <span className="flex shrink-0 items-center gap-2"><span className="text-[var(--foreground)]">Task Engine</span>
      <Select value={agent.engine} onValueChange={handleEngineChange}>
       <SelectTrigger aria-label="Select engine" className="h-8 w-[132px] bg-[var(--card)] text-xs"><SelectValue placeholder={engineLabel} /></SelectTrigger>
       <SelectContent>
        <SelectItem value="opencode_run">OpenCode</SelectItem>
        <SelectItem value="kilo_run">Kilo Code</SelectItem>
        <SelectItem value="antigravity_run">Antigravity</SelectItem>
        <SelectItem value="groq">Groq</SelectItem>
       </SelectContent>
      </Select>
     </span>
     <span className="flex min-w-0 flex-wrap items-center gap-2"><span className="shrink-0 text-[var(--foreground)]">Engine Model</span>
      <Select value={agent.model || modelOptions[0]?.id || ''} onValueChange={(model) => onUpdateAgent?.({ model })}>
       <SelectTrigger aria-label="Select model" className="h-8 w-[clamp(9rem,22vw,13.75rem)] max-w-full bg-[var(--card)] text-xs"><SelectValue placeholder={modelLabel} /></SelectTrigger>
       <SelectContent>
        {agent.model && !modelOptions.some((model) => model.id === agent.model) && <SelectItem value={agent.model}>{modelLabel}</SelectItem>}
        {modelOptions.map((model) => <SelectItem key={model.id} value={model.id}>{model.label}</SelectItem>)}
       </SelectContent>
      </Select>
     </span>
    </div>
   </header>
   <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
    <input ref={fileInputRef} type="file" multiple className="hidden" onChange={(event) => void handleFileUpload(event.target.files)} aria-label="Attach files to agent chat" />
    <AgentChatRuntime key={`${agent.id}-${activeThreadId}`} agent={agent} workspace={currentWorkspace} conversationId={activeThreadId.startsWith('conv_') ? activeThreadId : undefined} threadMessages={activeThread?.messages || []} uploadedFiles={uploadedFiles} onAttachFile={() => fileInputRef.current?.click()} onRemoveFile={(index) => setUploadedFiles((previous) => previous.filter((_, itemIndex) => itemIndex !== index))} onUpdateAgentStatus={onUpdateAgentStatus} onConversationComplete={handleConversationComplete} />
   </div>
  </main>

  <aside className="hidden min-h-0 flex-col border-l border-[var(--border)] bg-[var(--card)]/35 xl:flex">
   <div className="border-b border-[var(--border)] px-4 py-3">
    <h2 className="text-sm font-semibold text-[var(--foreground)]">Workspace</h2>
    <p className="mt-1 truncate text-xs text-[var(--muted-foreground)]" title={currentWorkspace}>{currentWorkspace || 'No folder selected'}</p>
    <Button variant="outline" size="sm" onClick={handleBrowseWorkspace} className="mt-3 h-8 w-full gap-2"><FolderOpen className="h-4 w-4" />Change folder</Button>
   </div>
   <div className="min-h-0 flex-1 overflow-y-auto p-3">
    <div className="mb-2 flex items-center justify-between">
     <h3 className="text-xs font-semibold text-[var(--foreground)]">Files</h3>
     <span className="text-[10px] text-[var(--muted-foreground)]">{workspaceFiles.length}</span>
    </div>
    {workspaceFiles.length ? workspaceFiles.map((file, index) => <div key={`${file.path || file.name}-${index}`} className="flex items-center gap-2 rounded px-2 py-2 text-xs text-[var(--muted-foreground)]"><FileText className="h-3.5 w-3.5 shrink-0" /><span className="truncate" title={file.path}>{file.name}</span></div>) : <p className="px-2 py-3 text-xs leading-relaxed text-[var(--muted-foreground)]">Files attached in ZEZO appear here.</p>}
   </div>
  </aside>
 </Frame>
 )
}

interface AgentChatRuntimeProps {
 agent: AgentOfficeMember
 workspace: string
 conversationId?: string
 threadMessages: ThreadMessageLike[]
 uploadedFiles: { name: string; size: string; type: string }[]
 onAttachFile: () => void
 onRemoveFile: (index: number) => void
 onUpdateAgentStatus?: AgentDirectChatViewProps['onUpdateAgentStatus']
 onConversationComplete: (userText: string, replyText: string, messages: ThreadMessageLike[], toolExecutions?: any[]) => void
}

function AgentChatRuntime({ agent, workspace, conversationId, threadMessages, uploadedFiles, onAttachFile, onRemoveFile, onUpdateAgentStatus, onConversationComplete }: AgentChatRuntimeProps) {
  const runtime = useLocalRuntime({
    async *run({ messages, abortSignal }) {
      const userText = messages[messages.length - 1]?.content?.map((part) => part.type === 'text' ? part.text : '').join('').trim() || ''
      if (!userText) return
      onUpdateAgentStatus?.(agent.id, 'WORKING', `Thinking: "${userText.slice(0, 24)}..."`)
      let currentText = ''
      let finalTaskDispatched: string | undefined

      try {
        // Real Server-Sent Events (SSE) streaming from backend
        for await (const chunk of api.streamAgentChat(agent.id, userText, agent.engine, agent.model, workspace, conversationId, abortSignal)) {
          if (abortSignal?.aborted) {
            break
          }
          if (chunk.type === 'status') {
            if (chunk.message) {
              onUpdateAgentStatus?.(agent.id, 'WORKING', chunk.message)
            }
          } else if (chunk.type === 'task_dispatched') {
            finalTaskDispatched = chunk.task_id
            onUpdateAgentStatus?.(agent.id, 'WORKING', `Executing task ${chunk.task_id}...`)
          } else if (chunk.type === 'chunk' && chunk.text) {
            currentText += chunk.text
            yield {
              content: [{ type: 'text' as const, text: currentText }],
            }
          } else if (chunk.type === 'done') {
            if (chunk.reply && !currentText) {
              currentText = chunk.reply
              yield {
                content: [{ type: 'text' as const, text: currentText }],
              }
            }
          } else if (chunk.type === 'error') {
            currentText += `\n\n⚠️ **Error**: ${chunk.error || 'Stream error'}`
            yield {
              content: [{ type: 'text' as const, text: currentText }],
            }
          }
        }

        const replyText = currentText || `Task started with ${agent.engine}. (ID: ${finalTaskDispatched || 'active'})`
        const savedMessages: ThreadMessageLike[] = [
          { id: `user-${Date.now()}`, role: 'user', content: [{ type: 'text', text: userText }] },
          { id: `assistant-${Date.now()}`, role: 'assistant', content: [{ type: 'text', text: replyText }], status: { type: 'complete', reason: 'stop' } },
        ]
        onConversationComplete(userText, replyText, savedMessages)
      } catch (error: any) {
        if (abortSignal?.aborted) {
          console.info('Agent chat stream aborted by user.')
          return
        }
        console.error('Agent chat stream error:', error)
        yield { content: [{ type: 'text', text: `⚠️ **Agent Stream Error**: ${error?.message || 'Failed to communicate with agent backend.'}` }] }
      } finally {
        onUpdateAgentStatus?.(agent.id, 'IDLE')
      }
    },
  }, { initialMessages: threadMessages })

  return <AssistantRuntimeProvider runtime={runtime}><AgentChatThread agent={agent} className="h-full min-h-0" onAttachFile={onAttachFile} uploadedFiles={uploadedFiles} onRemoveFile={onRemoveFile} /></AssistantRuntimeProvider>
}
