import { useEffect, useRef, useState, useCallback } from 'react'

export interface SocketMessage {
  type: string
  [key: string]: any
}

export interface LogEntry {
  id: string
  time: string
  source: string
  text: string
  type: string
  level?: string
}

export interface AudioDeviceState {
  inputs: Array<{ name: string; index?: number; is_default?: boolean }>
  outputs: Array<{ name: string; index?: number; is_default?: boolean }>
  current_input?: string
  current_output?: string
  echo_filter_active?: boolean
}

export interface TranscriptStreamEvent {
  speaker: string
  text: string
  done?: boolean
  id?: string
}

export interface CanvasDisplayEvent {
  title: string
  text: string
}

export interface LiveTelemetry {
  cpu: number
  mem: number
  gpu: number
  net: number
  tmp?: number
}

export interface ConfirmationEvent {
  active: boolean
  key: string
  title: string
  detail: string
  variant?: 'destructive' | 'warning' | 'default'
}

export function useZezoSocket() {
  const [isConnected, setIsConnected] = useState(false)
  const [systemState, setSystemState] = useState<'idle' | 'listening' | 'speaking' | 'thinking' | 'sleeping'>('listening')
  const [audioLevel, setAudioLevel] = useState(0)
  const [micLevel, setMicLevel] = useState(0)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [logStats, setLogStats] = useState<{ total_lines?: number; max_lines?: number }>({ total_lines: 0, max_lines: 20000 })
  const [logSources, setLogSources] = useState<string[]>([])
  const [audioDevices, setAudioDevices] = useState<AudioDeviceState>({ inputs: [], outputs: [] })
  const [remoteGateway, setRemoteGateway] = useState<{ url: string; key: string } | null>(null)
  const [lastMessage, setLastMessage] = useState<SocketMessage | null>(null)

  // Real backend live execution and speech stream state
  const [transcriptStream, setTranscriptStream] = useState<TranscriptStreamEvent | null>(null)
  const [canvasContent, setCanvasContent] = useState<CanvasDisplayEvent | null>(null)
  const [telemetry, setTelemetry] = useState<LiveTelemetry>({ cpu: 0, mem: 0, gpu: 0, net: 0, tmp: -1 })
  const [tasks, setTasks] = useState<any[]>([])
  const [activeAttachments, setActiveAttachments] = useState<any[]>([])
  const [currentView, setCurrentView] = useState<'home' | 'office' | null>(null)
  const [confirmationState, setConfirmationState] = useState<ConfirmationEvent>({
    active: false,
    key: '',
    title: '',
    detail: '',
    variant: 'default',
  })

  const wsRef = useRef<WebSocket | null>(null)
  const lastAudioLevelRef = useRef<number>(0)
  const lastMicLevelRef = useRef<number>(0)

  const send = useCallback((msg: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host || '127.0.0.1:8765'
    const wsUrl = `${protocol}//${host}/ws`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        console.log('[ZezoWS] Connected to ZEZO daemon:', wsUrl)
        // Request initial state and log snapshot
        ws.send(JSON.stringify({ type: 'get_backend_logs' }))
        ws.send(JSON.stringify({ type: 'get_audio_devices' }))
        ws.send(JSON.stringify({ type: 'get_remote_key' }))
      }

      ws.onclose = () => {
        setIsConnected(false)
        console.warn('[ZezoWS] Disconnected, reconnecting in 2.5s...')
        setTimeout(connect, 2500)
      }

      ws.onerror = (err) => {
        console.error('[ZezoWS] WebSocket Error:', err)
        ws.close()
      }

      ws.onmessage = (event) => {
        try {
          const raw: SocketMessage = JSON.parse(event.data)
          setLastMessage(raw)
          const msgType = raw.type || ''
          const d: Record<string, any> =
            raw.data && typeof raw.data === 'object' && !Array.isArray(raw.data)
              ? { ...raw, ...raw.data }
              : raw

          switch (msgType) {
            case 'init': {
              const initData = (raw.data && typeof raw.data === 'object') ? raw.data : raw
              if (initData.state) {
                const s = String(initData.state).toLowerCase()
                if (s === 'speaking' || s === 'listening' || s === 'thinking' || s === 'sleeping') {
                  setSystemState(s as any)
                } else {
                  setSystemState('idle')
                }
              }
              if (initData.tasks && Array.isArray(initData.tasks)) setTasks(initData.tasks)
              if (initData.inputs || initData.outputs || initData.input_devices || initData.output_devices) {
                const rawIn = initData.inputs || initData.input_devices || []
                const rawOut = initData.outputs || initData.output_devices || []
                setAudioDevices({
                  inputs: rawIn.map((x: any) => typeof x === 'string' ? { name: x } : x),
                  outputs: rawOut.map((x: any) => typeof x === 'string' ? { name: x } : x),
                  current_input: initData.current_input || initData.input_device || '',
                  current_output: initData.current_output || initData.output_device || '',
                  echo_filter_active: true,
                })
              }
              break
            }

            case 'state_change':
              if (d.state) {
                const s = String(d.state).toLowerCase()
                if (s === 'speaking' || s === 'listening' || s === 'thinking' || s === 'sleeping') {
                  setSystemState(s as any)
                } else {
                  setSystemState('idle')
                }
              }
              break

            case 'transcript_stream':
              if (d.text !== undefined) {
                setTranscriptStream({
                  speaker: String(d.speaker || 'zezo').toLowerCase(),
                  text: String(d.text || ''),
                  done: Boolean(d.done),
                  id: Math.random().toString(36).slice(2, 9),
                })
              }
              break

            case 'content_display':
              if (d.text !== undefined) {
                setCanvasContent({
                  title: String(d.title || 'OUTPUT'),
                  text: String(d.text || ''),
                })
              }
              break

            case 'telemetry_update':
              if (d.cpu !== undefined || d.mem !== undefined) {
                setTelemetry({
                  cpu: Number(d.cpu) || 0,
                  mem: Number(d.mem) || 0,
                  gpu: Number(d.gpu) || 0,
                  net: Number(d.net) || 0,
                  tmp: Number(d.tmp) || -1,
                })
              }
              break

            case 'task_list':
              if (d.tasks) {
                setTasks(Array.isArray(d.tasks) ? d.tasks : [])
              }
              break

            case 'file_ingested':
              if (d.data || d.name) {
                const item = d.data || d
                setActiveAttachments((prev) => {
                  const filtered = prev.filter((p) => p.path !== item.path)
                  return [item, ...filtered]
                })
              }
              break

            case 'confirm_request':
              setConfirmationState({
                active: true,
                key: String(d.key || ''),
                title: String(d.title || 'Confirmation Required'),
                detail: String(d.detail || ''),
                variant: (d.variant || 'default') as any,
              })
              break

            case 'confirm_hide':
            case 'confirmation_closed':
              setConfirmationState((prev) => ({ ...prev, active: false }))
              break

            case 'switch_view':
              if (d.view) {
                setCurrentView(d.view === 'office' ? 'office' : 'home')
              }
              break

            case 'audio_level':
            case 'output_level': {
              const val = Number(d.level ?? d.value ?? 0)
              const clamped = val < 0.05 ? 0 : Math.round(val * 20) / 20
              if (Math.abs(clamped - lastAudioLevelRef.current) >= 0.05 || (clamped === 0 && lastAudioLevelRef.current !== 0)) {
                lastAudioLevelRef.current = clamped
                setAudioLevel(clamped)
              }
              break
            }

            case 'mic_level':
            case 'mic_energy':
            case 'input_level': {
              const val = Number(d.energy ?? d.level ?? d.value ?? 0)
              const clamped = val < 0.05 ? 0 : Math.round(val * 20) / 20
              if (Math.abs(clamped - lastMicLevelRef.current) >= 0.05 || (clamped === 0 && lastMicLevelRef.current !== 0)) {
                lastMicLevelRef.current = clamped
                setMicLevel(clamped)
              }
              break
            }

            case 'backend_logs': {
              const rawLines: any[] = d.lines || []
              if (rawLines.length > 0) {
                const formatted: LogEntry[] = rawLines.map((line: any, idx: number) => {
                  if (typeof line === 'string') {
                    return {
                      id: `bus-${Date.now()}-${idx}`,
                      time: new Date().toLocaleTimeString(),
                      source: 'SYS',
                      text: line,
                      type: line.includes('ERROR') ? 'ERROR' : line.includes('WARN') ? 'WARNING' : 'INFO',
                      level: line.includes('ERROR') ? 'ERROR' : line.includes('WARN') ? 'WARNING' : 'INFO',
                    }
                  }
                  const rawLevel = (line.level || line.type || 'INFO').toUpperCase()
                  return {
                    id: line.id || (line.seq !== undefined ? `bus-${line.seq}` : `bus-${Date.now()}-${idx}`),
                    time: line.time || line.timestamp || line.ts || new Date().toLocaleTimeString(),
                    source: (line.source || line.logger || line.src || 'SYS').toUpperCase(),
                    text: line.text || line.message || line.msg || '',
                    type: rawLevel,
                    level: rawLevel,
                  }
                })
                setLogs((prev) => [...prev.slice(-2500), ...formatted])
                if (d.stats) setLogStats(d.stats)
                if (d.sources) setLogSources(d.sources)
              }
              break
            }

            case 'backend_logs_snapshot': {
              const snapshotData = d.data || d
              const rawLines: any[] = snapshotData.lines || []
              const formatted: LogEntry[] = rawLines.map((line: any, idx: number) => {
                if (typeof line === 'string') {
                  return {
                    id: `snap-${idx}-${Math.random().toString(36).slice(2, 6)}`,
                    time: new Date().toLocaleTimeString(),
                    source: 'SYS',
                    text: line,
                    type: line.includes('ERROR') ? 'ERROR' : line.includes('WARN') ? 'WARNING' : 'INFO',
                    level: line.includes('ERROR') ? 'ERROR' : line.includes('WARN') ? 'WARNING' : 'INFO',
                  }
                }
                const rawLevel = (line.level || line.type || 'INFO').toUpperCase()
                return {
                  id: line.id || (line.seq !== undefined ? `snap-${line.seq}` : `snap-${idx}`),
                  time: line.time || line.timestamp || line.ts || new Date().toLocaleTimeString(),
                  source: (line.source || line.logger || line.src || 'SYS').toUpperCase(),
                  text: line.text || line.message || line.msg || '',
                  type: rawLevel,
                  level: rawLevel,
                }
              })
              setLogs(formatted)
              if (snapshotData.stats) setLogStats(snapshotData.stats)
              if (snapshotData.sources) setLogSources(snapshotData.sources)
              break
            }

            case 'backend_logs_cleared':
              setLogs([])
              setLogStats({ total_lines: 0, max_lines: 20000 })
              break

            case 'log_bus_event':
            case 'log': {
              const now = new Date()
              const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
              const level = (d.level || d.type || 'INFO').toUpperCase()
              const source = (d.source || d.src || d.agent || 'SYSTEM').toUpperCase()

              const newEntry: LogEntry = {
                id: d.id || Math.random().toString(36).substring(2, 9),
                time: d.time || d.ts || timeStr,
                source,
                text: d.text || d.message || d.msg || '',
                type: level,
                level,
              }

              setLogs((prev) => [...prev.slice(-2500), newEntry])
              setLogStats((prev) => ({
                ...prev,
                total_lines: (prev.total_lines || 0) + 1,
              }))
              setLogSources((prev) => (prev.includes(source) ? prev : [...prev, source]))
              break
            }

            case 'speaker_status':
              break

            case 'audio_devices_updated': {
              const audioPayload = d.data || d
              const rawIn = audioPayload.inputs || audioPayload.input_devices || []
              const rawOut = audioPayload.outputs || audioPayload.output_devices || []
              setAudioDevices({
                inputs: rawIn.map((x: any) => typeof x === 'string' ? { name: x } : x),
                outputs: rawOut.map((x: any) => typeof x === 'string' ? { name: x } : x),
                current_input: audioPayload.current_input || audioPayload.input_device || '',
                current_output: audioPayload.current_output || audioPayload.output_device || '',
                echo_filter_active: true,
              })
              break
            }

            case 'remote_key_data':
              if (d.data || d.url) {
                setRemoteGateway(d.data || d)
              }
              break

            case 'fleet_updated':
            case 'agent_task_started':
            case 'agent_task_completed':
              window.dispatchEvent(new CustomEvent('zezo_fleet_updated', { detail: d }))
              break

            case 'teardown_progress':
            case 'teardown_groq_ready':
            case 'teardown_cli_progress':
            case 'teardown_completed':
              window.dispatchEvent(new CustomEvent(`zezo_${msgType}`, { detail: d }))
              break
          }
        } catch (e) {
          console.warn('[ZezoWS] Parse error:', e)
        }
      }
    } catch (err) {
      console.error('[ZezoWS] Connection failed:', err)
      setTimeout(connect, 3000)
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  const clearLogs = useCallback(() => {
    send({ type: 'clear_backend_logs' })
    setLogs([])
  }, [send])

  const cancelTask = useCallback((taskId: string) => {
    send({ type: 'task_cancel', task_id: taskId })
  }, [send])

  const saveAudioDevices = useCallback((inputDevice: string, outputDevice: string) => {
    send({
      type: 'save_audio_devices',
      input_device: inputDevice,
      output_device: outputDevice,
    })
  }, [send])

  const requestRemoteKey = useCallback(() => {
    send({ type: 'get_remote_key' })
  }, [send])

  const sendUserMessage = useCallback((text: string) => {
    send({ type: 'user_message', text: text.trim() })
  }, [send])

  const sendInterrupt = useCallback(() => {
    send({ type: 'interrupt' })
  }, [send])

  const sendMuteToggle = useCallback((muted: boolean) => {
    send({ type: 'mute_toggle', muted })
  }, [send])

  const sendSleepToggle = useCallback((sleeping: boolean) => {
    send({ type: 'sleep_toggle', sleeping })
  }, [send])

  const sendWakeToggle = useCallback((enable: boolean) => {
    send({ type: 'wake_toggle', enable })
  }, [send])

  const sendPttToggle = useCallback((enable: boolean) => {
    send({ type: 'ptt_toggle', enable })
  }, [send])

  const sendPayloadRemove = useCallback((path: string, name?: string, isFolder?: boolean) => {
    send({ type: 'payload_remove', path, name, is_folder: isFolder })
  }, [send])

  const sendPayloadClear = useCallback(() => {
    send({ type: 'payload_clear' })
    setActiveAttachments([])
  }, [send])

  const sendConfirmationResolve = useCallback((accepted: boolean) => {
    send({ type: 'resolve_confirmation', accepted })
    setConfirmationState((prev) => ({ ...prev, active: false }))
  }, [send])

  return {
    isConnected,
    systemState,
    audioLevel,
    micLevel,
    logs,
    logStats,
    logSources,
    audioDevices,
    remoteGateway,
    lastMessage,
    transcriptStream,
    canvasContent,
    telemetry,
    tasks,
    activeAttachments,
    setActiveAttachments,
    currentView,
    confirmationState,
    send,
    sendUserMessage,
    sendInterrupt,
    sendMuteToggle,
    sendSleepToggle,
    sendWakeToggle,
    sendPttToggle,
    sendPayloadRemove,
    sendPayloadClear,
    sendConfirmationResolve,
    clearLogs,
    cancelTask,
    saveAudioDevices,
    requestRemoteKey,
  }
}
