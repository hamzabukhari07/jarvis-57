export interface AgentProfile {
  id: string
  name: string
  displayName?: string
  role: string
  specialty: string
  color: string
  avatar_pixel?: string
  default_tool: string
  risk_tier: string
  model_id: string
  engine?: string
  status?: string
  worktree_branch?: string | null
  active_worktree?: string | null
  worktree?: string | null
  desk_x?: number
  desk_y?: number
  state?: 'idle' | 'working' | 'walking' | 'talking' | 'break'
  isBusy?: boolean
  logs?: string[]
  allowed_tools?: string[]
  allowed_skills?: string[]
  prompt_prefix?: string
  desk_coordinates?: { x: number; y: number }
}

export interface ZezoTelemetry {
  cpu_percent: number
  ram_percent: number
  gpu_percent?: number
  battery_percent?: number
  battery_charging?: boolean
}

export interface PipelineSettings {
  pipeline_mode: string
  stt_engine: string
  llm_engine: string
  tts_engine: string
  tts_voice: string
  voice_fallback: string
  voice_fallback_enabled: boolean
  has_gemini_key: boolean
  gemini_api_key_masked: string
  has_groq_key: boolean
  groq_api_key_masked: string
  has_elevenlabs_key: boolean
  elevenlabs_api_key_masked: string
}

export interface ChatMessage {
  id: string
  sender: 'user' | 'agent' | 'system'
  agentName?: string
  text: string
  time: string
  type?: 'text' | 'tool_call' | 'thought' | 'diff'
  toolMeta?: {
    toolName: string
    status: 'running' | 'completed' | 'failed'
    output?: string
  }
}

