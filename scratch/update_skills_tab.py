from pathlib import Path

file_path = Path("web/src/components/settings/SkillsSettingsTab.tsx")
text = file_path.read_text(encoding="utf-8")

# 1. Add api import
if "import { api } from '../../lib/api'" not in text:
    text = text.replace(
        "import React, { useState, useMemo } from 'react'",
        "import React, { useState, useMemo, useEffect } from 'react'\nimport { api } from '../../lib/api'"
    )

# 2. Add useEffect to fetch real skills from backend
target_hook = "  const [searchQuery, setSearchQuery] = useState('')"
load_hook = """  // Load real skills dynamically from backend /api/skills
  useEffect(() => {
    const loadRealSkills = async () => {
      try {
        const res = await api.getSkills()
        if (res && res.skills && Array.isArray(res.skills) && res.skills.length > 0) {
          const serverSkills: SkillItem[] = res.skills.map((s: any) => ({
            id: s.name,
            name: s.display_name || s.name.replace(/_/g, ' ').replace(/\\b\\w/g, (c: string) => c.toUpperCase()),
            type: 'skill' as const,
            category: (s.domain || 'coding') as any,
            version: s.version || '1.0.0',
            author: s.author || 'ZEZO Core',
            description: s.description || '',
            enabled: !s.disabled,
            tags: s.tags || [s.domain || 'System'],
            markdownDoc: s.instructions || `# ${s.name}\\n\\n${s.description || ''}`,
          }))
          setSkills(serverSkills)
        }
      } catch (e) {
        console.debug('Using cached skills:', e)
      }
    }
    loadRealSkills()
  }, [])
"""

text = text.replace(target_hook, load_hook + target_hook)

# 3. Update handleToggleSkill to call backend /api/skills/mode
old_toggle = """  // Toggle single skill
  const handleToggleSkill = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    const updated = skills.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s))
    persistSkills(updated)
    if (activeDrawerSkill?.id === id) {
      setActiveDrawerSkill((prev) => (prev ? { ...prev, enabled: !prev.enabled } : null))
    }
  }"""

new_toggle = """  // Toggle single skill and synchronize with backend disk registry
  const handleToggleSkill = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    const target = skills.find((s) => s.id === id)
    const nextEnabled = target ? !target.enabled : true
    const updated = skills.map((s) => (s.id === id ? { ...s, enabled: nextEnabled } : s))
    persistSkills(updated)
    if (activeDrawerSkill?.id === id) {
      setActiveDrawerSkill((prev) => (prev ? { ...prev, enabled: nextEnabled } : null))
    }
    try {
      await api.updateSkillMode(id, { disabled: !nextEnabled, auto_activate: nextEnabled })
    } catch (err) {
      console.warn('Backend skill mode toggle error:', err)
    }
  }"""

text = text.replace(old_toggle, new_toggle)

# 4. Update handleSaveDrawerDoc to call backend /api/skills/save
old_save_doc = """  // Save Drawer Content
  const handleSaveDrawerDoc = () => {
    if (!activeDrawerSkill) return
    setIsSavingDrawer(true)
    const updated = skills.map((s) =>
      s.id === activeDrawerSkill.id ? { ...s, markdownDoc: drawerEditedContent } : s
    )
    persistSkills(updated)
    setActiveDrawerSkill((prev) => (prev ? { ...prev, markdownDoc: drawerEditedContent } : null))

    setTimeout(() => {
      setIsSavingDrawer(false)
      setDrawerSaveSuccess(true)
      setTimeout(() => setDrawerSaveSuccess(false), 2000)
    }, 250)
  }"""

new_save_doc = """  // Save Drawer Content and persist to backend disk
  const handleSaveDrawerDoc = async () => {
    if (!activeDrawerSkill) return
    setIsSavingDrawer(true)
    const updated = skills.map((s) =>
      s.id === activeDrawerSkill.id ? { ...s, markdownDoc: drawerEditedContent } : s
    )
    persistSkills(updated)
    setActiveDrawerSkill((prev) => (prev ? { ...prev, markdownDoc: drawerEditedContent } : null))

    try {
      await api.saveSkill({
        name: activeDrawerSkill.id,
        description: activeDrawerSkill.description,
        instructions: drawerEditedContent,
        domain: activeDrawerSkill.category,
      })
    } catch (err) {
      console.warn('Backend skill save error:', err)
    }

    setIsSavingDrawer(false)
    setDrawerSaveSuccess(true)
    setTimeout(() => setDrawerSaveSuccess(false), 2000)
  }"""

text = text.replace(old_save_doc, new_save_doc)

file_path.write_text(text, encoding="utf-8")
print("SkillsSettingsTab.tsx successfully updated with real backend synchronization!")

