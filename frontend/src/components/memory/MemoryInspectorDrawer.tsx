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
  Tag,
  Sparkles,
} from '@/lib/zezo-icons'
import { Button } from '../ui/button'
import { Badge } from '../reui/badge'
import { Input } from '../ui/input'
import { ScrollArea } from '../ui/scroll-area'
import { ConfirmDialog } from '../reui/confirm-dialog'
import { api } from '../../lib/api'
import type { GraphNode } from './MemoryGraphCanvas'

export const CATEGORY_OPTIONS = [
  { id: 'profile', label: 'Profile', color: '#a855f7' },
  { id: 'project', label: 'Project', color: '#38bdf8' },
  { id: 'preference', label: 'Preference', color: '#fb923c' },
  { id: 'relationship', label: 'Relationship', color: '#facc15' },
  { id: 'knowledge', label: 'Knowledge', color: '#34d399' },
  { id: 'general', label: 'General', color: '#94a3b8' },
]

/**
 * Strict front-of-file YAML separation.
 * Only match '---' at index 0. Any '---' horizontal rules inside the markdown body
 * are preserved verbatim.
 */
function splitFrontmatterAndBody(raw: string): { meta: Record<string, any>; body: string } {
  if (!raw || (!raw.startsWith('---\n') && !raw.startsWith('---\r\n'))) {
    return { meta: {}, body: raw || '' }
  }
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/)
  if (!match) {
    return { meta: {}, body: raw }
  }
  const header = match[1]
  const body = match[2]
  const meta: Record<string, any> = {}
  for (const line of header.split(/\r?\n/)) {
    const idx = line.indexOf(':')
    if (idx > -1) {
      const k = line.slice(0, idx).trim().toLowerCase()
      let v = line.slice(idx + 1).trim()
      if (v.startsWith('[') && v.endsWith(']')) {
        meta[k] = v
          .slice(1, -1)
          .split(',')
          .map((s) => s.trim().replace(/^['"]|['"]$/g, ''))
          .filter(Boolean)
      } else {
        meta[k] = v.replace(/^['"]|['"]$/g, '')
      }
    }
  }
  return { meta, body }
}

function buildFrontmatterNote(
  id: string,
  title: string,
  category: string,
  tags: string[],
  body: string,
  turnCount?: number | null
): string {
  const cleanTitle = title.trim() || 'Untitled Note'
  const cleanCat = category.trim().toLowerCase() || 'knowledge'
  const tagList = tags.map((t) => t.trim()).filter(Boolean)
  const dateStr = new Date().toISOString().slice(0, 10)
  const headerLines = [
    '---',
    `id: ${id}`,
    `title: ${cleanTitle}`,
    `category: ${cleanCat}`,
    `updated: ${dateStr}`,
    `tags: [${tagList.join(', ')}]`,
  ]
  if (typeof turnCount === 'number' && turnCount > 0) {
    headerLines.push(`turn_count: ${turnCount}`)
  }
  headerLines.push('auto_generated: false', '---', '')
  return headerLines.join('\n') + body.trim() + '\n'
}

interface MemoryInspectorDrawerProps {
  mode?: 'inspect' | 'create'
  node: GraphNode | null
  onClose: () => void
  onNodeUpdated: () => void
  onSelectConnectedNode: (nodeId: string) => void
}

export const MemoryInspectorDrawer: React.FC<MemoryInspectorDrawerProps> = ({
  mode = 'inspect',
  node,
  onClose,
  onNodeUpdated,
  onSelectConnectedNode,
}) => {
  const [noteData, setNoteData] = useState<any | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isEditing, setIsEditing] = useState(mode === 'create')

  // Structured edit fields
  const [editTitle, setEditTitle] = useState('')
  const [editCategory, setEditCategory] = useState('knowledge')
  const [editTags, setEditTags] = useState('')
  const [editBody, setEditBody] = useState('')

  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isConfirmDeleteOpen, setIsConfirmDeleteOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  // Guard: If inspect mode and node is null, do not render
  if (!node && mode === 'inspect') return null

  // Fetch full note content or initialize create state
  useEffect(() => {
    if (mode === 'create') {
      setNoteData(null)
      setEditTitle('')
      setEditCategory('knowledge')
      setEditTags('')
      setEditBody('')
      setIsEditing(true)
      setIsLoading(false)
      return
    }

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
          const { meta, body } = splitFrontmatterAndBody(data?.content || '')
          setEditTitle(meta.title || data?.title || node.label || '')
          setEditCategory(meta.category || data?.category || node.category || 'knowledge')
          const rawTags = (meta.tags || data?.tags || node.tags || []).filter(
            (t: string) => !String(t).toLowerCase().endsWith('_turns') && String(t).toLowerCase() !== 'conversation'
          )
          setEditTags(Array.isArray(rawTags) ? rawTags.join(', ') : String(rawTags))
          setEditBody(body || data?.body || node.snippet || '')
          setIsLoading(false)
        }
      })
      .catch((err) => {
        console.warn('Could not fetch memory note details:', err)
        if (isMounted) {
          const fallbackData = {
            id: node.id,
            title: node.label,
            category: node.category,
            content: `# ${node.label}\n\n${node.snippet}`,
            body: node.snippet,
            outbound_links: [],
          }
          setNoteData(fallbackData)
          setEditTitle(node.label || '')
          setEditCategory(node.category || 'knowledge')
          const cleanTags = (node.tags || []).filter(
            (t: string) => !String(t).toLowerCase().endsWith('_turns') && String(t).toLowerCase() !== 'conversation'
          )
          setEditTags(cleanTags.join(', '))
          setEditBody(node.snippet || '')
          setIsLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [node, mode])

  const handleStartEditing = () => {
    if (noteData) {
      const { meta, body } = splitFrontmatterAndBody(noteData.content || '')
      setEditTitle(meta.title || noteData.title || node?.label || '')
      setEditCategory(meta.category || noteData.category || node?.category || 'knowledge')
      const rawTags = (meta.tags || noteData.tags || node?.tags || []).filter(
        (t: string) => !String(t).toLowerCase().endsWith('_turns') && String(t).toLowerCase() !== 'conversation'
      )
      setEditTags(Array.isArray(rawTags) ? rawTags.join(', ') : String(rawTags))
      setEditBody(body || noteData.body || node?.snippet || '')
    }
    setIsEditing(true)
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const tagList = editTags
        .split(',')
        .map((t) => t.trim().toLowerCase())
        .filter((t) => Boolean(t) && !t.endsWith('_turns') && t !== 'conversation')

      if (mode === 'create') {
        await api.createMemoryNote({
          title: editTitle.trim() || 'Untitled Note',
          category: editCategory.trim().toLowerCase() || 'knowledge',
          content: editBody.trim(),
          tags: tagList,
        })
        onNodeUpdated()
        onClose()
        return
      }

      if (!node?.file) return

      const turnCount =
        noteData?.turn_count ??
        node?.turn_count ??
        (() => {
          const allTags = noteData?.tags || node?.tags || []
          for (const t of allTags) {
            const m = String(t).match(/^(\d+)_turns$/i)
            if (m) return parseInt(m[1], 10)
          }
          return undefined
        })()

      const fullContent = buildFrontmatterNote(
        noteData?.id || node.id,
        editTitle,
        editCategory,
        tagList,
        editBody,
        turnCount
      )

      await api.saveMemoryNote(node.file, fullContent)
      setIsEditing(false)
      setNoteData((prev: any) => ({
        ...prev,
        title: editTitle,
        category: editCategory,
        tags: tagList,
        content: fullContent,
        body: editBody,
      }))
      onNodeUpdated()
    } catch (e) {
      console.error('Failed to save memory note:', e)
    } finally {
      setIsSaving(false)
    }
  }

  const handleExecuteDelete = async () => {
    if (!node?.file && !node?.id) return
    setIsDeleting(true)
    try {
      await api.deleteMemoryNote(node.file || node.id)
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
    navigator.clipboard.writeText(editBody || noteData?.body || noteData?.content || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const activeCategory = CATEGORY_OPTIONS.find(
    (c) => c.id === (isEditing ? editCategory : (noteData?.category || node?.category || 'knowledge'))
  )

  // Filter out internal system metadata
  const displayTags = (noteData?.tags || node?.tags || []).filter((t: string) => {
    const lower = String(t).toLowerCase()
    return !lower.endsWith('_turns') && lower !== 'conversation' && lower !== 'memory'
  })

  // Turn count resolution
  const turnCount: number | null =
    (typeof noteData?.turn_count === 'number' && noteData.turn_count > 0 ? noteData.turn_count : null) ??
    (typeof node?.turn_count === 'number' && node.turn_count > 0 ? node.turn_count : null) ??
    (() => {
      const allTags = noteData?.tags || node?.tags || []
      for (const t of allTags) {
        const m = String(t).match(/^(\d+)_turns$/i)
        if (m) return parseInt(m[1], 10)
      }
      return null
    })()

  return (
    <div className="w-80 md:w-96 border-l border-[rgba(120,120,255,0.2)] bg-[#0a0a14]/95 backdrop-blur-xl flex flex-col h-full animate-in slide-in-from-right-4 duration-200 z-30 shadow-2xl">
      {/* Top Header */}
      <div className="h-14 px-4 border-b border-[rgba(120,120,255,0.15)] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className="w-3 h-3 rounded-full shrink-0 shadow-xs"
            style={{ backgroundColor: activeCategory?.color || '#38bdf8' }}
          />
          <h3 className="text-xs font-bold text-foreground truncate font-mono tracking-tight">
            {mode === 'create' ? 'Add Memory Node' : (noteData?.title || node?.label)}
          </h3>
        </div>

        <div className="flex items-center gap-1">
          {mode !== 'create' && (
            <button
              type="button"
              onClick={handleCopy}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
              title="Copy Description"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          )}

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
          {/* Metadata Badges (Only in inspect view mode) */}
          {mode === 'inspect' && !isEditing && (
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge
                variant="outline"
                className="text-[10px] capitalize font-mono py-0.5 px-2 flex items-center gap-1 bg-[rgba(120,120,255,0.06)]"
                style={{ borderColor: activeCategory?.color }}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: activeCategory?.color || '#38bdf8' }}
                />
                {activeCategory?.label || node?.category}
              </Badge>

              {turnCount !== null && (
                <Badge
                  variant="secondary"
                  className="text-[10px] font-mono py-0.5 px-2 text-muted-foreground bg-muted/50 border border-border/50"
                >
                  {turnCount} {turnCount === 1 ? 'turn' : 'turns'}
                </Badge>
              )}

              {displayTags.map((tag: string) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="text-[10px] font-mono py-0.5 px-1.5 text-muted-foreground bg-muted/40"
                >
                  #{tag}
                </Badge>
              ))}
            </div>
          )}

          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-muted-foreground">
              <Loader2 className="w-5 h-5 animate-spin text-primary" />
              <span className="text-xs font-mono">Reading galaxy note...</span>
            </div>
          ) : (
            <>
              {/* Note Content View / Edit Mode */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-muted-foreground font-mono uppercase tracking-wider">
                    {mode === 'create' ? 'New Memory Node' : isEditing ? 'Edit Note' : 'Note Content'}
                  </span>
                  {mode === 'inspect' && (
                    <button
                      type="button"
                      onClick={() => {
                        if (isEditing) {
                          setIsEditing(false)
                        } else {
                          handleStartEditing()
                        }
                      }}
                      className="flex items-center gap-1 text-[11px] text-primary hover:underline font-mono"
                    >
                      <Edit3 className="w-3 h-3" />
                      <span>{isEditing ? 'Cancel' : 'Edit Note'}</span>
                    </button>
                  )}
                </div>

                {isEditing ? (
                  <div className="space-y-3 pt-1">
                    {/* Title */}
                    <div>
                      <label className="text-[10px] font-mono text-muted-foreground uppercase">Note Title</label>
                      <Input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        placeholder="e.g. NextJS Architecture Preferences"
                        className="mt-1 h-8 text-xs font-mono rounded-lg bg-background/80 border-border/80"
                        required
                      />
                    </div>

                    {/* Category Selector */}
                    <div>
                      <label className="text-[10px] font-mono text-muted-foreground uppercase">Category</label>
                      <div className="grid grid-cols-3 gap-1.5 mt-1">
                        {CATEGORY_OPTIONS.map((cat) => {
                          const isSelected = editCategory.toLowerCase() === cat.id
                          return (
                            <button
                              key={cat.id}
                              type="button"
                              onClick={() => setEditCategory(cat.id)}
                              className={`px-2 py-1.5 rounded-lg text-[11px] font-mono flex items-center gap-1.5 border transition-all ${
                                isSelected
                                  ? 'bg-primary/20 border-primary text-foreground font-semibold shadow-xs'
                                  : 'bg-muted/30 border-border/60 text-muted-foreground hover:bg-muted/60 hover:text-foreground'
                              }`}
                            >
                              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: cat.color }} />
                              <span className="truncate">{cat.label}</span>
                            </button>
                          )
                        })}
                      </div>
                    </div>

                    {/* Tags */}
                    <div>
                      <label className="text-[10px] font-mono text-muted-foreground uppercase flex items-center gap-1">
                        <Tag className="w-2.5 h-2.5" /> Tags (comma-separated)
                      </label>
                      <Input
                        value={editTags}
                        onChange={(e) => setEditTags(e.target.value)}
                        placeholder="e.g. react, architecture, preferences"
                        className="mt-1 h-8 text-xs font-mono rounded-lg bg-background/80 border-border/80"
                      />
                    </div>

                    {/* Body */}
                    <div>
                      <label className="text-[10px] font-mono text-muted-foreground uppercase">Note Content</label>
                      <textarea
                        value={editBody}
                        onChange={(e) => setEditBody(e.target.value)}
                        rows={9}
                        className="mt-1 w-full text-xs font-mono bg-background/90 border border-border/80 rounded-xl p-3 focus:outline-hidden focus:ring-1 focus:ring-primary leading-relaxed resize-y"
                        placeholder="Write your thoughts here. Use [[Note Name]] to link to other memories..."
                      />
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-1">
                      {mode === 'create' ? (
                        <>
                          <Button type="button" variant="ghost" size="sm" onClick={onClose} className="h-7 text-xs font-mono">
                            Cancel
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            onClick={handleSave}
                            disabled={isSaving || !editTitle.trim()}
                            className="h-7 text-xs px-3 font-mono gap-1"
                          >
                            {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                            <span>Create Node</span>
                          </Button>
                        </>
                      ) : (
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
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="p-3.5 rounded-xl bg-background/60 border border-border/70 text-xs text-foreground/90 leading-relaxed font-sans whitespace-pre-wrap selection:bg-primary/20">
                    {noteData?.body || noteData?.content || node?.snippet}
                  </div>
                )}
              </div>

              {/* Connected Wikilinks / Backlinks as interactive chips */}
              {mode === 'inspect' && !isEditing && noteData?.outbound_links && noteData.outbound_links.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-[rgba(120,120,255,0.15)]">
                  <div className="text-[11px] font-semibold text-muted-foreground font-mono uppercase tracking-wider">
                    Connected Synapses ({noteData.outbound_links.length})
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {noteData.outbound_links.map((linkTitle: string) => (
                      <button
                        key={linkTitle}
                        type="button"
                        onClick={() => onSelectConnectedNode(linkTitle)}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg bg-[rgba(120,120,255,0.08)] hover:bg-[rgba(120,120,255,0.18)] text-foreground border border-[rgba(120,120,255,0.25)] transition-all font-mono"
                      >
                        <ExternalLink className="w-2.5 h-2.5 text-primary" />
                        <span>{linkTitle}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Delete Note Option */}
              {mode === 'inspect' && (node?.file || node?.id) && (
                <div className="pt-4 border-t border-[rgba(120,120,255,0.15)] flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground font-mono truncate max-w-[160px]">
                    {node.file || node.id}
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

      {/* ReUI Confirmation Dialog for Deleting Memory */}
      {mode === 'inspect' && node && (
        <ConfirmDialog
          open={isConfirmDeleteOpen}
          onOpenChange={setIsConfirmDeleteOpen}
          title={`Delete Memory "${noteData?.title || node.label}"?`}
          description="Permanently delete this memory note and its recorded turns from ZEZO Brain?"
          warningText="This action will permanently delete the note from the markdown vault and purge any associated conversation turns from SQLite so it will never reappear."
          confirmText="Delete Permanently"
          cancelText="Cancel"
          variant="destructive"
          isLoading={isDeleting}
          onConfirm={handleExecuteDelete}
        />
      )}
    </div>
  )
}
