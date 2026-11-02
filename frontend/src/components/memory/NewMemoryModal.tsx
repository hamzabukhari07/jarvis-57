import React, { useState } from 'react'
import { Plus, X, Loader2, Sparkles, Tag } from '@/lib/zezo-icons'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { api } from '../../lib/api'
import { CATEGORY_OPTIONS } from './MemoryInspectorDrawer'

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
  const [category, setCategory] = useState('knowledge')
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
        category: category.trim().toLowerCase(),
        content: content.trim(),
        tags: tagList,
      })

      setTitle('')
      setCategory('knowledge')
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
      <div className="w-full max-w-lg rounded-2xl bg-card text-foreground border border-border p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-border/80 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-bold text-foreground">Add New Memory Node</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
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
            <label className="text-[11px] font-mono text-muted-foreground uppercase">Category</label>
            <div className="grid grid-cols-3 gap-1.5 mt-1">
              {CATEGORY_OPTIONS.map((cat) => {
                const isSelected = category.toLowerCase() === cat.id
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setCategory(cat.id)}
                    className={`px-2 py-1.5 rounded-lg text-[11px] font-mono flex items-center gap-1.5 border transition-all ${
                      isSelected
                        ? 'bg-primary/15 border-primary text-foreground font-semibold shadow-xs'
                        : 'bg-muted/40 border-border/70 text-muted-foreground hover:bg-muted/70 hover:text-foreground'
                    }`}
                  >
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: cat.color }} />
                    <span className="truncate">{cat.label}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <label className="text-[11px] font-mono text-muted-foreground uppercase flex items-center gap-1">
              <Tag className="w-2.5 h-2.5" /> Tags (comma-separated)
            </label>
            <Input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g. frontend, react, invariant"
              className="mt-1 h-8 text-xs font-mono rounded-xl"
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
