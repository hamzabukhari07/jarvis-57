from pathlib import Path

file_path = Path("web/src/components/settings/SettingsModal.tsx")
text = file_path.read_text(encoding="utf-8")

# 1. Add Volume2, VolumeX, FolderOpen, Database icons if not already present
text = text.replace(
    "  Loader2,\n} from 'lucide-react'",
    "  Loader2,\n  Volume2,\n  VolumeX,\n  FolderOpen,\n  Database,\n  Trash2,\n  RefreshCw,\n} from 'lucide-react'"
)

# 2. Add state variables for voiceFallback, memoryStats, isPlayingVoice
state_anchor = "  const [ttsEngine, setTtsEngine] = useState('edge_tts')"
new_states = """  const [ttsEngine, setTtsEngine] = useState('edge_tts')
  const [voiceFallback, setVoiceFallback] = useState('auto')
  const [memoryStats, setMemoryStats] = useState<{
    db_path: string
    db_size_kb: number
    turns_count: number
    facts_count: number
    active_workspace: string
    fts5_enabled: boolean
  } | null>(null)
  const [memoryToast, setMemoryToast] = useState<string | null>(null)
  const [isPlayingVoice, setIsPlayingVoice] = useState(false)"""

text = text.replace(state_anchor, new_states)

# 3. In load function, fetch voice_fallback and memory stats
old_load_cfg = "if (cfg.tts_engine) setTtsEngine(cfg.tts_engine)"
new_load_cfg = """if (cfg.tts_engine) setTtsEngine(cfg.tts_engine)
            if (cfg.voice_fallback) setVoiceFallback(cfg.voice_fallback)"""

text = text.replace(old_load_cfg, new_load_cfg)

old_load_end = "load()\n\n      if (audioDevices) {"
new_load_end = """load()
      api.getMemoryStats().then(setMemoryStats).catch(() => {})

      if (audioDevices) {"""

text = text.replace(old_load_end, new_load_end)

# 4. In auto-save, pass voice_fallback
old_save_config = """            pipeline_mode: pipelineMode,
            stt_engine: sttEngine,
            tts_engine: ttsEngine,"""

new_save_config = """            pipeline_mode: pipelineMode,
            stt_engine: sttEngine,
            tts_engine: ttsEngine,
            voice_fallback: voiceFallback,"""

text = text.replace(old_save_config, new_save_config)

# Also in save dependency array
old_dep_arr = "    ttsEngine,\n    geminiKey,"
new_dep_arr = "    ttsEngine,\n    voiceFallback,\n    geminiKey,"
text = text.replace(old_dep_arr, new_dep_arr)

# 5. Add voice preview handler, memory action handlers
handlers_anchor = "  const isLoadedRef = useRef(false)"
new_handlers = """  const isLoadedRef = useRef(false)

  const handlePreviewVoice = (vName: string) => {
    try {
      setIsPlayingVoice(true)
      const audio = new Audio(`/api/preview_voice?voice=${encodeURIComponent(vName.toLowerCase())}`)
      audio.onended = () => setIsPlayingVoice(false)
      audio.onerror = () => {
        setIsPlayingVoice(false)
        if ('speechSynthesis' in window) {
          const u = new SpeechSynthesisUtterance(`Hello, I am ${assistantName}. Voice timbre configured as ${vName}.`)
          window.speechSynthesis.speak(u)
        }
      }
      audio.play().catch(() => {
        setIsPlayingVoice(false)
        if ('speechSynthesis' in window) {
          const u = new SpeechSynthesisUtterance(`Hello, I am ${assistantName}. Voice timbre configured as ${vName}.`)
          window.speechSynthesis.speak(u)
        }
      })
    } catch {
      setIsPlayingVoice(false)
    }
  }

  const handlePickWorkspace = async () => {
    try {
      const res = await fetch('/api/fleet/pick_folder', { method: 'POST' })
      const data = await res.json()
      if (data && data.success && data.path) {
        await api.setWorkspace(data.path)
        const updated = await api.getMemoryStats()
        setMemoryStats(updated)
        setMemoryToast(`Target workspace set to ${data.path}`)
        setTimeout(() => setMemoryToast(null), 3000)
      }
    } catch (e) {
      console.warn('Failed to pick workspace folder:', e)
    }
  }

  const handleResetWorkspace = async () => {
    try {
      await api.setWorkspace('reset')
      const updated = await api.getMemoryStats()
      setMemoryStats(updated)
      setMemoryToast('Workspace reset to repository root')
      setTimeout(() => setMemoryToast(null), 3000)
    } catch (e) {
      console.warn('Failed to reset workspace:', e)
    }
  }

  const handleOptimizeDb = async () => {
    try {
      const res = await api.optimizeMemory()
      const updated = await api.getMemoryStats()
      setMemoryStats(updated)
      setMemoryToast(res.message || 'Database optimized and vacuumed ✓')
      setTimeout(() => setMemoryToast(null), 3000)
    } catch (e) {
      setMemoryToast('Failed to optimize database')
      setTimeout(() => setMemoryToast(null), 3000)
    }
  }

  const handleClearDbHistory = async () => {
    if (!window.confirm('Are you sure you want to clear conversation history turns from zezo_brain.db?')) return
    try {
      const res = await api.clearMemory()
      const updated = await api.getMemoryStats()
      setMemoryStats(updated)
      setMemoryToast(res.message || 'Conversation memory cleared ✓')
      setTimeout(() => setMemoryToast(null), 3000)
    } catch (e) {
      setMemoryToast('Failed to clear conversation history')
      setTimeout(() => setMemoryToast(null), 3000)
    }
  }
"""

text = text.replace(handlers_anchor, new_handlers)

# 6. Update Audio Section to include Pipeline Engine, STT Engine, TTS Engine, and Fallback
old_audio_section = """              {/* ──────────────── 2. AUDIO & SPEECH ──────────────── */}
              {activeSection === 'audio' && (
                <>
                  <div>
                    <h2 className="text-xl font-bold text-foreground tracking-tight">Audio Pipeline & Speech</h2>
                    <p className="text-xs text-muted-foreground mt-1">
                      Configure physical microphone/speaker endpoints and echo cancellation.
                    </p>
                  </div>

                  {/* Section: Physical Hardware Endpoints */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">Physical Endpoints</h3>
                    <div className="rounded-xl bg-card border border-border overflow-hidden divide-y divide-border shadow-xs">
                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Microphone Input Endpoint</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Capture user speech from hardware device</div>
                        </div>
                        <div className="w-64">
                          <Select value={selectedInputDev} onValueChange={setSelectedInputDev}>
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Default Microphone" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              {audioDevices?.inputs?.length ? (
                                audioDevices.inputs.map((d) => (
                                  <SelectItem key={d.name} value={d.name}>
                                    {d.name}
                                  </SelectItem>
                                ))
                              ) : (
                                <SelectItem value="default_mic">Default Microphone</SelectItem>
                              )}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Speaker Output Endpoint</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Render assistant audio to audio device</div>
                        </div>
                        <div className="w-64">
                          <Select value={selectedOutputDev} onValueChange={setSelectedOutputDev}>
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Default Speaker" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              {audioDevices?.outputs?.length ? (
                                audioDevices.outputs.map((d) => (
                                  <SelectItem key={d.name} value={d.name}>
                                    {d.name}
                                  </SelectItem>
                                ))
                              ) : (
                                <SelectItem value="default_spk">Default Speakers</SelectItem>
                              )}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Self-Echo & Mic Bleed Filter</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Filter assistant audio output from being picked up by mic</div>
                        </div>
                        <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10 text-[10px] font-mono">
                          ACTIVE
                        </Badge>
                      </div>
                    </div>
                  </div>
                </>
              )}"""

new_audio_section = """              {/* ──────────────── 2. AUDIO & SPEECH ──────────────── */}
              {activeSection === 'audio' && (
                <>
                  <div>
                    <h2 className="text-xl font-bold text-foreground tracking-tight">Audio Pipeline & Speech</h2>
                    <p className="text-xs text-muted-foreground mt-1">
                      Configure physical endpoints, live speech engines, and offline fallback cascade.
                    </p>
                  </div>

                  {/* Section 1: Audio Pipeline & Architecture */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">Voice Pipeline Engine</h3>
                    <div className="rounded-xl bg-card border border-border overflow-hidden divide-y divide-border shadow-xs">
                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Active Pipeline Mode</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Primary audio interaction loop architecture</div>
                        </div>
                        <div className="w-64">
                          <Select value={pipelineMode} onValueChange={setPipelineMode}>
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs font-mono">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              <SelectItem value="cloud_live">Google Gemini Live (WebSockets, Cloud)</SelectItem>
                              <SelectItem value="cascade">Local Cascade (VAD → STT → LLM → TTS)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Voice Fallback Mode</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Seamless failover to local STT/TTS when Live drops</div>
                        </div>
                        <div className="w-64">
                          <Select value={voiceFallback} onValueChange={setVoiceFallback}>
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs font-mono">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              <SelectItem value="auto">Auto (Failover to Local Pipeline)</SelectItem>
                              <SelectItem value="off">Off (Cloud Live Voice Only)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Speech-to-Text (STT) Engine</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Local transcription engine for voice inputs</div>
                        </div>
                        <div className="w-64">
                          <Select value={sttEngine} onValueChange={setSttEngine}>
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs font-mono">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              <SelectItem value="faster_whisper">Faster-Whisper (GPU / CPU Offline)</SelectItem>
                              <SelectItem value="vosk">Vosk (Low Memory Lightweight)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Text-to-Speech (TTS) Engine</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Spoken vocal response synthesizer</div>
                        </div>
                        <div className="w-64">
                          <Select value={ttsEngine} onValueChange={setTtsEngine}>
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs font-mono">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              <SelectItem value="edge_tts">Edge-TTS (Microsoft Neural Voices)</SelectItem>
                              <SelectItem value="elevenlabs">ElevenLabs (High-Fidelity AI Voice)</SelectItem>
                              <SelectItem value="kokoro">Kokoro (Local Neural Audio)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Section 2: Physical Hardware Endpoints */}
                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">Physical Hardware Endpoints</h3>
                    <div className="rounded-xl bg-card border border-border overflow-hidden divide-y divide-border shadow-xs">
                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Microphone Input Endpoint</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Capture user speech from hardware device</div>
                        </div>
                        <div className="w-64">
                          <Select value={selectedInputDev} onValueChange={setSelectedInputDev}>
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Default Microphone" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              {audioDevices?.inputs?.length ? (
                                audioDevices.inputs.map((d) => (
                                  <SelectItem key={d.name} value={d.name}>
                                    {d.name}
                                  </SelectItem>
                                ))
                              ) : (
                                <SelectItem value="default_mic">Default Microphone</SelectItem>
                              )}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Speaker Output Endpoint</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Render assistant audio to audio device</div>
                        </div>
                        <div className="w-64">
                          <Select value={selectedOutputDev} onValueChange={setSelectedOutputDev}>
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Default Speaker" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              {audioDevices?.outputs?.length ? (
                                audioDevices.outputs.map((d) => (
                                  <SelectItem key={d.name} value={d.name}>
                                    {d.name}
                                  </SelectItem>
                                ))
                              ) : (
                                <SelectItem value="default_spk">Default Speakers</SelectItem>
                              )}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Self-Echo & Mic Bleed Filter</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Filter assistant audio output from being picked up by mic</div>
                        </div>
                        <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10 text-[10px] font-mono">
                          ACTIVE
                        </Badge>
                      </div>
                    </div>
                  </div>
                </>
              )}"""

text = text.replace(old_audio_section, new_audio_section)

# 7. Add Voice Preview button in persona section
old_voice_profile = """                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Live Voice Profile</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Gemini Live speech timbre used during voice conversations</div>
                        </div>
                        <div className="w-64">
                          <Select value={voiceName} onValueChange={setVoiceName}>
                            <SelectTrigger className="h-8 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Select voice" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              <SelectItem value="Charon">Charon (Technical & Confident)</SelectItem>
                              <SelectItem value="Puck">Puck (Expressive & Energetic)</SelectItem>
                              <SelectItem value="Kore">Kore (Warm & Reassuring)</SelectItem>
                              <SelectItem value="Fenrir">Fenrir (Authoritative Executive)</SelectItem>
                              <SelectItem value="Aoede">Aoede (Clear & Adaptive)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>"""

new_voice_profile = """                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Live Voice Profile</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Gemini Live speech timbre used during voice conversations</div>
                        </div>
                        <div className="w-64 flex items-center gap-1.5">
                          <Select value={voiceName} onValueChange={setVoiceName}>
                            <SelectTrigger className="h-8 flex-1 bg-input/60 border-border text-foreground text-xs">
                              <SelectValue placeholder="Select voice" />
                            </SelectTrigger>
                            <SelectContent className="bg-popover border-border text-popover-foreground text-xs">
                              <SelectItem value="Charon">Charon (Technical & Confident)</SelectItem>
                              <SelectItem value="Puck">Puck (Expressive & Energetic)</SelectItem>
                              <SelectItem value="Kore">Kore (Warm & Reassuring)</SelectItem>
                              <SelectItem value="Fenrir">Fenrir (Authoritative Executive)</SelectItem>
                              <SelectItem value="Aoede">Aoede (Clear & Adaptive)</SelectItem>
                            </SelectContent>
                          </Select>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={isPlayingVoice}
                            onClick={() => handlePreviewVoice(voiceName)}
                            className="h-8 px-2 font-mono text-[10px] shrink-0 gap-1 text-[var(--primary)] border-[var(--primary)]/30 hover:bg-[var(--primary)]/10"
                            title="Preview Voice Sample"
                          >
                            <Volume2 className="w-3.5 h-3.5" />
                            <span>{isPlayingVoice ? 'Playing...' : 'Test'}</span>
                          </Button>
                        </div>
                      </div>"""

text = text.replace(old_voice_profile, new_voice_profile)

# 8. Update Memory Section with Real Interactive Stats and Controls
old_memory_section = """              {/* ──────────────── 6. MEMORY & INTELLIGENCE ──────────────── */}
              {activeSection === 'memory' && (
                <>
                  <div>
                    <h2 className="text-xl font-bold text-foreground tracking-tight">Memory & Intelligence</h2>
                    <p className="text-xs text-muted-foreground mt-1">
                      Inspect SQLite FTS5 persistence, BM25 memory buffer, and active workspace paths.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">Memory Engine</h3>
                    <div className="rounded-xl bg-card border border-border overflow-hidden divide-y divide-border shadow-xs">
                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Database Engine</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">zezo_brain.db with BM25 full-text indexing</div>
                        </div>
                        <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10 text-[10px] font-mono">
                          ONLINE
                        </Badge>
                      </div>

                      <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Active Target Workspace</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Target directory for code synthesis & modifications</div>
                        </div>
                        <span className="text-xs font-mono text-muted-foreground">c:\...\jarvis-57</span>
                      </div>
                    </div>
                  </div>
                </>
              )}"""

new_memory_section = """              {/* ──────────────── 6. MEMORY & INTELLIGENCE ──────────────── */}
              {activeSection === 'memory' && (
                <>
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-bold text-foreground tracking-tight">Memory & Intelligence</h2>
                      <p className="text-xs text-muted-foreground mt-1">
                        Inspect SQLite FTS5 persistence, BM25 memory buffer, and active workspace paths.
                      </p>
                    </div>
                    {memoryToast && (
                      <span className="text-xs font-mono text-primary bg-primary/10 border border-primary/30 px-2.5 py-1 rounded-md animate-in fade-in">
                        {memoryToast}
                      </span>
                    )}
                  </div>

                  <div className="space-y-4">
                    {/* Database Health & Metrics Card */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">
                          Memory Engine Telemetry
                        </h3>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => api.getMemoryStats().then(setMemoryStats).catch(() => {})}
                          className="h-6 text-[10px] px-2 font-mono gap-1 text-muted-foreground hover:text-foreground"
                        >
                          <RefreshCw className="w-3 h-3" />
                          <span>Refresh Stats</span>
                        </Button>
                      </div>

                      <div className="rounded-xl bg-card border border-border overflow-hidden divide-y divide-border shadow-xs">
                        <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                          <div>
                            <div className="text-xs font-semibold text-foreground">Database Engine</div>
                            <div className="text-[11px] text-muted-foreground mt-0.5">
                              {memoryStats?.db_path || 'memory/zezo_brain.db'} • SQLite WAL Mode
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-foreground font-semibold">
                              {memoryStats?.db_size_kb || 0} KB
                            </span>
                            <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10 text-[10px] font-mono">
                              FTS5 ONLINE
                            </Badge>
                          </div>
                        </div>

                        <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                          <div>
                            <div className="text-xs font-semibold text-foreground">Conversation History</div>
                            <div className="text-[11px] text-muted-foreground mt-0.5">Turn-by-turn user directives and assistant responses</div>
                          </div>
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted text-foreground border border-border font-semibold">
                            {memoryStats?.turns_count || 0} TURNS
                          </span>
                        </div>

                        <div className="flex items-center justify-between p-3.5 hover:bg-muted/30 transition-colors">
                          <div>
                            <div className="text-xs font-semibold text-foreground">Episodic Knowledge Facts</div>
                            <div className="text-[11px] text-muted-foreground mt-0.5">Long-term verified facts extracted from conversations</div>
                          </div>
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted text-foreground border border-border font-semibold">
                            {memoryStats?.facts_count || 0} FACTS
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Active Target Workspace */}
                    <div className="space-y-2">
                      <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">
                        Active Target Workspace
                      </h3>
                      <div className="rounded-xl bg-card border border-border p-3.5 space-y-2.5 shadow-xs">
                        <div className="flex items-center justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                              <FolderOpen className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                              <span className="truncate">Root Workspace Directory</span>
                            </div>
                            <div className="text-[11px] font-mono text-muted-foreground truncate mt-0.5" title={memoryStats?.active_workspace}>
                              {memoryStats?.active_workspace || 'c:/Users/Hamza Bukhari/Documents/antigravity/jarvis-57'}
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={handlePickWorkspace}
                              className="h-7 text-xs px-2.5 gap-1 font-mono text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/10"
                            >
                              <FolderOpen className="w-3.5 h-3.5" />
                              <span>Browse</span>
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={handleResetWorkspace}
                              className="h-7 text-xs px-2 font-mono text-muted-foreground hover:text-foreground"
                              title="Reset workspace to default repository root"
                            >
                              <span>Reset</span>
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Maintenance Actions */}
                    <div className="space-y-2">
                      <h3 className="text-xs font-semibold text-foreground/80 tracking-wide uppercase">
                        Database Maintenance
                      </h3>
                      <div className="rounded-xl bg-card border border-border p-3.5 flex flex-wrap items-center justify-between gap-3 shadow-xs">
                        <div>
                          <div className="text-xs font-semibold text-foreground">Database Optimization</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5">Execute PRAGMA optimize & VACUUM to reclaim disk space</div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={handleOptimizeDb}
                            className="h-7 text-xs px-3 gap-1 font-mono"
                          >
                            <Database className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Vacuum DB</span>
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={handleClearDbHistory}
                            className="h-7 text-xs px-3 gap-1 font-mono text-red-400 border-red-500/30 hover:bg-red-500/10"
                          >
                            <Trash2 className="w-3.5 h-3.5 text-red-400" />
                            <span>Clear Turns</span>
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}"""

text = text.replace(old_memory_section, new_memory_section)

file_path.write_text(text, encoding="utf-8")
print("SettingsModal.tsx successfully updated with real audio controls, voice preview, and live memory engine!")

