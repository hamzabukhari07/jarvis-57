import React, { useState, useEffect, useCallback } from 'react'
import QRCode from 'qrcode'
import {
 Dialog,
 DialogContent,
 DialogHeader,
 DialogTitle,
 DialogDescription,
} from '../ui/dialog'
import { Badge } from '../reui/badge'
import { Button } from '../ui/button'
import {
 Copy,
 Check,
 RefreshCw,
 Clock,
 Radio,
 Wifi,
 KeyRound,
 X,
 ExternalLink,
 QrCode,
} from 'lucide-react'

interface MobileRemoteModalProps {
 isOpen: boolean
 onClose: () => void
 remoteGateway: { url: string; key: string; tunnel_status?: string; tunnel_available?: boolean; tunnel_error?: string } | null
 onRequestNewKey?: () => void
}

const REMOTE_KEY_TTL_SECONDS = 600 // 10 minutes

export const MobileRemoteModal: React.FC<MobileRemoteModalProps> = ({
 isOpen,
 onClose,
 remoteGateway,
 onRequestNewKey,
}) => {
 const [localKey, setLocalKey] = useState<string>('')
 const [localUrl, setLocalUrl] = useState<string>('http://localhost:8000')
 const [qrDataUrl, setQrDataUrl] = useState<string | null>(null)
 const [remainingSeconds, setRemainingSeconds] = useState<number>(REMOTE_KEY_TTL_SECONDS)
 const [copiedKey, setCopiedKey] = useState(false)
 const [copiedUrl, setCopiedUrl] = useState(false)
 const [isGenerating, setIsGenerating] = useState(false)
 const [tunnelStatus, setTunnelStatus] = useState<string>('idle')
 const [tunnelError, setTunnelError] = useState<string>('')

 // Generate fallback 6-char key if offline
 const generateFallbackKey = useCallback(() => {
 const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
 let key = ''
 for (let i = 0; i < 6; i++) {
 key += chars.charAt(Math.floor(Math.random() * chars.length))
 }
 return key
 }, [])

 // Sync props from backend
 useEffect(() => {
 if (remoteGateway?.key) {
 setLocalKey(remoteGateway.key)
 } else if (!localKey) {
 setLocalKey(generateFallbackKey())
 }

 if (remoteGateway?.url) {
 setLocalUrl(remoteGateway.url)
 } else if (typeof window !== 'undefined') {
 const hostname = window.location.hostname || 'localhost'
 setLocalUrl(`http://${hostname}:8000`)
 }

 if (remoteGateway?.tunnel_status) setTunnelStatus(remoteGateway.tunnel_status)
 if (remoteGateway?.tunnel_error) setTunnelError(remoteGateway.tunnel_error)
 }, [remoteGateway, generateFallbackKey, localKey])

 // Request fresh key on open
 useEffect(() => {
 if (isOpen && onRequestNewKey) {
 onRequestNewKey()
 }
 }, [isOpen, onRequestNewKey])

 // Poll tunnel status while open; refresh URL/key once tunnel becomes ready
 useEffect(() => {
 if (!isOpen) return
 let cancelled = false
 const poll = async () => {
 try {
 const res = await fetch('/api/remote')
 if (!res.ok || cancelled) return
 const data = await res.json()
 if (cancelled) return
 if (data?.tunnel_status) setTunnelStatus(data.tunnel_status)
 if (data?.tunnel_error) setTunnelError(data.tunnel_error)
 if (data?.url && data.url !== localUrl) setLocalUrl(data.url)
 if (data?.key && data.key !== localKey) setLocalKey(data.key)
 } catch {
 /* ignore */
 }
 }
 poll()
 const interval = setInterval(poll, 2000)
 return () => {
 cancelled = true
 clearInterval(interval)
 }
 }, [isOpen])

 // Generate crisp client-side QR Code whenever URL or key updates
 useEffect(() => {
 if (!localUrl || !localKey) return
 const cleanUrl = localUrl.replace(/\/+$/, '')
 const fullLoginUrl = `${cleanUrl}/auto-login?key=${encodeURIComponent(localKey)}`

 let isSubscribed = true
 QRCode.toDataURL(fullLoginUrl, {
 width: 220,
 margin: 1.5,
 color: {
 dark: '#000000',
 light: '#ffffff',
 },
 errorCorrectionLevel: 'M',
 })
 .then((dataUri) => {
 if (isSubscribed) setQrDataUrl(dataUri)
 })
 .catch((err) => {
 console.warn('[QR] Canvas generation error, using fallback:', err)
 if (isSubscribed) {
 setQrDataUrl(
 `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(fullLoginUrl)}`
 )
 }
 })

 return () => {
 isSubscribed = false
 }
 }, [localUrl, localKey])

 // 10-minute countdown timer
 useEffect(() => {
 if (!isOpen) return
 setRemainingSeconds(REMOTE_KEY_TTL_SECONDS)
 const interval = setInterval(() => {
 setRemainingSeconds((prev) => {
 if (prev <= 1) {
 if (onRequestNewKey) {
 onRequestNewKey()
 } else {
 setLocalKey(generateFallbackKey())
 }
 return REMOTE_KEY_TTL_SECONDS
 }
 return prev - 1
 })
 }, 1000)
 return () => clearInterval(interval)
 }, [isOpen, generateFallbackKey, onRequestNewKey])

 const handleCopyKey = () => {
 if (!localKey) return
 navigator.clipboard.writeText(localKey)
 setCopiedKey(true)
 setTimeout(() => setCopiedKey(false), 2000)
 }

 const handleCopyUrl = () => {
 if (!localUrl) return
 navigator.clipboard.writeText(localUrl)
 setCopiedUrl(true)
 setTimeout(() => setCopiedUrl(false), 2000)
 }

 const handleOpenBrowser = () => {
 if (!localUrl || !localKey) return
 const cleanUrl = localUrl.replace(/\/+$/, '')
 const fullLoginUrl = `${cleanUrl}/auto-login?key=${encodeURIComponent(localKey)}`
 window.open(fullLoginUrl, '_blank')
 }

 const handleRegenerate = () => {
 setIsGenerating(true)
 if (onRequestNewKey) {
 onRequestNewKey()
 } else {
 setLocalKey(generateFallbackKey())
 setRemainingSeconds(REMOTE_KEY_TTL_SECONDS)
 }
 setTimeout(() => setIsGenerating(false), 400)
 }

 const formatTime = (secs: number) => {
 const m = Math.floor(secs / 60)
 const s = secs % 60
 return `${m}:${s.toString().padStart(2, '0')}`
 }

 return (
 <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
 <DialogContent hideCloseButton className="max-w-md w-[92vw] max-h-[92vh] overflow-y-auto border border-border bg-card p-0 ">
 <DialogHeader className="p-4 border-b border-border flex flex-row items-center justify-between sticky top-0 bg-card/95 z-10">
 <div className="flex items-center gap-2">
 <Radio className="w-4 h-4 text-primary animate-pulse" />
 <DialogTitle className="text-sm font-bold text-foreground">Mobile Remote Gateway</DialogTitle>
 </div>
 <Button
 variant="ghost"
 size="sm"
 onClick={onClose}
 className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
 >
 <X className="w-4 h-4" />
 </Button>
 </DialogHeader>

 <DialogDescription className="sr-only">Connect mobile device to ZEZO gateway via QR code</DialogDescription>

 <div className="p-5 space-y-4">
 {/* Centered QR Code Box */}
 <div className="flex flex-col items-center justify-center p-4 rounded-xl border border-border bg-muted/20">
 <div className="bg-white p-2.5 rounded-xl border border-white/20 flex items-center justify-center">
 {qrDataUrl ? (
 <img
 src={qrDataUrl}
 alt="Mobile Remote QR Code"
 className="w-44 h-44 object-contain block rounded-lg select-none"
 />
 ) : (
 <div className="w-44 h-44 flex flex-col items-center justify-center text-muted-foreground gap-2">
 <QrCode className="w-8 h-8 animate-pulse text-muted-foreground/60" />
 <span className="text-[11px] font-mono">Generating QR...</span>
 </div>
 )}
 </div>
 <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
 <QrCode className="w-3.5 h-3.5 text-primary" />
 <span>Scan with phone camera to auto-connect</span>
 </div>
 </div>

 {/* Tunnel status (auto Cloudflare tunnel) */}
 <div className="rounded-xl border border-border bg-muted/20 p-3 text-xs font-mono flex items-center gap-2">
 {tunnelStatus === 'running' ? (
 <span className="text-emerald-400">● Tunnel ready — accessible from anywhere</span>
 ) : tunnelStatus === 'starting' ? (
 <span className="text-amber-400 animate-pulse">● Connecting tunnel to internet…</span>
 ) : tunnelStatus === 'not_installed' ? (
 <span className="text-red-400">● cloudflared not installed — LAN only. Run: winget install Cloudflare.cloudflared</span>
 ) : tunnelStatus === 'error' ? (
 <span className="text-red-400">● Tunnel error: {tunnelError || 'unknown'}</span>
 ) : (
 <span className="text-muted-foreground">● Tunnel idle — LAN only</span>
 )}
 </div>

 {/* Gateway URL Field */}
 <div className="rounded-xl border border-border bg-muted/30 p-3.5 space-y-2.5">
 <div className="flex items-center justify-between text-xs">
 <span className="text-muted-foreground font-mono flex items-center gap-1.5">
 <Wifi className="w-3.5 h-3.5 text-emerald-400" />
 <span>Gateway URL</span>
 </span>
 <div className="flex items-center gap-1">
 <Button
 variant="ghost"
 size="sm"
 onClick={handleOpenBrowser}
 title="Open in new browser tab"
 className="h-6 px-2 text-[10px] font-mono gap-1 text-muted-foreground hover:text-foreground"
 >
 <ExternalLink className="w-3 h-3" />
 <span>Open</span>
 </Button>
 <Button
 variant="ghost"
 size="sm"
 onClick={handleCopyUrl}
 className="h-6 px-2 text-[10px] font-mono gap-1"
 >
 {copiedUrl ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
 <span>{copiedUrl ? 'Copied' : 'Copy'}</span>
 </Button>
 </div>
 </div>
 <div className="font-mono text-xs text-foreground bg-input/40 p-2.5 rounded-lg border border-border truncate select-all">
 {localUrl || 'http://192.168.100.56:8000'}
 </div>
 </div>

 {/* Pairing Secret Key Field */}
 <div className="rounded-xl border border-border bg-muted/30 p-3.5 space-y-2.5">
 <div className="flex items-center justify-between text-xs">
 <span className="text-muted-foreground font-mono flex items-center gap-1.5">
 <KeyRound className="w-3.5 h-3.5 text-primary" />
 <span>Pairing Secret Key</span>
 </span>
 <div className="flex items-center gap-2">
 <Badge variant="outline" className="font-mono text-[10px] text-muted-foreground gap-1">
 <Clock className="w-3 h-3 text-primary" />
 <span>{formatTime(remainingSeconds)}</span>
 </Badge>
 <Button
 variant="ghost"
 size="sm"
 onClick={handleCopyKey}
 className="h-6 px-2 text-[10px] font-mono gap-1"
 >
 {copiedKey ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
 <span>{copiedKey ? 'Copied' : 'Copy'}</span>
 </Button>
 </div>
 </div>
 <div className="font-mono text-xl font-bold tracking-[0.25em] text-primary text-center bg-input/40 p-3 rounded-lg border border-border select-all">
 {localKey || '——'}
 </div>
 </div>

 {/* Footer Controls */}
 <div className="flex items-center justify-between pt-1">
 <span className="text-[11px] text-muted-foreground">Open gateway on your phone to connect</span>
 <Button
 variant="outline"
 size="sm"
 onClick={handleRegenerate}
 disabled={isGenerating}
 className="h-7 text-xs font-mono gap-1.5"
 >
 <RefreshCw className={`w-3 h-3 ${isGenerating ? 'animate-spin' : ''}`} />
 <span>New Key</span>
 </Button>
 </div>
 </div>
 </DialogContent>
 </Dialog>
 )
}