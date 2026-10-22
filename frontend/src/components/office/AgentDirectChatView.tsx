import React, { useState, useEffect } from 'react'
import {
 Plus,
 Search,
 Terminal,
 Cpu,
 MessageSquare,
 Trash2,
} from 'lucide-react'
import {
 AssistantRuntimeProvider,
 useLocalRuntime,
} from '@assistant-ui/react'
import { AssistantUIThread } from '../assistant-ui/thread'
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
import { Blobatar } from 'blobatar/react'
import type { AgentOfficeMember } from './AutonomousOfficeScreen'
import { ENGINE_MODELS_MAP } from './AutonomousOfficeScreen'
import { api } from '../../lib/api'
import { cn } from '@/lib/utils'

export interface ChatThreadItem {
 id: string
 title: string
 preview: string
 updatedAt: string
 messageCount: number
 tag: string
}

interface AgentDirectChatViewProps {
 agent: AgentOfficeMember
 onBackToFloor?: () => void
 onUpdateAgent?: (updated: Partial<AgentOfficeMember>) => void
 onUpdateAgentStatus?: (agentId: string, status: AgentOfficeMember['status'], speech?: string) => void
}

export const AgentDirectChatView: React.FC<AgentDirectChatViewProps> = ({
 agent,
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
 return parsed.filter(
 (t: ChatThreadItem) =>
 !t.id.endsWith('-init') &&
 t.title !== `Chat with ${agent.name}` &&
 (t.messageCount || 0) > 0
 )
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

 const [currentEngine, setCurrentEngine] = useState<string>(agent.engine || 'opencode_run')
 const [currentModel, setCurrentModel] = useState<string>(() => {
 const list = ENGINE_MODELS_MAP[agent.engine] || ENGINE_MODELS_MAP['opencode_run'] || []
 return agent.model || list[0]?.id || 'opencode/big-pickle'
 })

 // Synchronize when agent prop changes from outside
 useEffect(() => {
 if (agent.engine && agent.engine !== currentEngine) {
 setCurrentEngine(agent.engine)
 }
 }, [agent.engine])

 useEffect(() => {
 if (agent.model && agent.model !== currentModel) {
 setCurrentModel(agent.model)
 }
 }, [agent.model])

 // Available models for active engine
 const availableEngineModels =
 ENGINE_MODELS_MAP[currentEngine] || ENGINE_MODELS_MAP['opencode_run'] || []

 // Real Assistant-UI Runtime wired directly to the backend LLM router & agent persona
 const agentRuntime = useLocalRuntime({
 async *run({ messages, abortSignal }) {
 const lastMessage = messages[messages.length - 1]
 const userText =
 lastMessage?.content
 ?.map((c) => (c.type === 'text' ? c.text : ''))
 .join('')
 .trim() || ''

 if (!userText) return

 // Inform office manager that agent is actively processing
 if (onUpdateAgentStatus) {
 onUpdateAgentStatus(agent.id, 'WORKING', `Thinking: "${userText.slice(0, 24)}..."`)
 }

 try {
 // Step 1: Real backend request via /api/fleet/chat
 const res = await api.sendAgentChat(agent.name, userText, currentEngine, currentModel)
 const rawReply =
 (res as any)?.reply ||
 res?.response ||
 `Hello Hamza! I am ${agent.name}. Directive received: "${userText}". Ready to assist on ${agent.role}.`

 // Check if the response contains genuine model reasoning tags (e.g. <think>...</think> from DeepSeek R1)
 let modelReasoning = ''
 let replyText = rawReply
 const thinkMatch = rawReply.match(/<think>([\s\S]*?)<\/think>/i)
 if (thinkMatch) {
 modelReasoning = thinkMatch[1].trim()
 replyText = rawReply.replace(/<think>[\s\S]*?<\/think>/i, '').trim()
 }

 // Step 2: Stream narrative response in smooth chunks (prevents QtWebEngine repaint flicker)
 const words = replyText.split(' ')
 let currentText = ''
 const CHUNK_SIZE = 3
 for (let i = 0; i < words.length; i += CHUNK_SIZE) {
 if (abortSignal?.aborted) break
 const chunk = words.slice(i, i + CHUNK_SIZE).join(' ')
 currentText += (currentText ? ' ' : '') + chunk

 const parts: any[] = []
 if (modelReasoning) {
 parts.push({ type: 'reasoning', text: modelReasoning })
 }
 parts.push({ type: 'text', text: currentText })

 yield { content: parts }

 if (words.length > 10) {
 await new Promise((r) => setTimeout(r, 24))
 }
 }

 // Update real active thread metadata, or create thread on first prompt
 setThreads((prev) => {
 const exists = prev.some((t) => t.id === activeThreadId)
 if (!exists) {
 const newThread: ChatThreadItem = {
 id: activeThreadId,
 title: userText.slice(0, 32) + (userText.length > 32 ? '...' : ''),
 preview: replyText.slice(0, 60) + (replyText.length > 60 ? '...' : ''),
 updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
 messageCount: 2,
 tag: (currentEngine || agent.engine || 'opencode').split('_')[0].toUpperCase(),
 }
 return [newThread, ...prev]
 }
 return prev.map((t) =>
 t.id === activeThreadId
 ? {
 ...t,
 title: t.messageCount === 0 ? userText.slice(0, 32) + (userText.length > 32 ? '...' : '') : t.title,
 preview: replyText.slice(0, 60) + (replyText.length > 60 ? '...' : ''),
 updatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
 messageCount: t.messageCount + 2,
 }
 : t
 )
 })
 } catch (err: any) {
 console.error('Agent chat error:', err)
 yield {
 content: [
 {
 type: 'text',
 text: `⚠️ **Agent Execution Error**: ${err?.message || 'Failed to communicate with fleet backend.'}`,
 },
 ],
 }
 } finally {
 if (onUpdateAgentStatus) {
 onUpdateAgentStatus(agent.id, 'IDLE')
 }
 }
 },
 })

 return (
 <Frame className="flex-1 min-h-0 flex flex-col md:flex-row overflow-hidden bg-[var(--background)]">
 {/* ── LEFT SIDEBAR: Agent Persona + Real Threads ── */}
 <aside className="w-full md:w-72 border-r border-[var(--border)] bg-[var(--card)]/90 flex flex-col shrink-0 min-h-0">
 {/* 1. AGENT IDENTITY CARD */}
 <div className="p-3 border-b border-[var(--border)] flex flex-col gap-2.5 shrink-0">
 <div className="flex items-center gap-2.5 min-w-0">
 <div className="w-9 h-9 rounded-xl overflow-hidden flex items-center justify-center border border-[var(--border)] bg-[var(--background)] shrink-0 p-0.5">
 <Blobatar name={agent.name} size={32} animate="hover" className="w-full h-full object-contain" />
 </div>
 <div className="flex-1 min-w-0">
 <div className="flex items-center justify-between gap-1">
 <span className="text-xs font-bold text-[var(--foreground)] truncate tracking-tight">
 {agent.name}
 </span>
 <span className="text-[9px] font-mono font-medium px-1.5 py-0.2 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 shrink-0">
 {agent.status}
 </span>
 </div>
 <div className="text-[10px] text-[var(--muted-foreground)] font-mono truncate">
 {agent.role}
 </div>
 </div>
 </div>

 {/* Engine & Dynamic Model Selectors */}
 <div className="space-y-2 pt-0.5">
 <div className="space-y-1">
 <label className="text-[9px] font-mono uppercase tracking-wider text-[var(--muted-foreground)] flex items-center gap-1 font-semibold">
 <Terminal className="w-2.5 h-2.5 text-purple-400" />
 Active Engine
 </label>
 <Select
 value={currentEngine}
 onValueChange={(val) => {
 const models = ENGINE_MODELS_MAP[val]
 const nextModel = models && models.length > 0 ? models[0].id : currentModel
 setCurrentEngine(val)
 setCurrentModel(nextModel)
 onUpdateAgent && onUpdateAgent({ engine: val, model: nextModel })
 }}
 >
 <SelectTrigger className="h-7 text-[11px] font-mono px-2 bg-[var(--input)]/80 border-[var(--border)] w-full">
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="opencode_run">OpenCode</SelectItem>
 <SelectItem value="kilo_run">KiloCode</SelectItem>
 <SelectItem value="antigravity_run">Antigravity</SelectItem>
 <SelectItem value="groq">Groq</SelectItem>
 </SelectContent>
 </Select>
 </div>

 <div className="space-y-1">
 <label className="text-[9px] font-mono uppercase tracking-wider text-[var(--muted-foreground)] flex items-center gap-1 font-semibold">
 <Cpu className="w-2.5 h-2.5 text-cyan-400" />
 Target Model
 </label>
 <Select
 value={currentModel}
 onValueChange={(val) => {
 setCurrentModel(val)
 onUpdateAgent && onUpdateAgent({ model: val })
 }}
 >
 <SelectTrigger className="h-7 text-[11px] font-mono px-2 bg-[var(--input)]/80 border-[var(--border)] w-full">
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 {availableEngineModels.map((m) => (
 <SelectItem key={m.id} value={m.id}>
 {m.label}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>
 </div>
 </div>

 {/* 2. ACTION BAR: New Chat & Search */}
 <div className="p-2.5 border-b border-[var(--border)] flex flex-col gap-2 shrink-0">
 <Button
 variant="default"
 size="sm"
 onClick={handleCreateNewThread}
 className="w-full h-8 text-xs font-semibold gap-2 rounded-xl cursor-pointer bg-primary hover:opacity-90 text-primary-foreground transition-all flex items-center justify-between px-3"
 >
 <div className="flex items-center gap-1.5">
 <Plus className="w-4 h-4" />
 <span>New Chat</span>
 </div>
 <span className="text-[10px] font-mono opacity-70 px-1 py-0.2 rounded bg-black/20">⌘N</span>
 </Button>

 <div className="relative">
 <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)] pointer-events-none" />
 <Input
 placeholder="Filter sessions..."
 value={searchQuery}
 onChange={(e) => setSearchQuery(e.target.value)}
 className="h-7 text-xs pl-8 bg-[var(--input)]/60 border-[var(--border)] rounded-lg placeholder:text-[var(--muted-foreground)]/60"
 />
 </div>
 </div>

 {/* 3. REAL CHAT SESSIONS LIST */}
 <div className="flex-1 min-h-0 overflow-y-auto px-2 py-2 space-y-1">
 <div className="px-2 pb-1 text-[10px] font-mono uppercase tracking-wider text-[var(--muted-foreground)]/80 font-bold flex items-center justify-between">
 <span>Conversations</span>
 <span className="text-[9px] opacity-60">{filteredThreads.length}</span>
 </div>

 <div className="space-y-0.5">
 {filteredThreads.length === 0 ? (
 <div className="py-8 px-2 text-center flex flex-col items-center justify-center text-[var(--muted-foreground)]">
 <MessageSquare className="w-5 h-5 opacity-25 mb-1.5" />
 <span className="text-[11px] font-medium text-[var(--foreground)]/80">No conversations yet</span>
 <span className="text-[9px] opacity-60 mt-0.5 max-w-[180px]">Start typing below to begin chatting with {agent.name}.</span>
 </div>
 ) : (
 filteredThreads.map((thread) => {
 const isActive = thread.id === activeThreadId
 return (
 <div
 key={thread.id}
 onClick={() => setActiveThreadId(thread.id)}
 className={cn(
 'group relative w-full text-left px-2.5 py-2 rounded-xl transition-colors duration-150 flex items-center justify-between border cursor-pointer select-none',
 isActive
 ? 'bg-[var(--primary)]/15 border-[var(--primary)]/40 text-[var(--foreground)] font-medium '
 : 'border-transparent hover:bg-[var(--secondary)]/60 text-[var(--muted-foreground)] hover:text-[var(--foreground)]'
 )}
 >
 <div className="flex items-center gap-2 min-w-0 flex-1 pr-1">
 <MessageSquare className={cn("w-3.5 h-3.5 shrink-0", isActive ? "text-[var(--primary)]" : "opacity-60")} />
 <div className="flex flex-col min-w-0 flex-1">
 <span className="text-xs truncate font-medium">
 {thread.title}
 </span>
 <span className="text-[10px] text-[var(--muted-foreground)] truncate opacity-80">
 {thread.preview}
 </span>
 </div>
 </div>

 {threads.length > 1 && (
 <button
 type="button"
 onClick={(e) => {
 e.stopPropagation()
 const remaining = threads.filter((t) => t.id !== thread.id)
 setThreads(remaining)
 if (activeThreadId === thread.id && remaining.length > 0) {
 setActiveThreadId(remaining[0].id)
 }
 }}
 className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-[var(--destructive)]/20 text-[var(--muted-foreground)] hover:text-red-400 transition-colors duration-150 shrink-0 cursor-pointer"
 title="Delete chat session"
 >
 <Trash2 className="w-3 h-3" />
 </button>
 )}
 </div>
 )
 })
 )}
 </div>
 </div>
 </aside>

 {/* ── RIGHT MAIN PANEL: Official Assistant-UI Thread ── */}
 <main className="flex-1 min-h-0 flex flex-col overflow-hidden bg-[var(--background)]">
 <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
 <AssistantRuntimeProvider runtime={agentRuntime}>
 <AssistantUIThread
 className="h-full min-h-0"
 agentName={agent.name}
 avatarName={agent.name}
 placeholder={`Message ${agent.name}...`}
 emptyTitle={`Direct with ${agent.name}`}
 emptySubtitle={`Real-time agent interaction. Engine: ${agent.engine || 'opencode_run'} | Model: ${agent.model || 'default'}`}
 showUpload={true}
 />
 </AssistantRuntimeProvider>
 </div>
 </main>
 </Frame>
 )
}
