import React, { useState, useMemo, useRef, useEffect } from 'react'
import {
 Dialog,
 DialogContent,
 DialogHeader,
 DialogTitle,
 DialogDescription,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { ScrollArea } from '../ui/scroll-area'
import {
 Select,
 SelectContent,
 SelectItem,
 SelectTrigger,
 SelectValue,
} from '../ui/select'
import {
 Terminal,
 Play,
 Pause,
 Trash2,
 Download,
 Copy,
 Check,
 Search,
 X,
} from 'lucide-react'
import type { LogEntry } from '../../hooks/useZezoSocket'

interface BackendLogModalProps {
 isOpen: boolean
 onClose: () => void
 logs: LogEntry[]
 logStats?: { total_lines?: number; max_lines?: number }
 logSources?: string[]
 onClearLogs?: () => void
}

export const BackendLogModal: React.FC<BackendLogModalProps> = ({
 isOpen,
 onClose,
 logs,
 logSources = [],
 onClearLogs,
}) => {
 const [isFollow, setIsFollow] = useState(true)
 const [isPaused, setIsPaused] = useState(false)
 const [frozenLogs, setFrozenLogs] = useState<LogEntry[]>([])
 const [searchQuery, setSearchQuery] = useState('')
 const [levelFilter, setLevelFilter] = useState('ALL')
 const [sourceFilter, setSourceFilter] = useState('ALL')
 const [copied, setCopied] = useState(false)
 const logEndRef = useRef<HTMLDivElement>(null)

 // When paused, freeze the stream
 useEffect(() => {
 if (isPaused) {
 setFrozenLogs([...logs])
 }
 }, [isPaused])

 const activeLogs = isPaused ? frozenLogs : logs

 // Filter logs based on search query, level, and source
 const filteredLogs = useMemo(() => {
 return activeLogs.filter((entry) => {
 if (levelFilter !== 'ALL') {
 const lvl = (entry.level || entry.type || '').toUpperCase()
 if (levelFilter === 'ERROR' && !lvl.includes('ERR')) return false
 if (levelFilter === 'WARNING' && !lvl.includes('WARN')) return false
 if (levelFilter === 'INFO' && !lvl.includes('INFO')) return false
 if (levelFilter === 'DEBUG' && !lvl.includes('DEBUG')) return false
 }

 if (sourceFilter !== 'ALL') {
 if ((entry.source || '').toUpperCase() !== sourceFilter.toUpperCase()) {
 return false
 }
 }

 if (searchQuery.trim()) {
 const q = searchQuery.toLowerCase()
 const textMatch = entry.text.toLowerCase().includes(q)
 const sourceMatch = entry.source.toLowerCase().includes(q)
 if (!textMatch && !sourceMatch) return false
 }

 return true
 })
 }, [activeLogs, searchQuery, levelFilter, sourceFilter])

 // Auto-scroll when follow is enabled and not paused
 useEffect(() => {
 if (isFollow && !isPaused && isOpen) {
 logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
 }
 }, [filteredLogs.length, isFollow, isPaused, isOpen])

 const handleCopyAll = async () => {
 const text = filteredLogs
 .map((l) => `[${l.time}] [${l.source}] [${l.type || 'INFO'}] ${l.text}`)
 .join('\n')
 await navigator.clipboard.writeText(text)
 setCopied(true)
 setTimeout(() => setCopied(false), 1500)
 }

 const handleExport = () => {
 const text = filteredLogs
 .map((l) => `[${l.time}] [${l.source}] [${l.type || 'INFO'}] ${l.text}`)
 .join('\n')
 const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
 const url = URL.createObjectURL(blob)
 const a = document.createElement('a')
 a.href = url
 a.download = `zezo_backend_logs_${Date.now()}.txt`
 a.click()
 URL.revokeObjectURL(url)
 }

 const allAvailableSources = useMemo(() => {
 const set = new Set<string>()
 logSources.forEach((s) => set.add(s.toUpperCase()))
 logs.forEach((l) => {
 if (l.source) set.add(l.source.toUpperCase())
 })
 return Array.from(set).sort()
 }, [logSources, logs])

 return (
 <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
 <DialogContent hideCloseButton className="max-w-4xl w-[95vw] bg-[var(--card)] border border-[var(--border)] p-0 overflow-hidden text-[var(--foreground)] flex flex-col h-[85vh] gap-0 rounded-[var(--radius)]">
 {/* Header */}
 <DialogHeader className="px-5 py-3.5 border-b border-[var(--border)] bg-[var(--card)] shrink-0">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-2.5">
 <div className="w-8 h-8 rounded-[var(--radius-sm,calc(var(--radius,0.5rem)-2px))] bg-[var(--primary)]/10 border border-[var(--primary)]/20 flex items-center justify-center text-[var(--primary)] ">
 <Terminal className="w-4 h-4" />
 </div>
 <div className="flex items-center gap-2">
 <DialogTitle className="text-sm font-semibold text-[var(--foreground)]">
 Log Console
 </DialogTitle>
 </div>
 </div>

 <Button
 variant="ghost"
 size="sm"
 onClick={onClose}
 className="h-7 w-7 p-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)] rounded-md"
 >
 <X className="w-4 h-4" />
 </Button>
 </div>
 <DialogDescription className="sr-only">Live log console</DialogDescription>
 </DialogHeader>

 {/* Action Controls & Filters Bar */}
 <div className="px-4 py-2.5 border-b border-[var(--border)] bg-[var(--input)] flex flex-wrap items-center justify-between gap-2 shrink-0">
 {/* Action buttons */}
 <div className="flex items-center gap-1.5 flex-wrap">
 <Button
 size="sm"
 variant={isFollow ? 'default' : 'outline'}
 onClick={() => setIsFollow(!isFollow)}
 className={`h-7 px-2.5 text-[11px] font-mono gap-1.5 ${
 isFollow
 ? 'bg-[var(--accent)] text-[var(--accent-foreground,#000000)] border border-[var(--accent)]'
 : 'bg-transparent border-[var(--border)] text-[var(--muted-foreground)]'
 }`}
 >
 <span className={`w-1.5 h-1.5 rounded-full ${isFollow ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-600'}`} />
 <span>FOLLOW</span>
 </Button>

 <Button
 size="sm"
 variant={isPaused ? 'destructive' : 'outline'}
 onClick={() => setIsPaused(!isPaused)}
 className={`h-7 px-2.5 text-[11px] font-mono gap-1.5 ${
 isPaused
 ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
 : 'bg-transparent border-[var(--border)] text-[var(--muted-foreground)]'
 }`}
 >
 {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
 <span>{isPaused ? 'RESUME' : 'PAUSE'}</span>
 </Button>

 <Button
 size="sm"
 variant="outline"
 onClick={onClearLogs}
 className="h-7 px-2.5 text-[11px] font-mono bg-transparent border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] gap-1.5"
 >
 <Trash2 className="w-3 h-3" />
 <span>CLEAR</span>
 </Button>

 <Button
 size="sm"
 variant="outline"
 onClick={handleExport}
 className="h-7 px-2.5 text-[11px] font-mono bg-transparent border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] gap-1.5"
 >
 <Download className="w-3 h-3" />
 <span>EXPORT</span>
 </Button>

 <Button
 size="sm"
 variant="outline"
 onClick={handleCopyAll}
 className="h-7 px-2.5 text-[11px] font-mono bg-transparent border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] gap-1.5"
 >
 {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
 <span>{copied ? 'COPIED' : 'COPY ALL'}</span>
 </Button>
 </div>

 {/* Filter inputs */}
 <div className="flex items-center gap-2 flex-wrap">
 {/* Search */}
 <div className="relative w-36 sm:w-44">
 <Search className="w-3 h-3 absolute left-2 top-2 text-[var(--muted-foreground)] pointer-events-none" />
 <Input
 placeholder="Filter text..."
 value={searchQuery}
 onChange={(e) => setSearchQuery(e.target.value)}
 className="h-7 pl-7 text-[11px] font-mono bg-[var(--card)] border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)]"
 />
 </div>

 {/* Level Select */}
 <div className="w-28">
 <Select value={levelFilter} onValueChange={setLevelFilter}>
 <SelectTrigger className="h-7 text-[10px] font-mono bg-[var(--card)] border-[var(--border)] text-[var(--foreground)]">
 <SelectValue placeholder="LEVEL" />
 </SelectTrigger>
 <SelectContent className="bg-[var(--popover)] border-[var(--border)] text-[var(--foreground)] text-xs">
 <SelectItem value="ALL">ALL LEVELS</SelectItem>
 <SelectItem value="INFO">INFO & UP</SelectItem>
 <SelectItem value="WARNING">WARNINGS</SelectItem>
 <SelectItem value="ERROR">ERRORS</SelectItem>
 <SelectItem value="DEBUG">DEBUG</SelectItem>
 </SelectContent>
 </Select>
 </div>

 {/* Source Select */}
 <div className="w-28">
 <Select value={sourceFilter} onValueChange={setSourceFilter}>
 <SelectTrigger className="h-7 text-[10px] font-mono bg-[var(--card)] border-[var(--border)] text-[var(--foreground)]">
 <SelectValue placeholder="SOURCE" />
 </SelectTrigger>
 <SelectContent className="bg-[var(--popover)] border-[var(--border)] text-[var(--foreground)] text-xs max-h-48">
 <SelectItem value="ALL">ALL SOURCES</SelectItem>
 {allAvailableSources.map((s) => (
 <SelectItem key={s} value={s}>
 {s}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>
 </div>
 </div>

 {/* Monospace Log Viewer */}
 <div className="flex-1 min-h-0 bg-[var(--background)] p-3 font-mono text-[11px] overflow-hidden">
 <ScrollArea className="h-full pr-3">
 {filteredLogs.length === 0 ? (
 <div className="flex flex-col items-center justify-center h-64 text-[var(--muted-foreground)] space-y-2">
 <Terminal className="w-8 h-8 opacity-30" />
 <p>No log records match the current filter.</p>
 </div>
 ) : (
 <div className="space-y-0.5">
 {filteredLogs.map((entry) => {
 const lvl = (entry.level || entry.type || 'INFO').toUpperCase()
 const isError = lvl.includes('ERR')
 const isWarn = lvl.includes('WARN')

 return (
 <div
 key={entry.id}
 className={`py-0.5 px-1.5 rounded flex items-start gap-2 hover:bg-[var(--accent)]/10 transition-colors leading-relaxed select-text ${
 isError
 ? 'text-red-400 bg-red-950/20'
 : isWarn
 ? 'text-amber-300 bg-amber-950/10'
 : 'text-[var(--foreground)]'
 }`}
 >
 <span className="text-[var(--muted-foreground)] shrink-0 text-[10px] select-none">
 [{entry.time}]
 </span>

 <span className="text-[var(--muted-foreground)] shrink-0 text-[10px] font-semibold bg-[var(--input)] px-1 rounded border border-[var(--border)] select-none">
 [{entry.source}]
 </span>

 {isError && (
 <span className="text-red-400 font-bold shrink-0 text-[10px] select-none">
 [ERROR]
 </span>
 )}
 {isWarn && (
 <span className="text-amber-400 font-bold shrink-0 text-[10px] select-none">
 [WARN]
 </span>
 )}

 <span className="break-all whitespace-pre-wrap flex-1">{entry.text}</span>
 </div>
 )
 })}
 <div ref={logEndRef} />
 </div>
 )}
 </ScrollArea>
 </div>
 </DialogContent>
 </Dialog>
 )
}
