import React, { useState, useMemo, useEffect, useCallback } from 'react'
import { api } from '../../lib/api'
import { Card } from '../reui/card'
import { Badge } from '../reui/badge'
import { Callout } from '../reui/callout'
import { ConfirmDialog } from '../reui/confirm-dialog'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { ScrollArea } from '../ui/scroll-area'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import {
  Search,
  Code2,
  Globe,
  Cpu,
  Palette,
  Workflow,
  Bot,
  Eye,
  Edit3,
  Save,
  FileCode,
  X,
  ChevronRight,
  Plus,
  Trash2,
  Pencil,
  AlertCircle,
  Check,
  Loader2,
} from 'lucide-react'

export interface SkillItem {
  id: string
  name: string
  type: 'skill' | 'action' | 'plugin'
  category: string
  version: string
  author: string
  description: string
  enabled: boolean
  tags: string[]
  markdownDoc: string
}

const CORE_SKILL_IDS = new Set(['website_build', 'website_clone', 'generate_design_md'])
const SLUG_REGEX = /^[a-z0-9_]{1,40}$/

const DOMAIN_OPTIONS = [
  { value: 'coding', label: 'Coding' },
  { value: 'design', label: 'Design' },
  { value: 'research', label: 'Research' },
  { value: 'orchestration', label: 'Fleet & Orchestration' },
  { value: 'system', label: 'System' },
  { value: 'media', label: 'Media & Office' },
]

export function formatSkillSlug(input: string): string {
  return input
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9_]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 40)
}

export const SkillsSettingsTab: React.FC = () => {
  const [skills, setSkills] = useState<SkillItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  // Toast Notification
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const showToast = useCallback((message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3500)
  }, [])

  // Slide-Over Drawer State
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [activeSkillId, setActiveSkillId] = useState<string | null>(null)
  const [activeDrawerTab, setActiveDrawerTab] = useState<'preview' | 'edit'>('preview')

  // Form Fields
  const [formName, setFormName] = useState('')
  const [formSlug, setFormSlug] = useState('')
  const [isCustomSlug, setIsCustomSlug] = useState(false)
  const [formCategory, setFormCategory] = useState('coding')
  const [formDescription, setFormDescription] = useState('')
  const [formMarkdownDoc, setFormMarkdownDoc] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  // Confirm Delete Dialog State
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [skillToDelete, setSkillToDelete] = useState<SkillItem | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // Fetch live skills from backend /api/skills
  const fetchSkills = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await api.getSkills()
      if (res && Array.isArray(res.skills)) {
        const parsed: SkillItem[] = res.skills.map((s: any) => ({
          id: s.name,
          name: s.display_name || s.name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
          type: 'skill',
          category: (s.domain || 'coding').toLowerCase(),
          version: s.version || '1.0.0',
          author: s.author || (CORE_SKILL_IDS.has(s.name) ? 'Hamza Bukhari' : 'ZEZO Core'),
          description: s.description || '',
          enabled: !s.disabled,
          tags: s.tags || [s.domain || 'System'],
          markdownDoc: s.instructions || '',
        }))
        setSkills(parsed)
      } else {
        setSkills([])
      }
    } catch (err: any) {
      console.error('Failed to load skills from backend:', err)
      showToast(err?.message || 'Failed to load skills from backend registry', 'error')
    } finally {
      setIsLoading(false)
    }
  }, [showToast])

  useEffect(() => {
    fetchSkills()
  }, [fetchSkills])

  // Filter skills by search query and category
  const filteredSkills = useMemo(() => {
    return skills.filter((item) => {
      const matchSearch =
        !searchQuery.trim() ||
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))

      const matchCategory =
        selectedCategory === 'all' || item.category === selectedCategory

      return matchSearch && matchCategory
    })
  }, [skills, searchQuery, selectedCategory])

  // Slug validation
  const isSlugValid = useMemo(() => SLUG_REGEX.test(formSlug), [formSlug])

  // Name input handler with auto-slug formatting
  const handleNameChange = (val: string) => {
    setFormName(val)
    if (!isCustomSlug || !formSlug) {
      setFormSlug(formatSkillSlug(val))
    }
  }

  // Slug input handler
  const handleSlugChange = (val: string) => {
    setIsCustomSlug(true)
    const cleaned = val.toLowerCase().replace(/[^a-z0-9_]/g, '_').slice(0, 40)
    setFormSlug(cleaned)
  }

  // Open Drawer for creating new skill
  const openCreateDrawer = () => {
    setIsCreating(true)
    setActiveSkillId(null)
    setFormName('')
    setFormSlug('')
    setIsCustomSlug(false)
    setFormCategory('coding')
    setFormDescription('')
    setFormMarkdownDoc(
      `# Skill SOP & Directives\n\n## Objective\nDescribe what this skill executes and the expected deliverables.\n\n## Directives & Execution Steps\n1. Detail procedure step one.\n2. Detail procedure step two.\n\n## Verification & Constraints\n- Outline safety boundaries and self-verification checks.\n`
    )
    setActiveDrawerTab('edit')
    setIsDrawerOpen(true)
  }

  // Open Drawer for viewing/previewing existing skill
  const openPreviewDrawer = (skill: SkillItem) => {
    setIsCreating(false)
    setActiveSkillId(skill.id)
    setFormName(skill.name)
    setFormSlug(skill.id)
    setIsCustomSlug(true)
    setFormCategory(skill.category || 'coding')
    setFormDescription(skill.description || '')
    setFormMarkdownDoc(skill.markdownDoc || '')
    setActiveDrawerTab('preview')
    setIsDrawerOpen(true)
  }

  // Open Drawer directly for editing existing skill
  const openEditDrawer = (skill: SkillItem) => {
    setIsCreating(false)
    setActiveSkillId(skill.id)
    setFormName(skill.name)
    setFormSlug(skill.id)
    setIsCustomSlug(true)
    setFormCategory(skill.category || 'coding')
    setFormDescription(skill.description || '')
    setFormMarkdownDoc(skill.markdownDoc || '')
    setActiveDrawerTab('edit')
    setIsDrawerOpen(true)
  }

  // Close Drawer
  const closeDrawer = () => {
    if (isSaving) return
    setIsDrawerOpen(false)
    setIsCreating(false)
    setActiveSkillId(null)
  }

  // Save skill to backend via api.saveSkill
  const handleSaveSkill = async () => {
    const targetId = isCreating ? formSlug : (activeSkillId || formSlug)
    if (!targetId || !SLUG_REGEX.test(targetId)) {
      showToast('Skill identifier must match ^[a-z0-9_]{1,40}$ (lowercase letters, numbers, and underscores).', 'error')
      return
    }
    if (!formDescription.trim()) {
      showToast('Please provide a short description for this skill.', 'error')
      return
    }

    setIsSaving(true)
    try {
      await api.saveSkill({
        name: targetId,
        description: formDescription.trim(),
        instructions: formMarkdownDoc,
        domain: formCategory,
      })
      showToast(`Skill "${targetId}" saved successfully!`, 'success')
      await fetchSkills()
      setIsDrawerOpen(false)
      setIsCreating(false)
      setActiveSkillId(null)
    } catch (err: any) {
      console.error('Backend skill save error:', err)
      showToast(err?.message || 'Failed to save skill', 'error')
    } finally {
      setIsSaving(false)
    }
  }

  // Handle skill delete confirmation
  const handleConfirmDelete = async () => {
    if (!skillToDelete) return
    if (CORE_SKILL_IDS.has(skillToDelete.id)) {
      showToast('System core skill cannot be deleted.', 'error')
      setIsDeleteDialogOpen(false)
      return
    }

    setIsDeleting(true)
    try {
      await api.deleteSkill(skillToDelete.id)
      showToast(`Skill "${skillToDelete.name}" deleted successfully`, 'success')
      setIsDeleteDialogOpen(false)
      if (activeSkillId === skillToDelete.id) {
        setIsDrawerOpen(false)
      }
      setSkillToDelete(null)
      await fetchSkills()
    } catch (err: any) {
      console.error('Backend skill delete error:', err)
      showToast(err?.message || 'Failed to delete skill', 'error')
    } finally {
      setIsDeleting(false)
    }
  }

  const getCategoryDetails = (category: string) => {
    switch (category) {
      case 'design':
        return {
          icon: Palette,
          color: '#f59e0b',
          badgeVariant: 'warning' as const,
        }
      case 'coding':
        return {
          icon: Code2,
          color: '#3b82f6',
          badgeVariant: 'default' as const,
        }
      case 'research':
        return {
          icon: Globe,
          color: '#10b981',
          badgeVariant: 'completed' as const,
        }
      case 'orchestration':
        return {
          icon: Bot,
          color: '#a855f7',
          badgeVariant: 'secondary' as const,
        }
      case 'system':
        return {
          icon: Cpu,
          color: '#06b6d4',
          badgeVariant: 'outline' as const,
        }
      case 'media':
        return {
          icon: FileCode,
          color: '#ec4899',
          badgeVariant: 'default' as const,
        }
      default:
        return {
          icon: Workflow,
          color: 'var(--primary)',
          badgeVariant: 'default' as const,
        }
    }
  }

  return (
    <div className="space-y-4 w-full min-w-0 max-w-full relative">
      {/* ── 1. Compact Header & Action Controls ── */}
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-foreground tracking-tight">Skills Hub</h2>
            {skills.length > 0 && (
              <Badge variant="outline" size="xs" className="font-mono text-[10px]">
                {skills.length} Loaded
              </Badge>
            )}
          </div>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Declarative agent directives & SOPs loaded live from disk.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {toast && (
            <div
              className={`text-xs px-2.5 py-1 rounded-md border flex items-center gap-1.5 font-medium animate-in fade-in duration-150 ${
                toast.type === 'error'
                  ? 'bg-red-500/10 border-red-500/30 text-red-400'
                  : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              }`}
            >
              {toast.type === 'error' ? <AlertCircle className="w-3 h-3" /> : <Check className="w-3 h-3" />}
              <span>{toast.message}</span>
            </div>
          )}

          <Button
            size="sm"
            onClick={openCreateDrawer}
            className="h-7 px-3 text-xs gap-1.5 font-medium bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Skill</span>
          </Button>
        </div>
      </div>

      {/* ── 2. Filter Pills Bar & Search Input ── */}
      <Card className="p-1.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 w-full min-w-0">
        {/* Category Pills */}
        <div className="flex items-center gap-1 overflow-x-auto py-0.5 min-w-0 flex-1">
          {[
            { id: 'all', label: 'All', icon: Workflow },
            { id: 'design', label: 'Design', icon: Palette },
            { id: 'coding', label: 'Coding', icon: Code2 },
            { id: 'research', label: 'Research', icon: Globe },
            { id: 'orchestration', label: 'Fleet', icon: Bot },
            { id: 'system', label: 'System', icon: Cpu },
            { id: 'media', label: 'Media', icon: FileCode },
          ].map((cat) => {
            const Icon = cat.icon
            const isActive = selectedCategory === cat.id
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => setSelectedCategory(cat.id)}
                className={`h-6 px-2.5 rounded-md flex items-center gap-1.5 text-[11px] font-medium transition-all whitespace-nowrap shrink-0 ${
                  isActive
                    ? 'bg-primary text-primary-foreground font-semibold'
                    : 'text-muted-foreground hover:text-foreground hover:bg-input'
                }`}
              >
                <Icon className="w-3 h-3" />
                <span>{cat.label}</span>
              </button>
            )
          })}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-44 shrink-0">
          <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search skills..."
            className="h-7 pl-6 pr-2 text-xs bg-input/60 rounded-md"
          />
        </div>
      </Card>

      {/* ── 3. Skills Cards Grid ── */}
      {isLoading ? (
        <div className="py-12 flex flex-col items-center justify-center text-center">
          <Loader2 className="w-6 h-6 animate-spin text-primary opacity-60 mb-2" />
          <span className="text-xs text-muted-foreground font-mono">Loading skills from live backend...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full min-w-0">
          {filteredSkills.map((skill) => {
            const cat = getCategoryDetails(skill.category)
            const Icon = cat.icon
            const isDrawerOpenForThis = isDrawerOpen && activeSkillId === skill.id
            const isCore = CORE_SKILL_IDS.has(skill.id)

            return (
              <Card
                key={skill.id}
                onClick={() => openPreviewDrawer(skill)}
                className={`px-3 py-2.5 transition-all duration-150 flex items-center justify-between gap-2.5 cursor-pointer group select-none ${
                  isDrawerOpenForThis
                    ? 'border-primary bg-primary/10 ring-1 ring-primary/40'
                    : 'hover:border-primary/40 hover:bg-input/40'
                }`}
              >
                {/* Left: Icon + Skill Name & Metadata */}
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <div
                    className="w-7 h-7 rounded-md flex items-center justify-center shrink-0 border transition-transform group-hover:scale-105"
                    style={{
                      backgroundColor: `${cat.color}15`,
                      borderColor: `${cat.color}30`,
                      color: cat.color,
                    }}
                  >
                    <Icon className="w-3.5 h-3.5" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                        {skill.name}
                      </span>
                      {isCore && (
                        <Badge
                          variant="outline"
                          size="xs"
                          className="font-mono text-[9px] border-amber-500/30 text-amber-400 bg-amber-500/10 shrink-0"
                        >
                          Core
                        </Badge>
                      )}
                    </div>
                    <div className="text-[10px] font-mono text-muted-foreground capitalize mt-0.5 truncate">
                      {skill.category} · {skill.id}
                    </div>
                  </div>
                </div>

                {/* Right: Clean ReUI Edit & Delete Buttons + Chevron */}
                <div
                  className="shrink-0 flex items-center gap-1"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      openEditDrawer(skill)
                    }}
                    className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-input"
                    title="Edit Skill Directives"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </Button>

                  {isCore ? (
                    <Button
                      variant="ghost"
                      size="icon"
                      disabled
                      title="System core skill cannot be deleted"
                      className="h-7 w-7 text-muted-foreground opacity-30 cursor-not-allowed hover:bg-transparent"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  ) : (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation()
                        setSkillToDelete(skill)
                        setIsDeleteDialogOpen(true)
                      }}
                      className="h-7 w-7 text-muted-foreground hover:text-red-400 hover:bg-red-500/10"
                      title="Delete Skill"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  )}

                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40 group-hover:text-primary group-hover:translate-x-0.5 transition-all ml-0.5" />
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && filteredSkills.length === 0 && (
        <Callout variant="default" className="py-8 text-center">
          <FileCode className="w-6 h-6 mx-auto mb-2 opacity-40" />
          <div className="text-xs font-semibold text-foreground">No matching skills found</div>
          <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
            {searchQuery || selectedCategory !== 'all'
              ? 'Try a different search query or category filter.'
              : 'No declarative skills registered. Click "+ Create Skill" to author one.'}
          </div>
        </Callout>
      )}

      {/* ── 4. Slide-Over Side Drawer for Detailed Info & Authoring SOP ── */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <div
            onClick={closeDrawer}
            className="absolute inset-0 bg-black/80 transition-opacity duration-150"
          />

          {/* Drawer Panel */}
          <div className="relative w-full max-w-md sm:max-w-xl h-full bg-card border-l border-border flex flex-col z-10 animate-in slide-in-from-right duration-200 ease-out shadow-2xl">
            {/* Drawer Header */}
            <div className="px-4 py-3 border-b border-border flex items-center justify-between gap-3 bg-input/30 shrink-0">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <h3 className="text-sm font-bold text-foreground truncate">
                  {isCreating ? 'Create New Skill' : formName || formSlug}
                </h3>
                {!isCreating && CORE_SKILL_IDS.has(formSlug) && (
                  <Badge
                    variant="outline"
                    size="xs"
                    className="font-mono text-[9px] border-amber-500/30 text-amber-400 bg-amber-500/10 shrink-0"
                  >
                    System Core
                  </Badge>
                )}
              </div>

              <Button
                variant="ghost"
                size="sm"
                onClick={closeDrawer}
                disabled={isSaving}
                className="w-7 h-7 p-0 text-muted-foreground hover:text-foreground"
                title="Close"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* Drawer Content */}
            <div className="flex-1 flex flex-col min-h-0 overflow-y-auto p-4 space-y-4">
              {/* Creation / Edit Form Inputs */}
              {isCreating ? (
                <div className="space-y-3 shrink-0">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] font-medium text-foreground block mb-1">
                        Skill Name <span className="text-red-400">*</span>
                      </label>
                      <Input
                        value={formName}
                        onChange={(e) => handleNameChange(e.target.value)}
                        placeholder="e.g. Master React Architect"
                        className="h-8 text-xs bg-input/60"
                      />
                    </div>

                    <div>
                      <label className="text-[11px] font-medium text-foreground block mb-1 flex items-center justify-between">
                        <span>Skill Slug (ID) <span className="text-red-400">*</span></span>
                        <span className="text-[9px] font-mono text-muted-foreground">
                          {formSlug.length}/40
                        </span>
                      </label>
                      <Input
                        value={formSlug}
                        onChange={(e) => handleSlugChange(e.target.value)}
                        placeholder="master_react_architect"
                        className={`h-8 text-xs font-mono bg-input/60 ${
                          formSlug && !isSlugValid ? 'border-red-500/80 focus:border-red-500' : ''
                        }`}
                      />
                      {formSlug && !isSlugValid && (
                        <p className="text-[10px] text-red-400 mt-1">
                          Must match ^[a-z0-9_]{'{1,40}'}$ (lowercase, digits, underscores)
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] font-medium text-foreground block mb-1">
                        Domain / Category
                      </label>
                      <Select value={formCategory} onValueChange={setFormCategory}>
                        <SelectTrigger className="h-8 text-xs bg-input/60">
                          <SelectValue placeholder="Select Category" />
                        </SelectTrigger>
                        <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                          {DOMAIN_OPTIONS.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value} className="text-xs">
                              {opt.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <label className="text-[11px] font-medium text-foreground block mb-1">
                        Short Description <span className="text-red-400">*</span>
                      </label>
                      <Input
                        value={formDescription}
                        onChange={(e) => setFormDescription(e.target.value)}
                        placeholder="Brief summary of capabilities..."
                        className="h-8 text-xs bg-input/60"
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 shrink-0">
                  <Callout variant="info" className="p-3 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-foreground">{formSlug}</span>
                      <Badge variant="outline" size="xs" className="capitalize text-[9px] font-mono">
                        {formCategory}
                      </Badge>
                    </div>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      {formDescription || 'No description provided.'}
                    </p>
                  </Callout>

                  {activeDrawerTab === 'edit' && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                      <div>
                        <label className="text-[11px] font-medium text-foreground block mb-1">
                          Domain / Category
                        </label>
                        <Select value={formCategory} onValueChange={setFormCategory}>
                          <SelectTrigger className="h-8 text-xs bg-input/60">
                            <SelectValue placeholder="Select Category" />
                          </SelectTrigger>
                          <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                            {DOMAIN_OPTIONS.map((opt) => (
                              <SelectItem key={opt.value} value={opt.value} className="text-xs">
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <label className="text-[11px] font-medium text-foreground block mb-1">
                          Short Description
                        </label>
                        <Input
                          value={formDescription}
                          onChange={(e) => setFormDescription(e.target.value)}
                          placeholder="Brief description..."
                          className="h-8 text-xs bg-input/60"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tabs for Edit Directives / Preview */}
              <Tabs
                value={activeDrawerTab}
                onValueChange={(val) => setActiveDrawerTab(val as 'preview' | 'edit')}
                className="flex-1 flex flex-col min-h-[300px]"
              >
                <div className="flex items-center justify-between gap-2 pb-2 shrink-0">
                  <TabsList className="h-7 p-0.5">
                    <TabsTrigger value="edit" className="text-xs h-6 px-2.5 gap-1.5">
                      <Edit3 className="w-3 h-3" />
                      <span>Edit Directives</span>
                    </TabsTrigger>
                    <TabsTrigger value="preview" className="text-xs h-6 px-2.5 gap-1.5">
                      <Eye className="w-3 h-3" />
                      <span>Preview</span>
                    </TabsTrigger>
                  </TabsList>

                  <span className="text-[10px] font-mono text-muted-foreground">
                    {formMarkdownDoc.length} chars · {formMarkdownDoc.split('\n').length} lines
                  </span>
                </div>

                <TabsContent value="edit" className="flex-1 flex flex-col min-h-0 mt-0">
                  <textarea
                    value={formMarkdownDoc}
                    onChange={(e) => setFormMarkdownDoc(e.target.value)}
                    placeholder="Enter Markdown directives and standard operating procedures..."
                    className="flex-1 w-full p-3 font-mono text-xs bg-[#0b0f14] text-[#e2e8f0] border border-border rounded-lg resize-none focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed min-h-[260px]"
                    spellCheck={false}
                  />
                </TabsContent>

                <TabsContent value="preview" className="flex-1 min-h-0 mt-0">
                  <ScrollArea className="h-full max-h-[460px] min-h-[260px] rounded-lg border border-border bg-card p-3">
                    <div className="text-xs text-foreground leading-relaxed font-mono whitespace-pre-wrap">
                      {formMarkdownDoc || 'No directives specified.'}
                    </div>
                  </ScrollArea>
                </TabsContent>
              </Tabs>
            </div>

            {/* Drawer Footer with Discard & Save Skill */}
            <div className="px-4 py-3 border-t border-border bg-input/20 flex items-center justify-between gap-2 shrink-0">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={closeDrawer}
                disabled={isSaving}
                className="h-8 px-3 text-xs"
              >
                Discard
              </Button>

              <Button
                type="button"
                size="sm"
                onClick={handleSaveSkill}
                disabled={isSaving || (isCreating && (!formSlug || !isSlugValid))}
                className="h-8 px-3 text-xs gap-1.5 font-medium bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-3.5 h-3.5" />
                    <span>Save Skill</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── 5. ReUI Confirmation Dialog for Skill Deletion ── */}
      <ConfirmDialog
        open={isDeleteDialogOpen}
        onOpenChange={(open) => {
          setIsDeleteDialogOpen(open)
          if (!open) setSkillToDelete(null)
        }}
        title="Delete Skill"
        description={
          skillToDelete
            ? `Are you sure you want to permanently delete "${skillToDelete.name}" (${skillToDelete.id})?`
            : undefined
        }
        warningText="This action is irreversible and purges the declarative skill file from disk."
        confirmText="Delete Skill"
        cancelText="Cancel"
        variant="destructive"
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
      />
    </div>
  )
}
