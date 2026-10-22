import React, { useState, useRef, useEffect } from 'react'
import { 
 ArrowUp, 
 Terminal, 
 ChevronRight, 
 ChevronDown, 
 Sparkles,
 Paperclip,
 Code2
} from 'lucide-react'
import { ChatAvatarIcon } from '../avatar/ChatAvatarIcon'
import type { ChatMessage, AgentProfile } from '../../types/zezo'

interface ChatPanelProps {
 messages: ChatMessage[]
 currentAgent: AgentProfile | null
 isStreaming: boolean
 onSendMessage: (text: string) => void
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
 messages,
 currentAgent,
 isStreaming,
 onSendMessage,
}) => {
 const [input, setInput] = useState('')
 const [collapsedTools, setCollapsedTools] = useState<Record<string, boolean>>({})
 const scrollRef = useRef<HTMLDivElement>(null)

 useEffect(() => {
 if (scrollRef.current) {
 scrollRef.current.scrollTop = scrollRef.current.scrollHeight
 }
 }, [messages, isStreaming])

 const toggleToolCollapse = (id: string) => {
 setCollapsedTools((prev) => ({ ...prev, [id]: !prev[id] }))
 }

 const handleSend = () => {
 if (!input.trim() || isStreaming) return
 onSendMessage(input.trim())
 setInput('')
 }

 return (
 <div className="flex flex-col h-full bg-[#121110] text-[#e4e0d8] border border-white/10 rounded-xl overflow-hidden ">
 {/* Top Banner with Active Agent Context */}
 <div className="px-4 py-3 bg-[#1a1918]/80 border-b border-white/10 flex items-center justify-between">
 <div className="flex items-center gap-2.5">
 <div 
 className="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs text-[#121110] "
 style={{ backgroundColor: currentAgent?.color || '#e4e0d8' }}
 >
 {currentAgent?.avatar_pixel || currentAgent?.displayName?.[0] || 'Z'}
 </div>
 <div>
 <div className="flex items-center gap-1.5 leading-none">
 <span className="font-semibold text-xs text-[#e4e0d8]">
 {currentAgent ? currentAgent.displayName || currentAgent.name : 'ZEZO Orchestrator'}
 </span>
 <span className="text-[10px] bg-white/5 text-[#d8d2c8] font-mono px-1.5 py-0.5 rounded border border-white/10">
 {currentAgent?.model_id || 'gemini-2.5-flash'}
 </span>
 </div>
 <div className="text-[10px] text-[#9a948a] leading-tight">
 {currentAgent?.specialty || 'Central Agentic Voice & Desktop Executive'}
 </div>
 </div>
 </div>

 <div className="flex items-center gap-2 text-[11px] text-[#9a948a] font-mono">
 <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
 <span>Interactive Session</span>
 </div>
 </div>

 {/* Message Stream */}
 <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
 {messages.length === 0 ? (
 <div className="h-full flex flex-col items-center justify-center text-center text-[#9a948a] space-y-3 p-6">
 <div className="w-12 h-12 rounded-2xl bg-[#1a1918] border border-white/10 flex items-center justify-center text-[#e2d8ca] ">
 <Sparkles className="w-6 h-6" />
 </div>
 <div>
 <p className="text-sm font-semibold text-[#e4e0d8]">Autonomous Assistant Ready</p>
 <p className="text-xs text-[#9a948a] max-w-sm mt-1">
 Ask {currentAgent?.displayName || 'ZEZO'} to analyze code, refactor components, trigger fleet agents, or control desktop settings.
 </p>
 </div>
 </div>
 ) : (
 messages.map((msg) => {
 const isUser = msg.sender === 'user'

 // Render Tool Call Card (Assistant-UI & AI-SDK Style)
 if (msg.type === 'tool_call' && msg.toolMeta) {
 const isCollapsed = collapsedTools[msg.id] ?? false
 return (
 <div key={msg.id} className="my-2 max-w-2xl mx-auto rounded-lg border border-white/10 bg-[#1a1918]/60 overflow-hidden font-mono text-xs">
 <div 
 onClick={() => toggleToolCollapse(msg.id)}
 className="p-2.5 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors"
 >
 <div className="flex items-center gap-2">
 <Terminal className="w-3.5 h-3.5 text-[#e2d8ca]" />
 <span className="font-semibold text-[#e4e0d8]">{msg.toolMeta.toolName}</span>
 <span className="text-[10px] text-[#9a948a] px-1.5 py-0.5 rounded bg-[#121110] border border-white/10">
 {msg.toolMeta.status}
 </span>
 </div>
 {isCollapsed ? <ChevronRight className="w-3.5 h-3.5 text-[#9a948a]" /> : <ChevronDown className="w-3.5 h-3.5 text-[#9a948a]" />}
 </div>

 {!isCollapsed && msg.toolMeta.output && (
 <div className="p-3 bg-[#121110] border-t border-white/10 text-[11px] text-[#d8d2c8] max-h-48 overflow-y-auto whitespace-pre-wrap">
 {msg.toolMeta.output}
 </div>
 )}
 </div>
 )
 }

 // Normal Message Bubble
 return (
 <div
 key={msg.id}
 className={`flex gap-3 max-w-2xl ${isUser ? 'ml-auto' : 'mr-auto'}`}
 >
 {!isUser && (
 <div className="w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-semibold overflow-hidden bg-card border border-border">
 <ChatAvatarIcon size={26} expression="happy" />
 </div>
 )}

 <div
 className={`px-3.5 py-2.5 rounded-2xl text-xs leading-relaxed ${
 isUser
 ? 'bg-[#e4e0d8] text-[#121110] font-medium rounded-tr-none '
 : 'bg-[#1a1918] border border-white/10 text-[#e4e0d8] rounded-tl-none '
 }`}
 >
 <div className="whitespace-pre-wrap">{msg.text}</div>
 <div
 className={`mt-1 text-[10px] font-mono ${
 isUser ? 'text-[#5a544c] text-right' : 'text-[#9a948a]'
 }`}
 >
 {msg.time}
 </div>
 </div>
 </div>
 )
 })
 )}

 {isStreaming && (
 <div className="flex gap-3 max-w-2xl mr-auto">
 <div className="w-7 h-7 rounded-full bg-card border border-border shrink-0 flex items-center justify-center overflow-hidden">
 <ChatAvatarIcon size={26} expression="curious" state="talking" />
 </div>
 <div className="px-3.5 py-2.5 rounded-2xl bg-[#1a1918] border border-white/10 text-[#9a948a] text-xs rounded-tl-none flex items-center gap-2">
 <span className="w-2 h-2 rounded-full bg-[#e2d8ca] animate-ping" />
 <span>Generating response...</span>
 </div>
 </div>
 )}
 </div>

 {/* Auto-Resizing Prompt Input Box (assistant-ui aesthetic) */}
 <div className="p-3 bg-[#1a1918]/70 border-t border-white/10">
 <div className="relative rounded-xl bg-[#121110] border border-white/10 focus-within:border-[#e4e0d8]/80 transition-all p-2 flex flex-col gap-2 ">
 <textarea
 value={input}
 onChange={(e) => setInput(e.target.value)}
 onKeyDown={(e) => {
 if (e.key === 'Enter' && !e.shiftKey) {
 e.preventDefault()
 handleSend()
 }
 }}
 placeholder={`Message ${currentAgent?.displayName || 'ZEZO'}... (Enter to send, Shift+Enter for new line)`}
 rows={2}
 className="w-full bg-transparent text-xs text-[#e4e0d8] placeholder:text-[#9a948a] resize-none focus:outline-hidden px-1"
 />

 <div className="flex items-center justify-between pt-1 border-t border-white/5">
 <div className="flex items-center gap-1.5 text-[#9a948a] text-xs">
 <button className="p-1 hover:text-[#e4e0d8] rounded-md hover:bg-white/5 transition-colors" title="Attach file or context">
 <Paperclip className="w-3.5 h-3.5" />
 </button>
 <button className="p-1 hover:text-[#e4e0d8] rounded-md hover:bg-white/5 transition-colors" title="Insert code snippet">
 <Code2 className="w-3.5 h-3.5" />
 </button>
 </div>

 <button
 onClick={handleSend}
 disabled={!input.trim() || isStreaming}
 className={`w-7 h-7 rounded-full flex items-center justify-center transition-all ${
 input.trim() && !isStreaming
 ? 'bg-[#e4e0d8] hover:bg-white text-[#121110] font-medium /5 active:scale-95'
 : 'bg-white/5 text-[#9a948a] cursor-not-allowed'
 }`}
 >
 <ArrowUp className="w-3.5 h-3.5" />
 </button>
 </div>
 </div>
 </div>
 </div>
 )
}
