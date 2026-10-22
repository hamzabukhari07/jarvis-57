import React, { useState, useEffect } from 'react'
import {
 X,
 Edit3,
 Save,
 Trash2,
 ExternalLink,
 Copy,
 Check,
 Loader2,
} from 'lucide-react'
import { Button } from '../ui/button'
import { Badge } from '../reui/badge'
import { ScrollArea } from '../ui/scroll-area'
import { ConfirmDialog } from '../reui/confirm-dialog'
import { api } from '../../lib/api'
import type { GraphNode } from './MemoryGraphCanvas'

interface MemoryInspectorDrawerProps {
 node: GraphNode | null
 onClose: () => void
 onNodeUpdated: () => void
 onSelectConnectedNode: (nodeId: string) => void
}

export const MemoryInspectorDrawer: React.FC<MemoryInspectorDrawerProps> = ({
 node,
 onClose,
 onNodeUpdated,
 onSelectConnectedNode,
}) => {
 const [noteData, setNoteData] = useState<any | null>(null)
 const [isLoading, setIsLoading] = useState(false)
 const [isEditing, setIsEditing] = useState(false)
 const [editContent, setEditContent] = useState('')
 const [isSaving, setIsSaving] = useState(false)
 const [isDeleting, setIsDeleting] = useState(false)
 const [isConfirmDeleteOpen, setIsConfirmDeleteOpen] = useState(false)
 const [copied, setCopied] = useState(false)

 // Fetch full note content whenever selected node changes
 useEffect(() => {
 if (!node) {
 setNoteData(null)
 setIsEditing(false)
 return
 }

 let isMounted = true
 setIsLoading(true)

 api
 .getMemoryNote(node.file || node.id)
 .then((data) => {
 if (isMounted) {
 setNoteData(data)
 setEditContent(data?.content || '')
 setIsLoading(false)
 }
 })
 .catch((err) => {
 console.warn('Could not fetch memory note details:', err)
 if (isMounted) {
 setNoteData({
 id: node.id,
 title: node.label,
 category: node.category,
 content: `# ${node.label}\n\n${node.snippet}`,
 body: node.snippet,
 outbound_links: [],
 })
 setEditContent(`# ${node.label}\n\n${node.snippet}`)
 setIsLoading(false)
 }
 })

 return () => {
 isMounted = false
 }
 }, [node])

 if (!node) return null

 const handleSave = async () => {
 if (!node.file) return
 setIsSaving(true)
 try {
 await api.saveMemoryNote(node.file, editContent)
 setIsEditing(false)
 onNodeUpdated()
 } catch (e) {
 console.error('Failed to save memory note:', e)
 } finally {
 setIsSaving(false)
 }
 }

 const handleExecuteDelete = async () => {
 if (!node.file) return
 setIsDeleting(true)
 try {
 await api.deleteMemoryNote(node.file)
 setIsConfirmDeleteOpen(false)
 onClose()
 onNodeUpdated()
 } catch (e) {
 console.error('Failed to delete memory note:', e)
 } finally {
 setIsDeleting(false)
 }
 }

 const handleCopy = () => {
 navigator.clipboard.writeText(editContent || noteData?.content || '')
 setCopied(true)
 setTimeout(() => setCopied(false), 1500)
 }
 return (
 <div className="w-80 md:w-96 border-l border-border/80 bg-[#0a0a0a] flex flex-col h-full animate-in slide-in-from-right-4 duration-200">
 {/* Top Header */}
 <div className="h-14 px-4 border-b border-border/80 flex items-center justify-between shrink-0">
 <div className="flex items-center gap-2 min-w-0">
 <div
 className="w-3 h-3 rounded-full shrink-0 "
 style={{ backgroundColor: node.color || '#38bdf8' }}
 />
 <h3 className="text-xs font-bold text-foreground truncate font-mono">
 {node.label}
 </h3>
 </div>

 <div className="flex items-center gap-1">
 <button
 type="button"
 onClick={handleCopy}
 className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
 title="Copy Markdown"
 >
 {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
 </button>

 <button
 type="button"
 onClick={onClose}
 className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
 >
 <X className="w-3.5 h-3.5" />
 </button>
 </div>
 </div>

 <ScrollArea className="flex-1">
 <div className="p-4 space-y-4">
 {/* Metadata Badges */}
 <div className="flex flex-wrap items-center gap-1.5">
 <Badge variant="outline" className="text-[10px] capitalize font-mono py-0.5 px-2">
 {node.category}
 </Badge>
 {noteData?.tags?.map((tag: string) => (
 <Badge key={tag} variant="secondary" className="text-[10px] font-mono py-0.5 px-1.5 text-muted-foreground">
 #{tag}
 </Badge>
 ))}
 </div>

 {isLoading ? (
 <div className="py-12 flex flex-col items-center justify-center gap-2 text-muted-foreground">
 <Loader2 className="w-5 h-5 animate-spin text-primary" />
 <span className="text-xs font-mono">Reading vault note...</span>
 </div>
 ) : (
 <>
 {/* Note Content View / Edit Mode */}
 <div className="space-y-2">
 <div className="flex items-center justify-between">
 <span className="text-[11px] font-semibold text-muted-foreground font-mono uppercase tracking-wider">
 Markdown Content
 </span>
 <button
 type="button"
 onClick={() => setIsEditing(!isEditing)}
 className="flex items-center gap-1 text-[11px] text-primary hover:underline font-mono"
 >
 <Edit3 className="w-3 h-3" />
 <span>{isEditing ? 'Cancel Edit' : 'Edit Note'}</span>
 </button>
 </div>

 {isEditing ? (
 <div className="space-y-2">
 <textarea
 value={editContent}
 onChange={(e) => setEditContent(e.target.value)}
 rows={12}
 className="w-full text-xs font-mono bg-background border border-border/80 rounded-xl p-3 focus:outline-hidden focus:ring-1 focus:ring-primary leading-relaxed resize-y"
 placeholder="Write markdown with [[wikilinks]]..."
 />
 <div className="flex items-center justify-end gap-2">
 <Button
 type="button"
 size="sm"
 onClick={handleSave}
 disabled={isSaving}
 className="h-7 text-xs px-3 font-mono gap-1"
 >
 {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
 <span>Save Changes</span>
 </Button>
 </div>
 </div>
 ) : (
 <div className="p-3.5 rounded-xl bg-background/80 border border-border/70 text-xs text-foreground/90 leading-relaxed font-sans whitespace-pre-wrap selection:bg-primary/20">
 {noteData?.body || noteData?.content || node.snippet}
 </div>
 )}
 </div>

 {/* Connected Wikilinks / Backlinks */}
 {noteData?.outbound_links && noteData.outbound_links.length > 0 && (
 <div className="space-y-2 pt-2 border-t border-border/60">
 <div className="text-[11px] font-semibold text-muted-foreground font-mono uppercase tracking-wider">
 Connected Backlinks ({noteData.outbound_links.length})
 </div>
 <div className="flex flex-wrap gap-1.5">
 {noteData.outbound_links.map((linkTitle: string) => (
 <button
 key={linkTitle}
 type="button"
 onClick={() => onSelectConnectedNode(linkTitle)}
 className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg bg-muted/60 hover:bg-muted text-foreground border border-border/60 transition-colors font-mono"
 >
 <ExternalLink className="w-2.5 h-2.5 text-primary" />
 <span>{linkTitle}</span>
 </button>
 ))}
 </div>
 </div>
 )}

 {/* Delete Note Option */}
 {node.file && (
 <div className="pt-4 border-t border-border/60 flex items-center justify-between">
 <span className="text-[10px] text-muted-foreground font-mono truncate max-w-[160px]">
 {node.file}
 </span>
 <Button
 type="button"
 variant="ghost"
 size="sm"
 onClick={() => setIsConfirmDeleteOpen(true)}
 disabled={isDeleting}
 className="h-7 text-xs px-2 text-destructive hover:bg-destructive/10 font-mono gap-1"
 >
 {isDeleting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
 <span>Delete Memory</span>
 </Button>
 </div>
 )}
 </>
 )}
 </div>
 </ScrollArea>

 {/* ReUI Confirmation Dialog for Deleting Memory Node */}
 <ConfirmDialog
 open={isConfirmDeleteOpen}
 onOpenChange={setIsConfirmDeleteOpen}
 title="Delete Memory Note"
 description={`Are you sure you want to delete memory "${node.label}"?`}
 warningText={`This will permanently delete the Markdown note "${node.file}" and remove this node and all its connected backlinks from the knowledge graph.`}
 confirmText="Delete Note"
 cancelText="Cancel"
 variant="destructive"
 isLoading={isDeleting}
 onConfirm={handleExecuteDelete}
 />
 </div>
 )
}
