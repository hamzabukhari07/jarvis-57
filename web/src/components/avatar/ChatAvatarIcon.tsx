import React, { useState, useEffect, useMemo } from 'react'
import { QiviIcon, CHARACTERS } from 'qivi-react'
import type { QiviPersonality, QiviThemeName, QiviExpression, QiviState } from 'qivi-react'

export interface ChatAvatarIconProps {
  size?: number
  className?: string
  expression?: QiviExpression
  state?: QiviState
}

const PRESET_PERSONALITY_MAP: Record<string, QiviPersonality> = {
  qivi: 'core',
  female: 'spark',
  male: 'diplomat',
  ember: 'chaos',
  sage: 'sage',
  atlas: 'guardian',
}

export const ChatAvatarIcon: React.FC<ChatAvatarIconProps> = ({
  size = 26,
  className = '',
  expression = 'happy',
  state = 'idle',
}) => {
  const [preset, setPreset] = useState<string>(() => localStorage.getItem('zezo_avatar_preset') || 'qivi')
  const [theme, setTheme] = useState<string>(() => localStorage.getItem('zezo_avatar_theme') || 'match_theme')

  useEffect(() => {
    const handleAvatarSettings = (e: Event) => {
      const customEvent = e as CustomEvent
      if (customEvent.detail) {
        if (customEvent.detail.preset) setPreset(customEvent.detail.preset)
        if (customEvent.detail.theme) setTheme(customEvent.detail.theme)
      } else {
        setPreset(localStorage.getItem('zezo_avatar_preset') || 'qivi')
        setTheme(localStorage.getItem('zezo_avatar_theme') || 'match_theme')
      }
    }

    const handleThemeChanged = () => {
      setTheme(localStorage.getItem('zezo_avatar_theme') || 'match_theme')
    }

    window.addEventListener('zezo_avatar_settings_changed', handleAvatarSettings)
    window.addEventListener('zezo_theme_changed', handleThemeChanged)
    return () => {
      window.removeEventListener('zezo_avatar_settings_changed', handleAvatarSettings)
      window.removeEventListener('zezo_theme_changed', handleThemeChanged)
    }
  }, [])

  const resolvedTheme = useMemo<QiviThemeName>(() => {
    if (!theme || theme === 'default') return 'default' as QiviThemeName
    if (theme === 'match_theme') {
      const osTheme = localStorage.getItem('zezo_theme') || 'copper'
      if (osTheme.includes('emerald') || osTheme.includes('mint')) return 'mint' as QiviThemeName
      if (osTheme.includes('arctic') || osTheme.includes('teal')) return 'arctic' as QiviThemeName
      if (osTheme.includes('indigo') || osTheme.includes('violet') || osTheme.includes('purple')) return 'lavender' as QiviThemeName
      if (osTheme.includes('copper')) return 'amber' as QiviThemeName
      return 'default' as QiviThemeName
    }
    return theme as QiviThemeName
  }, [theme])

  const characterConfig = useMemo(() => {
    if (preset && preset !== 'custom' && (CHARACTERS as any)[preset]) {
      return (CHARACTERS as any)[preset]
    }
    return undefined
  }, [preset])

  const personality = characterConfig?.personality || PRESET_PERSONALITY_MAP[preset] || 'core'

  return (
    <QiviIcon
      size={size}
      personality={personality}
      character={characterConfig}
      theme={resolvedTheme}
      expression={expression}
      state={state}
      className={className}
    />
  )
}
