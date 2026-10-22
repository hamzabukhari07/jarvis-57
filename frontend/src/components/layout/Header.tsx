import React from 'react'
import { 
 Bot, 
 Cpu, 
 Activity, 
 Settings, 
 Mic, 
 MicOff, 
 Radio, 
 Layers, 
 Workflow, 
 Sparkles 
} from 'lucide-react'
import type { ZezoTelemetry } from '../../types/zezo'

interface HeaderProps {
 activeView: 'office' | 'canvas' | 'chat'
 onViewChange: (view: 'office' | 'canvas' | 'chat') => void
 telemetry: ZezoTelemetry | null
 systemState: string
 audioLevel: number
 isLiveMicActive: boolean
 onToggleMic: () => void
 onOpenSettings: () => void
}

export const Header: React.FC<HeaderProps> = ({
 activeView,
 onViewChange,
 telemetry,
 systemState,
 audioLevel,
 isLiveMicActive,
 onToggleMic,
 onOpenSettings,
}) => {
 const getStatusColor = () => {
 switch (systemState.toLowerCase()) {
 case 'listening':
 return 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.6)]'
 case 'thinking':
 return 'bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.6)] animate-pulse'
 case 'speaking':
 return 'bg-blue-500 shadow-[0_0_12px_rgba(59,130,246,0.6)]'
 case 'error':
 return 'bg-red-500 shadow-[0_0_12px_rgba(239,68,68,0.6)]'
 default:
 return 'bg-zinc-400'
 }
 }

 return (
 <header className="h-14 border-b border-white/10 bg-[#121110]/90 backdrop-blur-md px-4 flex items-center justify-between z-40 select-none">
 {/* Brand & State Indicator */}
 <div className="flex items-center gap-3">
 <div className="flex items-center gap-2">
 <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-[#e4e0d8] to-[#9a948a] flex items-center justify-center /5">
 <Sparkles className="w-4.5 h-4.5 text-[#121110]" />
 </div>
 <div>
 <div className="flex items-center gap-1.5 leading-none">
 <span className="font-bold text-sm tracking-wide text-[#e4e0d8]">ZEZO</span>
 <span className="text-[10px] uppercase font-semibold text-[#e2d8ca] bg-white/5 px-1.5 py-0.5 rounded border border-white/10">v2.4</span>
 </div>
 <div className="text-[10px] text-[#9a948a] leading-tight">Forma OS Architecture</div>
 </div>
 </div>

 <div className="h-4 w-px bg-white/10 mx-1" />

 {/* System State Pill */}
 <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#1a1918]/90 border border-white/10 text-xs text-[#e4e0d8]">
 <span className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
 <span className="font-mono text-[11px] uppercase tracking-wider text-[#e4e0d8] font-medium">{systemState}</span>
 {audioLevel > 0.05 && (
 <div className="flex items-center gap-0.5 ml-1">
 <span 
 className="w-1 bg-[#e2d8ca] rounded-full transition-all duration-75" 
 style={{ height: `${Math.min(16, Math.max(4, audioLevel * 20))}px` }} 
 />
 <span 
 className="w-1 bg-[#d8d2c8] rounded-full transition-all duration-75" 
 style={{ height: `${Math.min(14, Math.max(3, audioLevel * 16))}px` }} 
 />
 </div>
 )}
 </div>
 </div>

 {/* View Switcher Navigation */}
 <nav className="flex items-center p-1 bg-[#1a1918]/80 border border-white/10 rounded-lg">
 <button
 onClick={() => onViewChange('office')}
 className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
 activeView === 'office'
 ? 'bg-white/10 text-[#e4e0d8] border border-white/15'
 : 'text-[#9a948a] hover:text-[#e4e0d8]'
 }`}
 >
 <Layers className="w-3.5 h-3.5 text-[#e2d8ca]" />
 <span>Office View</span>
 </button>
 <button
 onClick={() => onViewChange('canvas')}
 className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
 activeView === 'canvas'
 ? 'bg-white/10 text-[#e4e0d8] border border-white/15'
 : 'text-[#9a948a] hover:text-[#e4e0d8]'
 }`}
 >
 <Workflow className="w-3.5 h-3.5 text-[#d1ccc3]" />
 <span>Flow Canvas</span>
 </button>
 <button
 onClick={() => onViewChange('chat')}
 className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
 activeView === 'chat'
 ? 'bg-white/10 text-[#e4e0d8] border border-white/15'
 : 'text-[#9a948a] hover:text-[#e4e0d8]'
 }`}
 >
 <Bot className="w-3.5 h-3.5 text-[#e4e0d8]" />
 <span>Chat Stream</span>
 </button>
 </nav>

 {/* Telemetry & Quick Action Controls */}
 <div className="flex items-center gap-3">
 {telemetry && (
 <div className="hidden lg:flex items-center gap-3 text-[11px] font-mono text-[#9a948a] bg-[#1a1918]/80 px-2.5 py-1 rounded-md border border-white/10">
 <div className="flex items-center gap-1">
 <Cpu className="w-3 h-3 text-zinc-400" />
 <span>{Math.round(telemetry.cpu_percent)}%</span>
 </div>
 <div className="flex items-center gap-1">
 <Activity className="w-3 h-3 text-zinc-400" />
 <span>{Math.round(telemetry.ram_percent)}%</span>
 </div>
 {telemetry.gpu_percent !== undefined && (
 <div className="flex items-center gap-1">
 <Radio className="w-3 h-3 text-zinc-400" />
 <span>GPU {Math.round(telemetry.gpu_percent)}%</span>
 </div>
 )}
 </div>
 )}

 {/* Live Mic Toggle */}
 <button
 onClick={onToggleMic}
 className={`p-2 rounded-lg border transition-all ${
 isLiveMicActive
 ? 'bg-red-500/10 border-red-500/40 text-red-400 shadow-[0_0_12px_rgba(239,68,68,0.2)]'
 : 'bg-zinc-900 border-zinc-800 text-zinc-300 hover:border-zinc-700 hover:text-zinc-100'
 }`}
 title={isLiveMicActive ? 'Mute Live Voice Loop' : 'Activate Live Voice Loop'}
 >
 {isLiveMicActive ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4 text-zinc-400" />}
 </button>

 {/* Settings Dialog Trigger */}
 <button
 onClick={onOpenSettings}
 className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300 hover:border-zinc-700 hover:text-zinc-100 transition-all"
 title="Open System & Pipeline Settings"
 >
 <Settings className="w-4 h-4" />
 </button>
 </div>
 </header>
 )
}
