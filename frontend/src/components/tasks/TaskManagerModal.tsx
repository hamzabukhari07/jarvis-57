import React, { useState, useEffect, useMemo } from 'react'
import {
 Dialog,
 DialogContent,
 DialogHeader,
 DialogTitle,
 DialogDescription,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Badge } from '../reui/badge'
import { Progress } from '../ui/progress'
import { ScrollArea } from '../ui/scroll-area'
import {
 Layers,
 Activity,
 CheckCircle2,
 Clock,
 AlertTriangle,
 StopCircle,
 Copy,
 Check,
 Search,
 RefreshCw,
 ExternalLink,
 X,
} from 'lucide-react'
import { api } from '../../lib/api'

interface TaskManagerModalProps {
 isOpen: boolean
 onClose: () => void
 onCancelTask?: (taskId: string) => void
 tasks?: any[]
}

export const TaskManagerModal: React.FC<TaskManagerModalProps> = ({
 isOpen,
 onClose,
 onCancelTask,
 tasks: initialTasks,
}) => {
 const [tasks, setTasks] = useState<any[]>(initialTasks || [])
 const [isLoading, setIsLoading] = useState(false)
 const [searchQuery, setSearchQuery] = useState('')
 const [statusFilter, setStatusFilter] = useState<'ALL' | 'RUNNING' | 'QUEUED' | 'DONE' | 'FAILED'>('ALL')
 const [selectedTask, setSelectedTask] = useState<any | null>(null)
 const [isDetailOpen, setIsDetailOpen] = useState(false)
 const [copiedId, setCopiedId] = useState<string | null>(null)
 const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())

 // Keep tasks synced with live tasks passed from parent socket
 useEffect(() => {
 if (initialTasks && Array.isArray(initialTasks) && initialTasks.length > 0) {
 setTasks(initialTasks)
 }
 }, [initialTasks])

 const fetchTasks = async () => {
 setIsLoading(true)
 try {
 const list = await api.getTasks()
 if (Array.isArray(list) && list.length > 0) {
 setTasks(list)
 } else if (!initialTasks || initialTasks.length === 0) {
 setTasks(list || [])
 }
 } catch {
 // Offline fallback
 } finally {
 setIsLoading(false)
 }
 }

 useEffect(() => {
 if (isOpen) {
 fetchTasks()
 const interval = setInterval(fetchTasks, 3000)
 return () => clearInterval(interval)
 }
 }, [isOpen])

 // KPI counts
 const kpis = useMemo(() => {
 let running = 0
 let queued = 0
 let done = 0
 let failed = 0

 tasks.forEach((t) => {
 const s = (t.status || '').toLowerCase()
 if (s === 'running') running++
 else if (s === 'queued' || s === 'created') queued++
 else if (s === 'done' || s === 'completed') done++
 else if (s === 'failed' || s === 'cancelled') failed++
 })

 return { running, queued, done, failed, total: tasks.length }
 }, [tasks])

 // Group tasks by group_id for nested display
 const groupedTasks = useMemo(() => {
   const grouped = new Map<string, { parent: any; children: any[] }>()
   
   // Build a map of all parent-child relationships
   tasks.forEach((t) => {
     const groupId = t.group_id
     
     if (groupId) {
       if (!grouped.has(groupId)) {
         // Find the parent task
         const parent = tasks.find(task => task.id === groupId)
         if (parent) {
           grouped.set(groupId, { parent, children: [] })
         } else {
           grouped.set(groupId, { parent: null, children: [] })
         }
       }
       
       // Add this task as a child if it has parent_id
       if (t.parent_id === groupId) {
         const group = grouped.get(groupId)
         if (group) {
           group.children.push(t)
         }
       }
     }
   })
   
   return grouped
 }, [tasks])
 
 // Filter tasks
 const filteredTasks = useMemo(() => {
   return tasks.filter((t) => {
     const s = (t.status || "").toLowerCase()
 
     // Apply status filter
     if (statusFilter === "RUNNING" && s !== "running") return false
     if (statusFilter === "QUEUED" && s !== "queued" && s !== "created") return false
     if (statusFilter === "DONE" && s !== "done" && s !== "completed") return false
     if (statusFilter === "FAILED" && s !== "failed" && s !== "cancelled") return false
 
     // Hide child tasks that have parent - they will be shown nested
     if (t.parent_id) {
       const parent = tasks.find(task => task.id === t.parent_id)
       if (parent) {
         return false
       }
     }
 
     if (searchQuery.trim()) {
       const q = searchQuery.toLowerCase()
       const matchTitle = (
         t.prompt ||
         t.description ||
         t.message ||
         t.group_title ||
         t.params?.taskTitle ||
         t.params?.task ||
         t.params?.target ||
         t.params?.query ||
         ""
       ).toLowerCase().includes(q)
       const matchId = (t.id || "").toLowerCase().includes(q)
       const matchTool = (t.tool || t.engine || "").toLowerCase().includes(q)
       
       if (matchTitle || matchId || matchTool) return true
       
       // Check if any child of this task matches search
       if (groupedTasks.has(t.id)) {
         const group = groupedTasks.get(t.id)
         if (group?.children.some(child => {
           const childTitle = (
             child.prompt ||
             child.description ||
             child.message ||
             child.group_title ||
             child.params?.taskTitle ||
             child.params?.task ||
             child.params?.target ||
             child.params?.query ||
             ""
           ).toLowerCase().includes(q)
           const childId = (child.id || "").toLowerCase().includes(q)
           const childTool = (child.tool || child.engine || "").toLowerCase().includes(q)
           return childTitle || childId || childTool
         })) {
           return true
         }
       }
       
       return false
     }
 
     return true
   })
 }, [tasks, searchQuery, statusFilter, groupedTasks])

 const handleCopy = async (text: string, id: string) => {
 try {
 await navigator.clipboard.writeText(text)
 setCopiedId(id)
 setTimeout(() => setCopiedId(null), 1500)
 } catch (e) {
 console.warn('Copy failed:', e)
 }
 }

 const getStatusBadge = (status: string) => {
 const s = (status || '').toLowerCase()
 if (s === 'running') {
 return (
 <Badge variant="running" size="xs" className="gap-1">
 <span className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] animate-pulse" />
 RUNNING
 </Badge>
 )
 }
 if (s === 'done' || s === 'completed') {
 return (
 <Badge variant="success" size="xs" className="gap-1">
 <CheckCircle2 className="w-2.5 h-2.5" />
 COMPLETED
 </Badge>
 )
 }
 if (s === 'failed' || s === 'cancelled') {
 return (
 <Badge variant="destructive" size="xs" className="gap-1">
 <AlertTriangle className="w-2.5 h-2.5" />
 {status.toUpperCase()}
 </Badge>
 )
 }
 return (
 <Badge variant="queued" size="xs" className="gap-1">
 <Clock className="w-2.5 h-2.5" />
 QUEUED
 </Badge>
 )
 }

 return (
 <>
 <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
 <DialogContent hideCloseButton className="max-w-4xl w-[95vw] bg-[var(--card)] border border-[var(--border)] p-0 overflow-hidden text-[var(--foreground)] flex flex-col h-[85vh] gap-0 rounded-[var(--radius)]">
 {/* Header */}
 <DialogHeader className="px-5 py-3.5 border-b border-[var(--border)] bg-[var(--card)] shrink-0">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-2.5">
 <div className="w-8 h-8 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--primary)]/10 border border-[var(--primary)]/20 flex items-center justify-center text-[var(--primary)] ">
 <Layers className="w-4 h-4" />
 </div>
 <div className="flex items-center gap-2">
 <DialogTitle className="text-sm font-semibold text-[var(--foreground)]">
 Task Matrix & Registry
 </DialogTitle>
 </div>
 </div>

 <div className="flex items-center gap-2">
 <Button
 size="sm"
 variant="outline"
 onClick={fetchTasks}
 disabled={isLoading}
 className="h-7 px-2.5 text-[11px] font-mono gap-1.5"
 >
 <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
 <span>REFRESH</span>
 </Button>
 <Button
 variant="ghost"
 size="sm"
 onClick={onClose}
 className="h-7 w-7 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)] rounded-md"
 >
 <X className="w-4 h-4" />
 </Button>
 </div>
 </div>
 <DialogDescription className="sr-only">Autonomous process registry and background worker telemetry</DialogDescription>
 </DialogHeader>

 {/* Compact KPI Summary Strip */}
 <div className="grid grid-cols-4 gap-2.5 px-5 py-3 bg-[var(--background)]/60 border-b border-[var(--border)] shrink-0">
 <div className="px-3 py-2 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--card)] border border-[var(--border)] flex items-center justify-between ">
 <div className="flex items-center gap-1.5 text-[11px] font-mono text-[var(--muted-foreground)]">
 <Activity className="w-3.5 h-3.5 text-amber-400" />
 <span>Running</span>
 </div>
 <span className="text-base font-bold font-mono text-amber-400">{kpis.running}</span>
 </div>

 <div className="px-3 py-2 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--card)] border border-[var(--border)] flex items-center justify-between ">
 <div className="flex items-center gap-1.5 text-[11px] font-mono text-[var(--muted-foreground)]">
 <Clock className="w-3.5 h-3.5 text-sky-400" />
 <span>Queued</span>
 </div>
 <span className="text-base font-bold font-mono text-sky-400">{kpis.queued}</span>
 </div>

 <div className="px-3 py-2 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--card)] border border-[var(--border)] flex items-center justify-between ">
 <div className="flex items-center gap-1.5 text-[11px] font-mono text-[var(--muted-foreground)]">
 <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
 <span>Done</span>
 </div>
 <span className="text-base font-bold font-mono text-emerald-400">{kpis.done}</span>
 </div>

 <div className="px-3 py-2 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--card)] border border-[var(--border)] flex items-center justify-between ">
 <div className="flex items-center gap-1.5 text-[11px] font-mono text-[var(--muted-foreground)]">
 <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
 <span>Failed</span>
 </div>
 <span className="text-base font-bold font-mono text-red-400">{kpis.failed}</span>
 </div>
 </div>

 {/* Search & Filter Toolbar */}
 <div className="px-5 py-2.5 border-b border-[var(--border)] bg-[var(--card)] flex flex-wrap items-center justify-between gap-2 shrink-0">
 <div className="flex items-center gap-1.5">
 {(['ALL', 'RUNNING', 'QUEUED', 'DONE', 'FAILED'] as const).map((st) => (
 <Button
 key={st}
 size="sm"
 variant={statusFilter === st ? 'default' : 'outline'}
 onClick={() => setStatusFilter(st)}
 className={`h-7 px-2.5 text-[11px] font-mono ${
 statusFilter === st ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : ''
 }`}
 >
 {st}
 </Button>
 ))}
 </div>

 <div className="relative w-52">
 <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-[var(--muted-foreground)] pointer-events-none" />
 <Input
 placeholder="Search tasks..."
 value={searchQuery}
 onChange={(e) => setSearchQuery(e.target.value)}
 className="h-7 pl-8 text-xs font-mono bg-[var(--input)] border-[var(--border)]"
 />
 </div>
 </div>

 {/* Tasks List */}
 <div className="flex-1 min-h-0 p-5 overflow-hidden bg-[var(--background)]">
 <ScrollArea className="h-full pr-3">
 {filteredTasks.length === 0 ? (
 <div className="flex flex-col items-center justify-center h-64 text-[var(--muted-foreground)] space-y-1.5 font-mono text-xs">
 <Layers className="w-8 h-8 opacity-25" />
 <p className="font-semibold">No tasks in registry</p>
 </div>
 ) : (
 <div className="space-y-2.5">
 {filteredTasks.map((t) => {
 const st = (t.status || '').toLowerCase()
 const isRunning = st === 'running'
 const isDone = st === 'done' || st === 'completed'
 const progressVal = t.progress !== undefined ? t.progress : isDone ? 100 : isRunning ? 50 : 0
 const children = groupedTasks.has(t.id) ? groupedTasks.get(t.id)?.children || [] : []

 return (
 <div
 key={t.id}
 className="p-3 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition-all space-y-2 "
 >
 {/* Task Top Row */}
 <div className="flex items-center justify-between gap-2">
 <div className="flex items-center gap-2">
 <Badge variant="outline" className="text-[10px] font-mono text-[var(--foreground)] bg-[var(--input)] border-[var(--border)]">
 {t.tool || 'AGENT_TASK'}
 </Badge>
 <span className="font-mono text-[11px] text-[var(--muted-foreground)]">#{t.id}</span>
 </div>

 <div className="flex items-center gap-2">
 {getStatusBadge(t.status)}
 <Button
 size="sm"
 variant="outline"
 onClick={() => {
 setSelectedTask(t)
 setIsDetailOpen(true)
 }}
 className="h-6 px-2 text-[10px] font-mono gap-1"
 >
 <ExternalLink className="w-2.5 h-2.5" />
 <span>INSPECT</span>
 </Button>
 </div>
 </div>

 {/* Title */}
 <div className="text-xs font-semibold text-[var(--foreground)] line-clamp-2 break-all">
 {t.prompt || t.group_title || t.params?.taskTitle || t.params?.task || t.params?.target || t.description || t.message || 'Executing agentic synthesis'}
 </div>

 {/* Progress Bar */}
 <div className="space-y-1">
 <div className="flex items-center justify-between text-[10px] font-mono text-[var(--muted-foreground)]">
 <span>Progress</span>
 <span>{progressVal}%</span>
 </div>
 <Progress value={progressVal} className="h-1.5" />
 </div>

 {/* Nested child tasks (subtasks) - collapsible */}
 {children.length > 0 && (
 <div className="mt-2">
 <button
 onClick={() => setExpandedTasks(prev => {
   const next = new Set(prev)
   if (next.has(t.id)) { next.delete(t.id) } else { next.add(t.id) }
   return next
 })}
 className="text-[10px] font-mono text-[var(--primary)] hover:underline mb-1.5 flex items-center gap-1"
 >
 {expandedTasks.has(t.id) ? '[-]' : '[+]'} {children.length} step{children.length > 1 ? 's' : ''}
 </button>
 {expandedTasks.has(t.id) && (
 <div className="pl-3 border-l-2 border-[var(--primary)]/30 space-y-2">
 {children.map((child) => {
 const cSt = (child.status || '').toLowerCase()
 const cIsDone = cSt === 'done' || cSt === 'completed'
 const cProgress = child.progress !== undefined ? child.progress : cIsDone ? 100 : 0
 return (
 <div key={child.id} className="p-2 rounded bg-[var(--background)] border border-[var(--border)]/50 space-y-1.5">
 <div className="flex items-center justify-between gap-2">
 <Badge variant="outline" className="text-[9px] font-mono">{child.tool || 'AGENT_TASK'}</Badge>
 <span className="text-[9px] font-mono text-[var(--muted-foreground)]">#{child.id}</span>
 {getStatusBadge(child.status)}
 </div>
 <div className="text-[10px] text-[var(--foreground)] line-clamp-1">
 {child.prompt || child.group_title || child.params?.taskTitle || 'Executing...'}
 </div>
 <div className="flex items-center gap-2">
 <Progress value={cProgress} className="h-1 flex-1" />
 <span className="text-[9px] font-mono text-[var(--muted-foreground)]">{cProgress}%</span>
 </div>
 </div>
 )
 })}
 </div>
 )}
 </div>
 )}

 {/* Metadata Footer */}
 <div className="pt-1 flex items-center justify-between text-[10px] font-mono text-[var(--muted-foreground)] border-t border-[var(--border)]/30">
 <div className="flex items-center gap-3">
 {t.model && <span>Model: {t.model}</span>}
 {t.started_at && <span>Started: {t.started_at}</span>}
 {t.duration && <span>Duration: {t.duration}</span>}
 </div>

 <div className="flex items-center gap-2">
 {isRunning && onCancelTask && (
 <Button
 size="sm"
 variant="destructive"
 onClick={() => onCancelTask(t.id)}
 className="h-5 px-1.5 text-[9px] font-mono gap-1"
 >
 <StopCircle className="w-2.5 h-2.5" />
 <span>CANCEL</span>
 </Button>
 )}

 <Button
 size="sm"
 variant="ghost"
 onClick={() => handleCopy(JSON.stringify(t, null, 2), t.id)}
 className="h-5 px-1 text-[9px] font-mono text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
 >
 {copiedId === t.id ? (
 <Check className="w-2.5 h-2.5 text-emerald-400" />
 ) : (
 <Copy className="w-2.5 h-2.5" />
 )}
 </Button>
 </div>
 </div>
 </div>
 )
 })}
 </div>
 )}
 </ScrollArea>
 </div>
 </DialogContent>
 </Dialog>

 {/* Task Detail Modal */}
 {selectedTask && (
 <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
 <DialogContent hideCloseButton className="max-w-xl bg-[var(--card)] border border-[var(--border)] p-0 overflow-hidden text-[var(--foreground)] rounded-[var(--radius)]">
 <DialogHeader className="px-5 py-3.5 border-b border-[var(--border)] bg-[var(--card)]">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-2">
 <Badge variant="outline" className="text-[10px] font-mono text-[var(--foreground)] bg-[var(--input)] border-[var(--border)]">
 {selectedTask.tool || 'AGENT_TASK'}
 </Badge>
 <span className="font-mono text-xs text-[var(--muted-foreground)]">#{selectedTask.id}</span>
 </div>
 <div className="flex items-center gap-2">
 {getStatusBadge(selectedTask.status)}
 <Button
 variant="ghost"
 size="sm"
 onClick={() => setIsDetailOpen(false)}
 className="h-6 w-6 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)] rounded-md"
 >
 <X className="w-3.5 h-3.5" />
 </Button>
 </div>
 </div>
 <DialogTitle className="text-sm font-semibold text-[var(--foreground)] mt-2 leading-snug">
 {selectedTask.prompt || selectedTask.description || selectedTask.message || 'Task Overview'}
 </DialogTitle>
 <DialogDescription className="sr-only">Task execution inspector</DialogDescription>
 </DialogHeader>

 <div className="p-5 space-y-4 text-xs font-mono">
 {/* Progress */}
 <div className="space-y-1.5">
 <div className="flex items-center justify-between text-[11px]">
 <span className="text-[var(--muted-foreground)]">Progress</span>
 <span className="font-bold text-[var(--foreground)]">{selectedTask.progress || 0}%</span>
 </div>
 <Progress value={selectedTask.progress || 0} className="h-2" />
 </div>

 {/* Details grid */}
 <div className="rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] border border-[var(--border)] bg-[var(--input)]/60 p-3 space-y-2 text-[11px]">
 <div className="flex justify-between">
 <span className="text-[var(--muted-foreground)]">Engine:</span>
 <span className="text-[var(--foreground)] font-semibold">{selectedTask.tool || 'Autonomous Agent'}</span>
 </div>
 <div className="flex justify-between">
 <span className="text-[var(--muted-foreground)]">Model:</span>
 <span className="text-[var(--primary)] font-semibold">{selectedTask.model || 'Gemini 3.1 Flash'}</span>
 </div>
 {selectedTask.started_at && (
 <div className="flex justify-between">
 <span className="text-[var(--muted-foreground)]">Started:</span>
 <span className="text-[var(--foreground)]">{selectedTask.started_at}</span>
 </div>
 )}
 {selectedTask.duration && (
 <div className="flex justify-between">
 <span className="text-[var(--muted-foreground)]">Duration:</span>
 <span className="text-[var(--foreground)]">{selectedTask.duration}</span>
 </div>
 )}
 </div>

 {/* Logs */}
 {selectedTask.logs && (
 <div className="space-y-1.5">
 <div className="text-[10px] text-[var(--muted-foreground)] uppercase tracking-wider">Execution Logs</div>
 <div className="bg-[var(--background)] p-3 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] border border-[var(--border)] text-[10px] text-[var(--foreground)] max-h-40 overflow-y-auto whitespace-pre-wrap">
 {Array.isArray(selectedTask.logs)
   ? selectedTask.logs
       .map((l: string | { time?: string; text?: string; progress?: number }) => (typeof l === 'string' ? l : `${l?.time ?? ''} ${l?.text ?? ''}`.trim()))
       .join('\n')
   : String(selectedTask.logs)}
 </div>
 </div>
 )}
 </div>

 {/* Actions */}
 <div className="px-5 py-3 border-t border-[var(--border)] bg-[var(--card)] flex items-center justify-between">
 {(selectedTask.status || '').toLowerCase() === 'running' && onCancelTask ? (
 <Button
 size="sm"
 variant="destructive"
 onClick={() => {
 onCancelTask(selectedTask.id)
 setIsDetailOpen(false)
 }}
 className="h-7 text-xs font-mono gap-1.5"
 >
 <StopCircle className="w-3.5 h-3.5" />
 <span>CANCEL TASK</span>
 </Button>
 ) : (
 <div />
 )}

 <Button
 size="sm"
 variant="outline"
 onClick={() => handleCopy(JSON.stringify(selectedTask, null, 2), 'detail')}
 className="h-7 text-xs font-mono gap-1.5"
 >
 {copiedId === 'detail' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
 <span>COPY PARAMS</span>
 </Button>
 </div>
 </DialogContent>
 </Dialog>
 )}
 </>
 )
}
