import React, { useMemo, useState, useEffect } from 'react'
import { QiviAvatar, CHARACTERS } from 'qivi-react'
import type { QiviState, QiviExpression, QiviPersonality, QiviShape, QiviThemeName } from 'qivi-react'
import 'qivi-react/styles.css'
import { api } from '../../lib/api'

export interface QiviAvatarVisualizerProps {
  systemState?: 'idle' | 'listening' | 'speaking' | 'thinking' | 'sleeping'
  audioLevel?: number
  isSleeping?: boolean
  isMicMuted?: boolean
  className?: string
  size?: number
  characterPreset?: string
  shape?: QiviShape
  themeName?: string
  quality?: 'auto' | 'high' | 'medium' | 'low' | 'static'
  lighting?: number
  interactive?: boolean
}

export const QiviAvatarVisualizer: React.FC<QiviAvatarVisualizerProps> = React.memo(({
  systemState = 'idle',
  audioLevel = 0,
  isSleeping = false,
  isMicMuted = false,
  className = '',
  size = 220,
  characterPreset: propPreset,
  shape: propShape,
  themeName: propThemeName,
  quality: propQuality,
  lighting: propLighting,
  interactive = true,
}) => {
  // Local storage state with reactive event fallback
  const [localPreset, setLocalPreset] = useState<string>(() => localStorage.getItem('zezo_avatar_preset') || 'qivi')
  const [localShape, setLocalShape] = useState<QiviShape>(() => (localStorage.getItem('zezo_avatar_shape') as QiviShape) || 'blob')
  const [localTheme, setLocalTheme] = useState<string>(() => localStorage.getItem('zezo_avatar_theme') || 'match_theme')
  const [localQuality, setLocalQuality] = useState<'auto' | 'high' | 'medium' | 'low' | 'static'>(
    () => (localStorage.getItem('zezo_avatar_quality') as any) || 'high'
  )
  const [localLighting, setLocalLighting] = useState<number>(() => {
    const val = localStorage.getItem('zezo_avatar_lighting')
    return val ? parseFloat(val) : 0.85
  })

  useEffect(() => {
    const handleSettingsChanged = (e: Event) => {
      const customEvent = e as CustomEvent
      if (customEvent.detail) {
        if (customEvent.detail.preset) setLocalPreset(customEvent.detail.preset)
        if (customEvent.detail.shape) setLocalShape(customEvent.detail.shape)
        if (customEvent.detail.theme) setLocalTheme(customEvent.detail.theme)
        if (customEvent.detail.quality) setLocalQuality(customEvent.detail.quality)
        if (customEvent.detail.lighting !== undefined) setLocalLighting(customEvent.detail.lighting)
      } else {
        setLocalPreset(localStorage.getItem('zezo_avatar_preset') || 'qivi')
        setLocalShape((localStorage.getItem('zezo_avatar_shape') as QiviShape) || 'blob')
        setLocalTheme(localStorage.getItem('zezo_avatar_theme') || 'match_theme')
        setLocalQuality((localStorage.getItem('zezo_avatar_quality') as any) || 'high')
        const val = localStorage.getItem('zezo_avatar_lighting')
        if (val) setLocalLighting(parseFloat(val))
      }
    }

    window.addEventListener('zezo_avatar_settings_changed', handleSettingsChanged)

    // Hydrate avatar settings directly from persistent backend configuration
    api.getConfig().then((cfg) => {
      if (cfg) {
        if (cfg.avatar_preset) setLocalPreset(cfg.avatar_preset)
        if (cfg.avatar_shape) setLocalShape(cfg.avatar_shape)
        if (cfg.avatar_theme) setLocalTheme(cfg.avatar_theme)
        if (cfg.avatar_quality) setLocalQuality(cfg.avatar_quality)
        if (cfg.avatar_lighting !== undefined) {
          const lgt = parseFloat(cfg.avatar_lighting) || 0.85
          setLocalLighting(lgt)
        }
      }
    }).catch(() => {})

    return () => {
      window.removeEventListener('zezo_avatar_settings_changed', handleSettingsChanged)
    }
  }, [])

  const activePreset = propPreset || localPreset
  const activeShape = propShape || localShape
  const activeThemeName = propThemeName || localTheme
  const activeQuality = propQuality || localQuality
  const activeLighting = propLighting !== undefined ? propLighting : localLighting

  const { state, expression, personality, intensity } = useMemo(() => {
    if (isSleeping || systemState === 'sleeping') {
      return {
        state: 'idle' as QiviState,
        expression: 'sleepy' as QiviExpression,
        personality: 'core' as QiviPersonality,
        intensity: 0.2,
      }
    }

    if (isMicMuted) {
      return {
        state: 'idle' as QiviState,
        expression: 'neutral' as QiviExpression,
        personality: 'guardian' as QiviPersonality,
        intensity: 0.4,
      }
    }

    // Apply noise gate to audioLevel to prevent micro-fluctuations from redrawing WebGL mesh
    const gatedAudio = audioLevel < 0.08 ? 0 : Math.round(audioLevel * 10) / 10

    switch (systemState) {
      case 'speaking':
        return {
          state: 'talking' as QiviState,
          expression: 'happy' as QiviExpression,
          personality: 'spark' as QiviPersonality,
          intensity: Math.min(1.0, 0.75 + (gatedAudio > 0 ? gatedAudio : 0.4) * 1.2),
        }
      case 'thinking':
        return {
          state: 'thinking' as QiviState,
          expression: 'thinking' as QiviExpression,
          personality: 'analyst' as QiviPersonality,
          intensity: 0.85,
        }
      case 'listening':
        return {
          state: 'listening' as QiviState,
          expression: 'curious' as QiviExpression,
          personality: 'core' as QiviPersonality,
          intensity: Math.min(1.0, 0.6 + (gatedAudio > 0 ? gatedAudio : 0.3) * 1.5),
        }
      case 'idle':
      default:
        return {
          state: 'idle' as QiviState,
          expression: 'neutral' as QiviExpression,
          personality: 'core' as QiviPersonality,
          intensity: 0.5,
        }
    }
  }, [systemState, isSleeping, isMicMuted, audioLevel < 0.08 ? 0 : Math.round(audioLevel * 10) / 10])

  const resolvedVoice = useMemo(() => {
    if (isSleeping || systemState === 'sleeping' || isMicMuted) return null
    if (systemState === 'speaking') return 'simulate' as const
    if (systemState === 'listening' && audioLevel > 0.08) return 'simulate' as const
    return null
  }, [systemState, isSleeping, isMicMuted, audioLevel > 0.08])

  const resolvedTheme = useMemo(() => {
    if (!activeThemeName || activeThemeName === 'default') {
      return 'default' as QiviThemeName
    }
    if (activeThemeName === 'match_theme') {
      const osTheme = localStorage.getItem('zezo_theme') || 'copper'
      if (osTheme.includes('emerald') || osTheme.includes('mint')) return 'mint' as QiviThemeName
      if (osTheme.includes('arctic') || osTheme.includes('teal')) return 'arctic' as QiviThemeName
      if (osTheme.includes('indigo') || osTheme.includes('violet')) return 'lavender' as QiviThemeName
      if (osTheme.includes('copper')) return 'amber' as QiviThemeName
      return 'default' as QiviThemeName
    }
    return activeThemeName as QiviThemeName
  }, [activeThemeName])

  const characterConfig = useMemo(() => {
    const base = (activePreset && activePreset !== 'custom' && (CHARACTERS as any)[activePreset])
      ? (CHARACTERS as any)[activePreset]
      : (CHARACTERS as any).qivi

    return {
      ...base,
      behavior: {
        ...base?.behavior,
        probe: 0, // Disable idle probe pseudopod to prevent deformed double-blob glitch
      },
    }
  }, [activePreset])

  return (
    <div className={`relative flex items-center justify-center w-full h-full ${className}`}>
      <QiviAvatar
        size={size}
        state={state}
        expression={expression}
        personality={characterConfig?.personality || personality}
        character={characterConfig}
        shape={activeShape}
        theme={resolvedTheme}
        voice={resolvedVoice}
        smile={systemState === 'speaking' || expression === 'happy'}
        glyphs={true}
        accent={systemState === 'speaking' || systemState === 'thinking' ? 'always' : 'auto'}
        appearance="dark"
        lighting={activeLighting}
        intensity={intensity}
        quality={activeQuality}
        interactive={interactive}
      />
    </div>
  )
})

QiviAvatarVisualizer.displayName = 'QiviAvatarVisualizer'
