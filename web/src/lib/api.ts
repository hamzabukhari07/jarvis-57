import type { AgentProfile, PipelineSettings, ZezoTelemetry } from '../types/zezo'

const API_BASE = '' // Vite proxy handles /api -> http://127.0.0.1:8000/api

export interface FleetStateResponse {
  fleet?: AgentProfile[]
  agents?: Record<string, AgentProfile>
  telemetry?: ZezoTelemetry
}

export interface ModelOption {
  id: string
  name: string
  provider: string
}

export interface AvailableModelsResponse {
  models?: ModelOption[]
  gemini?: string[]
  groq?: string[]
  antigravity?: string[]
  opencode?: string[]
  kilo?: string[]
}

export const api = {
  async getFleetState(): Promise<FleetStateResponse> {
    const res = await fetch(`${API_BASE}/api/fleet/state`)
    if (!res.ok) throw new Error(`Failed to fetch fleet state: ${res.statusText}`)
    return res.json()
  },

  async sendAgentChat(
    agentId: string,
    message: string,
    engine?: string,
    model?: string
  ): Promise<{ response?: string; reply?: string; status?: string; task_id?: string; engine?: string; model?: string }> {
    const res = await fetch(`${API_BASE}/api/fleet/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId, message, engine, model }),
    })
    if (!res.ok) throw new Error(`Agent chat failed: ${res.statusText}`)
    return res.json()
  },

  async dispatchTask(payload: {
    agent_id: string
    prompt: string
    worktree?: string
    tool?: string
    model?: string
  }): Promise<{ status: string; task_id?: string; message?: string }> {
    const res = await fetch(`${API_BASE}/api/fleet/dispatch_task`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`Task dispatch failed: ${res.statusText}`)
    return res.json()
  },

  async saveAgent(agent: AgentProfile): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/api/fleet/save_agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(agent),
    })
    if (!res.ok) throw new Error(`Save agent failed: ${res.statusText}`)
    return res.json()
  },

  async updateAgent(agentId: string, updates: Partial<AgentProfile>): Promise<{ status: string }> {
    return this.saveAgent({ id: agentId, ...updates } as AgentProfile)
  },

  async deleteAgent(agentId: string): Promise<{ success: boolean }> {
    const res = await fetch(`${API_BASE}/api/fleet/delete_agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId }),
    })
    if (!res.ok) throw new Error(`Delete agent failed: ${res.statusText}`)
    return res.json()
  },

  async getModels(): Promise<AvailableModelsResponse> {
    try {
      const res = await fetch(`${API_BASE}/api/models`)
      if (!res.ok) return {}
      return res.json()
    } catch {
      return {}
    }
  },

  async getSettings(): Promise<PipelineSettings> {
    const res = await fetch(`${API_BASE}/api/settings/pipeline`)
    if (!res.ok) throw new Error(`Failed to fetch settings: ${res.statusText}`)
    return res.json()
  },

  async saveSettings(settings: Partial<PipelineSettings>): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/api/settings/pipeline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    })
    if (!res.ok) throw new Error(`Failed to save settings: ${res.statusText}`)
    return res.json()
  },

  async getConfig(): Promise<any> {
    try {
      const res = await fetch(`${API_BASE}/api/config`)
      if (!res.ok) return await this.getSettings()
      return res.json()
    } catch {
      return this.getSettings()
    }
  },

  async saveConfig(config: any): Promise<{ status: string }> {
    try {
      const res = await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (!res.ok) return await this.saveSettings(config)
      return res.json()
    } catch {
      return this.saveSettings(config)
    }
  },

  async getTasks(): Promise<any[]> {
    try {
      const res = await fetch(`${API_BASE}/api/tasks`)
      if (!res.ok) return []
      const data = await res.json()
      return data.tasks || []
    } catch {
      return []
    }
  },

  async saveAssistantSettings(payload: any): Promise<any> {
    const res = await fetch(`${API_BASE}/api/settings/assistant`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`Failed to save assistant settings: ${res.statusText}`)
    return res.json()
  },

  async saveKeysSettings(payload: any): Promise<any> {
    const res = await fetch(`${API_BASE}/api/settings/keys`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`Failed to save keys: ${res.statusText}`)
    return res.json()
  },

  async getSkills(): Promise<any> {
    try {
      const res = await fetch(`${API_BASE}/api/skills`)
      if (!res.ok) return { skills: [] }
      return res.json()
    } catch {
      return { skills: [] }
    }
  },

  async updateSkillMode(name: string, payload: { pinned?: boolean; disabled?: boolean; auto_activate?: boolean }): Promise<any> {
    const res = await fetch(`${API_BASE}/api/skills/mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, ...payload }),
    })
    if (!res.ok) throw new Error(`Failed to update skill mode: ${res.statusText}`)
    return res.json()
  },

  async saveSkill(data: { name: string; description?: string; instructions?: string; domain?: string }): Promise<any> {
    const res = await fetch(`${API_BASE}/api/skills/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(`Failed to save skill: ${res.statusText}`)
    return res.json()
  },

  async deleteSkill(name: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/skills/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    if (!res.ok) throw new Error(`Failed to delete skill: ${res.statusText}`)
    return res.json()
  },

  async getMemoryStats(): Promise<{
    status: string
    db_path: string
    db_size_kb: number
    turns_count: number
    facts_count: number
    active_workspace: string
    fts5_enabled: boolean
  }> {
    const res = await fetch(`${API_BASE}/api/memory/stats`)
    if (!res.ok) throw new Error(`Failed to fetch memory stats: ${res.statusText}`)
    return res.json()
  },

  async clearMemory(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/api/memory/clear`, { method: 'POST' })
    if (!res.ok) throw new Error(`Failed to clear memory: ${res.statusText}`)
    return res.json()
  },

  async wipeAllMemory(): Promise<{
    status: string
    message: string
    sqlite_deleted?: Record<string, number>
    vault_deleted_conv_files?: number
  }> {
    const res = await fetch(`${API_BASE}/api/memory/wipe_all`, { method: 'POST' })
    if (!res.ok) throw new Error(`Failed to wipe all memory: ${res.statusText}`)
    return res.json()
  },

  async optimizeMemory(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/api/memory/optimize`, { method: 'POST' })
    if (!res.ok) throw new Error(`Failed to optimize memory: ${res.statusText}`)
    return res.json()
  },

  async setWorkspace(path: string): Promise<{ status: string; active_workspace: string }> {
    const res = await fetch(`${API_BASE}/api/workspace/set`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    })
    if (!res.ok) throw new Error(`Failed to set workspace: ${res.statusText}`)
    return res.json()
  },

  async getSystemStatus(): Promise<ZezoTelemetry> {
    const res = await fetch(`${API_BASE}/api/system/status`)
    if (!res.ok) throw new Error(`Failed to fetch system status: ${res.statusText}`)
    return res.json()
  },

  async getAttachments(): Promise<any[]> {
    try {
      const res = await fetch(`${API_BASE}/api/attachments`)
      if (!res.ok) return []
      const data = await res.json()
      return data.attachments || []
    } catch {
      return []
    }
  },

  async uploadFiles(formData: FormData): Promise<any> {
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`)
    return res.json()
  },

  async getRemoteGateway(): Promise<{ status: string; url: string; key: string; login_url: string }> {
    const res = await fetch(`${API_BASE}/api/remote`)
    if (!res.ok) throw new Error(`Failed to fetch remote gateway: ${res.statusText}`)
    return res.json()
  },

  async requestNewRemoteKey(): Promise<{ status: string; url: string; key: string; login_url: string }> {
    const res = await fetch(`${API_BASE}/api/remote/new_key`, { method: 'POST' })
    if (!res.ok) throw new Error(`Failed to generate new remote key: ${res.statusText}`)
    return res.json()
  },

  async getBackendLogs(minLevel = 'DEBUG'): Promise<{ status: string; lines: any[]; stats: any; sources: string[] }> {
    try {
      const res = await fetch(`${API_BASE}/api/backend_logs?min_level=${encodeURIComponent(minLevel)}`)
      if (!res.ok) return { status: 'error', lines: [], stats: {}, sources: [] }
      return res.json()
    } catch {
      return { status: 'error', lines: [], stats: {}, sources: [] }
    }
  },

  async clearBackendLogs(): Promise<void> {
    try {
      await fetch(`${API_BASE}/api/backend_logs/clear`, { method: 'POST' })
    } catch { }
  },

  /* ── Obsidian Markdown Vault & Knowledge Graph ── */
  async getMemoryGraph(): Promise<{
    status: string
    nodes: Array<{
      id: string
      label: string
      category: string
      file: string
      snippet: string
      color: string
      size: number
      tags: string[]
    }>
    links: Array<{
      source: string
      target: string
      value: number
    }>
    stats: {
      total_notes: number
      total_links: number
      categories: string[]
    }
  }> {
    const res = await fetch(`${API_BASE}/api/memory/graph`)
    if (!res.ok) throw new Error(`Failed to fetch memory graph: ${res.statusText}`)
    return res.json()
  },

  async getMemoryNotes(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/api/memory/notes`)
    if (!res.ok) return []
    const data = await res.json()
    return data.notes || []
  },

  async getMemoryNote(fileOrId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/memory/note?file=${encodeURIComponent(fileOrId)}`)
    if (!res.ok) throw new Error(`Failed to fetch note: ${res.statusText}`)
    const data = await res.json()
    return data.note
  },

  async saveMemoryNote(file: string, content: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/memory/note`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file, content }),
    })
    if (!res.ok) throw new Error(`Failed to save note: ${res.statusText}`)
    return res.json()
  },

  async createMemoryNote(payload: { title: string; category: string; content: string; tags?: string[] }): Promise<any> {
    const res = await fetch(`${API_BASE}/api/memory/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`Failed to create note: ${res.statusText}`)
    return res.json()
  },

  async deleteMemoryNote(file: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/memory/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file }),
    })
    if (!res.ok) throw new Error(`Failed to delete note: ${res.statusText}`)
    return res.json()
  },

  async getAudioDevices(): Promise<any> {
    const res = await fetch(`${API_BASE}/api/audio_devices`)
    if (!res.ok) throw new Error(`Failed to fetch audio devices: ${res.statusText}`)
    return res.json()
  },
}
