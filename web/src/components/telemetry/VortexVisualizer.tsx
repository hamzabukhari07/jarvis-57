import React, { useMemo } from 'react'

interface VortexVisualizerProps {
  systemState: string
  audioLevel: number
  micEnergy?: number
}

export const VortexVisualizer: React.FC<VortexVisualizerProps> = ({
  systemState,
  audioLevel,
  micEnergy = 0,
}) => {
  const energy = Math.max(audioLevel, micEnergy)

  // Color schemes according to state
  const colorConfig = useMemo(() => {
    switch (systemState.toLowerCase()) {
      case 'listening':
        return {
          glow: 'rgba(16, 185, 129, 0.4)',
          core: 'from-emerald-400 to-teal-500',
          ring: 'border-emerald-500/40',
          particle: 'bg-emerald-400',
        }
      case 'thinking':
        return {
          glow: 'rgba(226, 216, 202, 0.35)',
          core: 'from-[#e4e0d8] to-[#9a948a]',
          ring: 'border-[#e4e0d8]/30',
          particle: 'bg-[#e4e0d8]',
        }
      case 'speaking':
        return {
          glow: 'rgba(226, 216, 202, 0.45)',
          core: 'from-[#e2d8ca] to-[#d8d2c8]',
          ring: 'border-[#e2d8ca]/40',
          particle: 'bg-[#e2d8ca]',
        }
      default:
        return {
          glow: 'rgba(113, 113, 122, 0.2)',
          core: 'from-zinc-500 to-zinc-700',
          ring: 'border-zinc-700/30',
          particle: 'bg-zinc-500',
        }
    }
  }, [systemState])

  const scale = 1 + energy * 0.45
  const rotationDuration = systemState === 'thinking' ? '3s' : '10s'

  return (
    <div className="relative flex items-center justify-center w-52 h-52 select-none">
      {/* Outer Glow Halo */}
      <div
        className="absolute inset-0 rounded-full blur-2xl transition-all duration-300"
        style={{
          backgroundColor: colorConfig.glow,
          transform: `scale(${scale * 1.1})`,
          opacity: 0.6 + energy * 0.4,
        }}
      />

      {/* Orbit Ring 1 */}
      <div
        className={`absolute inset-4 rounded-full border border-dashed ${colorConfig.ring} animate-spin`}
        style={{
          animationDuration: rotationDuration,
          transform: `scale(${scale})`,
        }}
      />

      {/* Orbit Ring 2 (Counter-Rotating) */}
      <div
        className={`absolute inset-8 rounded-full border border-dotted ${colorConfig.ring} animate-[spin_8s_linear_infinite_reverse]`}
        style={{
          transform: `scale(${scale * 0.9})`,
        }}
      />

      {/* Center Core Orb */}
      <div
        className={`w-20 h-20 rounded-full bg-gradient-to-tr ${colorConfig.core} shadow-2xl flex items-center justify-center transition-transform duration-100 ease-out`}
        style={{
          transform: `scale(${scale})`,
          boxShadow: `0 0 35px ${colorConfig.glow}`,
        }}
      >
        {/* Inner Radial Shimmer */}
        <div className="w-14 h-14 rounded-full bg-white/20 backdrop-blur-xs flex items-center justify-center">
          <div className="w-7 h-7 rounded-full bg-white/40 shadow-inner" />
        </div>
      </div>

      {/* Waveform Bar Halo on Speaking or Listening */}
      {energy > 0.04 && (
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
          {Array.from({ length: 12 }).map((_, i) => {
            const rot = i * 30
            const height = 10 + (energy * 35 * ((i % 3) + 1)) / 2
            return (
              <div
                key={i}
                className="absolute w-1 rounded-full bg-[#e2d8ca]/80 transition-all duration-75"
                style={{
                  height: `${height}px`,
                  transform: `rotate(${rot}deg) translateY(-60px)`,
                }}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}

