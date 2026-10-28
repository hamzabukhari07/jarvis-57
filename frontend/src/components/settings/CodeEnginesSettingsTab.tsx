import { useState, useEffect, useCallback, useMemo } from 'react'
import { Card } from '../reui/card'
import { Badge } from '../reui/badge'
import { Callout } from '../reui/callout'
import { Button } from '../ui/button'
import { Switch } from '../ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import {
  Terminal,
  RefreshCw,
  Key,
  Download,
  FolderOpen,
  AlertTriangle,
  Loader2,
  Copy,
  Check,
} from 'lucide-react'
import { api, type CodeEngineStatus } from '../../lib/api'
import { cn } from '../../lib/utils'

const DEFAULT_FALLBACK_ENGINES: CodeEngineStatus[] = [
  {
    id: 'antigravity',
    label: 'Antigravity CLI',
    short_code: 'AG',
    state: 'unknown',
    binary_path: null,
    version: null,
    models: [
      'gemini-3.7-flash-high',
      'gemini-3.7-flash-medium',
      'claude-sonnet-5-5',
      'claude-opus-5-5',
    ],
    reason: 'Checking engine readiness...',
    backs_tool: 'antigravity_action',
    timestamp: 0,
  },
  {
    id: 'opencode',
    label: 'OpenCode',
    short_code: 'OC',
    state: 'unknown',
    binary_path: null,
    version: null,
    models: [
      'glm-5.3-flash-free',
      'mimo-v2.5-free',
      'opencode/nemotron-3-ultra-free',
    ],
    reason: 'Checking engine readiness...',
    backs_tool: 'opencode_action',
    timestamp: 0,
  },
  {
    id: 'kilo',
    label: 'Kilo Code',
    short_code: 'KC',
    state: 'unknown',
    binary_path: null,
    version: null,
    models: ['kilo/free', 'kilo/fast-code'],
    reason: 'Checking engine readiness...',
    backs_tool: 'kilo_action',
    timestamp: 0,
  },
]

export function CodeEnginesSettingsTab() {
  const [engines, setEngines] = useState<CodeEngineStatus[]>(DEFAULT_FALLBACK_ENGINES)
  const [defaultEngine, setDefaultEngine] = useState<string>('antigravity')
  const [loading, setLoading] = useState<boolean>(true)
  const [probingMap, setProbingMap] = useState<Record<string, boolean>>({})
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null)
  const [activeInstallModal, setActiveInstallModal] = useState<string | null>(null)

  // Local enable state persisted in localStorage
  const [enabledEngines, setEnabledEngines] = useState<Record<string, boolean>>(() => {
    try {
      const stored = localStorage.getItem('zezo_enabled_code_engines')
      return stored ? JSON.parse(stored) : { antigravity: true, opencode: true, kilo: true }
    } catch {
      return { antigravity: true, opencode: true, kilo: true }
    }
  })

  const loadEngines = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.getCodeEngines()
      if (res && res.engines) {
        setEngines(res.engines)
      }
      if (res && res.default_engine) {
        setDefaultEngine(res.default_engine)
      }
    } catch (e) {
      console.error('Failed to load code engines status:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadEngines()
  }, [loadEngines])

  const handleProbeSingle = async (engineId: string) => {
    setProbingMap((prev) => ({ ...prev, [engineId]: true }))
    try {
      const res = await api.probeEngine(engineId)
      if (res && res.engine) {
        setEngines((prev) =>
          prev.map((e) => (e.id === engineId ? res.engine! : e))
        )
      }
    } catch (e) {
      console.error(`Failed to probe engine ${engineId}:`, e)
    } finally {
      setProbingMap((prev) => ({ ...prev, [engineId]: false }))
    }
  }

  const handleProbeAll = async () => {
    setLoading(true)
    try {
      const res = await api.probeEngine()
      if (res && res.engines) {
        setEngines(res.engines)
      }
      if (res && res.default_engine) {
        setDefaultEngine(res.default_engine)
      }
    } catch (e) {
      console.error('Failed to probe all engines:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleSetDefault = async (engineId: string) => {
    setDefaultEngine(engineId)
    try {
      await api.setDefaultCodeEngine(engineId)
    } catch (e) {
      console.error(`Failed to set default code engine to ${engineId}:`, e)
    }
  }

  const handleToggleEngine = (engineId: string, checked: boolean) => {
    setEnabledEngines((prev) => {
      const next = { ...prev, [engineId]: checked }
      try {
        localStorage.setItem('zezo_enabled_code_engines', JSON.stringify(next))
      } catch {}
      return next
    })

    if (!checked && engineId === defaultEngine) {
      const fallback = engines.find(
        (e) => e.id !== engineId && enabledEngines[e.id] !== false
      )
      if (fallback) {
        setDefaultEngine(fallback.id)
        api.setDefaultCodeEngine(fallback.id).catch((err) => {
          console.error(`Failed to set default code engine to ${fallback.id}:`, err)
        })
      }
    }
  }

  const handleOpenFolder = async (path: string) => {
    try {
      // Extract directory path if it's a file
      const dirPath = path.replace(/[/\\][^/\\]+$/, '')
      await fetch('/api/fleet/open_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: dirPath }),
      })
    } catch (e) {
      console.error('Failed to open folder:', e)
    }
  }

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedCmd(id)
    setTimeout(() => setCopiedCmd(null), 2000)
  }

  // Tally counts
  const readyCount = useMemo(
    () => engines.filter((e) => e.state === 'ready').length,
    [engines]
  )
  const needsAuthCount = useMemo(
    () => engines.filter((e) => e.state === 'sign_in_required').length,
    [engines]
  )
  const missingCount = useMemo(
    () => engines.filter((e) => e.state === 'not_installed').length,
    [engines]
  )

  // Default engine resolution and active fallback
  const currentDefault = useMemo(
    () => engines.find((e) => e.id === defaultEngine) || engines[0],
    [engines, defaultEngine]
  )

  const activeFallback = useMemo(() => {
    if (!currentDefault || currentDefault.state === 'ready') return null
    return engines.find((e) => e.id !== currentDefault.id && e.state === 'ready') || null
  }, [currentDefault, engines])

  const renderBadge = (engine: CodeEngineStatus, isProbing: boolean) => {
    if (isProbing) {
      return (
        <Badge variant="outline" size="xs" radius="full" className="text-muted-foreground gap-1">
          <Loader2 className="w-2.5 h-2.5 animate-spin" />
          Probing...
        </Badge>
      )
    }

    if (engine.state === 'ready') {
      return (
        <Badge variant="completed" size="xs" radius="full" className="gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          Ready
        </Badge>
      )
    }

    if (engine.state === 'sign_in_required') {
      return (
        <Badge variant="warning" size="xs" radius="full" className="gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          Sign in required
        </Badge>
      )
    }

    if (engine.state === 'not_installed') {
      return (
        <Badge variant="secondary" size="xs" radius="full" className="gap-1 opacity-80">
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" />
          Not installed
        </Badge>
      )
    }

    return (
      <Badge variant="outline" size="xs" radius="full" className="gap-1">
        Unknown
      </Badge>
    )
  }

  return (
    <div className="space-y-6 text-foreground">
      {/* Pane Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Terminal className="w-5 h-5 text-primary" />
            Code Engines
          </h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-2xl leading-relaxed">
            These are the command-line agents ZEZO hands coding work to. ZEZO runs an engine
            only when it is installed and signed in. Anything else produces no files.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={loading}
          onClick={handleProbeAll}
          className="h-8 text-xs shrink-0"
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
          )}
          Re-probe all
        </Button>
      </div>

      {/* Summary Strip */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-border bg-card text-xs text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <b className="font-semibold text-foreground">{readyCount}</b> ready
        </span>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-border bg-card text-xs text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <b className="font-semibold text-foreground">{needsAuthCount}</b> needs sign-in
        </span>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-border bg-card text-xs text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-zinc-500" />
          <b className="font-semibold text-foreground">{missingCount}</b> not installed
        </span>
      </div>

      {/* Routing & Fallback Notification */}
      {currentDefault && currentDefault.state !== 'ready' && activeFallback && (
        <Callout variant="warning" className="flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-500 flex-none mt-0.5" />
          <div className="text-xs leading-relaxed">
            <span className="font-semibold text-foreground">{currentDefault.label}</span> is the default
            engine but is currently {currentDefault.state === 'sign_in_required' ? 'not signed in' : 'unavailable'}.
            ZEZO will automatically route autonomous tasks to{' '}
            <span className="font-semibold text-foreground">{activeFallback.label}</span> until it is ready.
            You can sign in below or switch the default engine.
          </div>
        </Callout>
      )}

      {/* Engine Cards List */}
      <div className="space-y-4">
        {engines.map((engine) => {
          const isProbing = Boolean(probingMap[engine.id])
          const isEnabled = enabledEngines[engine.id] !== false
          const isWarn = engine.state === 'sign_in_required'
          const isOff = engine.state === 'not_installed'

          return (
            <Card
              key={engine.id}
              className={cn(
                'p-4.5 flex flex-col gap-3.5 transition-colors border',
                isWarn && 'border-amber-500/40 bg-amber-500/5',
                isOff && 'opacity-85 bg-card/60'
              )}
            >
              {/* Header: Mark + Identity + Status */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <div className="w-9 h-9 rounded-lg border border-border bg-muted/40 font-mono text-xs font-semibold flex items-center justify-center text-foreground flex-none">
                    {engine.short_code}
                  </div>
                  <div className="flex flex-col min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <strong className="text-sm font-semibold text-foreground">
                        {engine.label}
                      </strong>
                      {renderBadge(engine, isProbing)}
                      {defaultEngine === engine.id && (
                        <Badge variant="outline" size="xs" radius="full" className="text-primary border-primary/40">
                          Default
                        </Badge>
                      )}
                    </div>
                    <div
                      className="font-mono text-[11px] text-muted-foreground truncate mt-0.5"
                      title={engine.binary_path || 'Binary not located'}
                    >
                      {engine.binary_path ? (
                        <>
                          {engine.binary_path} {engine.version && `· v${engine.version}`}
                        </>
                      ) : (
                        `Not found on PATH or in vendor directories`
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Status Explanation / Reason */}
              <p className="text-xs text-muted-foreground leading-relaxed">
                {engine.reason}
              </p>

              {/* Models Metadata Row */}
              {engine.models && engine.models.length > 0 && (
                <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/80 mr-1">
                    Models
                  </span>
                  {engine.models.slice(0, 3).map((m) => (
                    <span
                      key={m}
                      className="font-mono text-[10.5px] px-2 py-0.5 rounded-md bg-muted/50 border border-border/80 text-foreground"
                    >
                      {m}
                    </span>
                  ))}
                  {engine.models.length > 3 && (
                    <span className="font-mono text-[10.5px] px-2 py-0.5 rounded-md bg-muted/30 border border-border/50 text-muted-foreground">
                      +{engine.models.length - 3} more
                    </span>
                  )}
                </div>
              )}

              {/* Action Buttons Row */}
              <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-border/50">
                {engine.state === 'sign_in_required' && (
                  <Button
                    size="sm"
                    className="h-7 text-xs bg-amber-500 hover:bg-amber-600 text-black font-semibold"
                    onClick={() => {
                      if (engine.id === 'antigravity') {
                        copyToClipboard('agy auth login', 'auth_agy')
                      } else {
                        copyToClipboard(`${engine.id} auth login`, `auth_${engine.id}`)
                      }
                    }}
                  >
                    <Key className="w-3.5 h-3.5 mr-1" />
                    {copiedCmd === `auth_${engine.id}` || copiedCmd === 'auth_agy' ? 'Command copied!' : 'Sign in'}
                  </Button>
                )}

                {engine.state === 'not_installed' && (
                  <Button
                    size="sm"
                    className="h-7 text-xs bg-primary hover:bg-primary/90 text-primary-foreground font-medium"
                    onClick={() => setActiveInstallModal(activeInstallModal === engine.id ? null : engine.id)}
                  >
                    <Download className="w-3.5 h-3.5 mr-1" />
                    Install
                  </Button>
                )}

                {engine.state === 'ready' && defaultEngine !== engine.id && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => handleSetDefault(engine.id)}
                  >
                    Set as default
                  </Button>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  disabled={isProbing}
                  onClick={() => handleProbeSingle(engine.id)}
                >
                  {isProbing ? (
                    <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                  ) : (
                    <RefreshCw className="w-3.5 h-3.5 mr-1" />
                  )}
                  Test
                </Button>

                {engine.binary_path && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-muted-foreground hover:text-foreground"
                    onClick={() => handleOpenFolder(engine.binary_path!)}
                  >
                    <FolderOpen className="w-3.5 h-3.5 mr-1" />
                    Open folder
                  </Button>
                )}

                {/* Right-aligned toggle */}
                <div className="ml-auto flex items-center gap-2">
                  <Switch
                    checked={isEnabled && engine.state !== 'sign_in_required'}
                    disabled={engine.state === 'sign_in_required'}
                    onCheckedChange={(checked) => handleToggleEngine(engine.id, checked)}
                  />
                  <span className="text-[11px] text-muted-foreground">
                    {engine.state === 'sign_in_required' ? 'off until signed in' : 'Use for coding tasks'}
                  </span>
                </div>
              </div>

              {/* Install instructions drop-panel if clicked */}
              {activeInstallModal === engine.id && (
                <div className="mt-2 p-3 rounded-lg border border-border bg-muted/30 space-y-2 text-xs">
                  <div className="font-semibold text-foreground flex items-center gap-1.5">
                    <Download className="w-3.5 h-3.5 text-primary" />
                    Installation instructions for {engine.label}
                  </div>
                  <div className="flex items-center gap-2">
                    <code className="font-mono text-[11px] bg-background px-2.5 py-1 rounded border border-border flex-1 select-all">
                      {engine.id === 'antigravity'
                        ? 'powershell -c "irm https://antigravity.dev/install.ps1 | iex"'
                        : `npm install -g ${engine.id}`}
                    </code>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() =>
                        copyToClipboard(
                          engine.id === 'antigravity'
                            ? 'powershell -c "irm https://antigravity.dev/install.ps1 | iex"'
                            : `npm install -g ${engine.id}`,
                          `inst_${engine.id}`
                        )
                      }
                    >
                      {copiedCmd === `inst_${engine.id}` ? (
                        <Check className="w-3.5 h-3.5 text-emerald-500" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </Button>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    After running the install command in your terminal, click "Test" on this card to verify.
                  </p>
                </div>
              )}
            </Card>
          )
        })}
      </div>

      {/* Default Engine Row */}
      <div className="rounded-xl border border-border bg-card p-4 flex flex-wrap gap-4 items-center justify-between">
        <div className="space-y-0.5">
          <div className="text-sm font-semibold text-foreground">Default engine</div>
          <div className="text-xs text-muted-foreground">
            Used when a user request or coding prompt does not specify a specific engine.
          </div>
        </div>
        <Select value={defaultEngine} onValueChange={handleSetDefault}>
          <SelectTrigger className="w-[200px] h-8 text-xs font-mono">
            <SelectValue placeholder="Select default" />
          </SelectTrigger>
          <SelectContent>
            {engines
              .filter((e) => enabledEngines[e.id] !== false)
              .map((e) => (
                <SelectItem key={e.id} value={e.id} className="text-xs">
                  {e.label} {e.state !== 'ready' ? `(${e.state.replace('_', ' ')})` : ''}
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
