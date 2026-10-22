import React, { useState } from 'react'
import { Plus, X, Loader2, Sparkles } from 'lucide-react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { api } from '../../lib/api'

interface NewMemoryModalProps {
 isOpen: boolean
 onClose: () => void
 onCreated: () => void
}

export const NewMemoryModal: React.FC<NewMemoryModalProps> = ({
 isOpen,
 onClose,
 onCreated,
}) => {
 const [title, setTitle] = useState('')
 const [content, setContent] = useState('')
 const [tags, setTags] = useState('')
 const [isSaving, setIsSaving] = useState(false)

 if (!isOpen) return null

 const handleSubmit = async (e: React.FormEvent) => {
 e.preventDefault()
 if (!title.trim()) return

 setIsSaving(true)
 try {
 const tagList = tags
 .split(',')
 .map((t) => t.trim().toLowerCase())
 .filter(Boolean)

 await api.createMemoryNote({
 title: title.trim(),
 category: 'knowledge',
 content: content.trim(),
 tags: tagList,
 })

 setTitle('')
 setContent('')
 setTags('')
 onCreated()
 onClose()
 } catch (err) {
 console.error('Failed to create new memory:', err)
 } finally {
 setIsSaving(false)
 }
 }

 return (
 <div className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4">
 <div className="w-full max-w-lg rounded-2xl bg-card text-foreground border border-border p-6 space-y-4">
 <div className="flex items-center justify-between border-b border-border/80 pb-3">
 <div className="flex items-center gap-2">
 <Sparkles className="w-4 h-4 text-primary" />
 <h3 className="text-sm font-bold text-foreground">Add New Memory Node</h3>
 </div>
 <button
 type="button"
 onClick={onClose}
 className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50"
 >
 <X className="w-4 h-4" />
 </button>
 </div>

 <form onSubmit={handleSubmit} className="space-y-3.5">
 <div>
 <label className="text-[11px] font-mono text-muted-foreground uppercase">Memory Title</label>
 <Input
 value={title}
 onChange={(e) => setTitle(e.target.value)}
 placeholder="e.g. NextJS Architecture Preferences"
 className="mt-1 h-8 text-xs font-mono rounded-xl"
 required
 />
 </div>

 <div>
 <label className="text-[11px] font-mono text-muted-foreground uppercase">
 Markdown Content (Use [[links]] to connect)
 </label>
 <textarea
 value={content}
 onChange={(e) => setContent(e.target.value)}
 rows={5}
 placeholder="Write memory description. You can link to other notes using [[Note Title]]..."
 className="mt-1 w-full text-xs font-mono bg-background border border-border rounded-xl p-3 focus:outline-hidden focus:ring-1 focus:ring-primary leading-relaxed resize-y"
 />
 </div>

 <div>
 <label className="text-[11px] font-mono text-muted-foreground uppercase">Tags (comma separated)</label>
 <Input
 value={tags}
 onChange={(e) => setTags(e.target.value)}
 placeholder="e.g. frontend, react, invariant"
 className="mt-1 h-8 text-xs font-mono rounded-xl"
 />
 </div>

 <div className="pt-2 flex items-center justify-end gap-2">
 <Button type="button" variant="ghost" size="sm" onClick={onClose} className="text-xs">
 Cancel
 </Button>
 <Button type="submit" size="sm" disabled={isSaving || !title.trim()} className="text-xs gap-1.5">
 {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
 <span>Create Node</span>
 </Button>
 </div>
 </form>
 </div>
 </div>
 )
}

