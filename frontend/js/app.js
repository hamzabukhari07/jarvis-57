/**
 * Main Application Orchestrator for ZEZO OS Desktop UI.
 */
import { socket } from './socket.js';
import { AvatarVisualizer } from './canvas_avatar.js';
import { TaskManagerUI } from './tasks.js';

class ZezoApp {
    constructor() {
        this.visualizer = new AvatarVisualizer('avatarCanvas', 'waveformCanvas');
        this.taskManager = new TaskManagerUI('taskMatrixList', 'taskMatrixDrawer');

        this.currentAccent = '#f24e1e';
        this.currentState = 'IDLE';
        this.activeTab = 'coding';
        this.activeTaskCount = 0;

        this._bindDOM();
        this._bindSocket();
        this._initClock();
    }

    _bindDOM() {
        // Input row
        this.cmdInput = document.getElementById('cmdInput');
        this.sendBtn = document.getElementById('sendBtn');
        if (this.sendBtn) this.sendBtn.addEventListener('click', () => this.submitInput());
        if (this.cmdInput) {
            this.cmdInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.submitInput();
                }
            });
        }

        // Header buttons
        this.drawerBtn = document.getElementById('drawerBtn');
        this.quickDrawer = document.getElementById('quickDrawer');
        if (this.drawerBtn) {
            this.drawerBtn.addEventListener('click', () => {
                this.quickDrawer.classList.toggle('hidden');
                this.drawerBtn.classList.toggle('active');
            });
        }

        this.matrixBtn = document.getElementById('matrixBtn');
        this.matrixDrawer = document.getElementById('matrixDrawer');
        if (this.matrixBtn) {
            this.matrixBtn.addEventListener('click', () => {
                this.matrixDrawer.classList.toggle('open');
            });
        }

        this.qrBtn = document.getElementById('qrBtn');
        this.remoteModal = document.getElementById('remoteModal');
        if (this.qrBtn) {
            this.qrBtn.addEventListener('click', () => {
                this.openRemoteModal();
            });
        }

        // Log Copy Bar buttons
        const copyAllBtn = document.getElementById('copyAllBtn');
        if (copyAllBtn) copyAllBtn.addEventListener('click', () => this.copyAllLogs());
        const clearLogBtn = document.getElementById('clearLogBtn');
        if (clearLogBtn) clearLogBtn.addEventListener('click', () => this.clearLogs());

        // Multi-view operational tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabKey = e.currentTarget.getAttribute('data-tab');
                this.switchTab(tabKey);
            });
        });

        // Theme accent color picker
        document.querySelectorAll('.theme-dot').forEach(dot => {
            dot.addEventListener('click', (e) => {
                const color = e.currentTarget.getAttribute('data-color');
                this.setAccentColor(color);
            });
        });
    }

    _bindSocket() {
        socket.on('connect', () => {
            this.appendLog('SYS', 'Connected to ZEZO Core Engine');
            socket.send('get_initial_state');
        });

        socket.on('disconnect', () => {
            this.appendLog('SYS', 'Disconnected from Core Engine — reconnecting...');
        });

        socket.on('init', (data) => {
            if (data.state) this.setState(data.state);
            if (data.tasks) this.taskManager.updateTasks(data.tasks);
        });

        socket.on('state_change', (data) => {
            if (data && data.state) {
                this.setState(data.state);
            }
        });

        socket.on('telemetry_update', (metrics) => {
            this.updateTelemetry(metrics);
        });

        socket.on('task_update', (task) => {
            this.taskManager.updateTasks([task]);
        });

        socket.on('task_list', (tasks) => {
            this.taskManager.updateTasks(tasks);
        });

        socket.on('log_entry', (entry) => {
            this.appendLog(entry.tag || 'SYS', entry.message || '');
        });

        socket.on('content_display', (payload) => {
            this.showInspectorContent(payload.title, payload.text);
        });

        socket.on('accent_changed', (data) => {
            if (data && data.color) {
                this.applyAccentCSS(data.color);
            }
        });

        socket.on('remote_key_data', (data) => {
            this.renderRemoteKey(data.url, data.key);
        });

        socket.connect();
    }

    _initClock() {
        const timeEl = document.getElementById('clockTime');
        const dateEl = document.getElementById('clockDate');
        const update = () => {
            const now = new Date();
            if (timeEl) timeEl.textContent = now.toTimeString().split(' ')[0];
            if (dateEl) dateEl.textContent = now.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase();
        };
        setInterval(update, 1000);
        update();
    }

    setState(stateName) {
        this.currentState = (stateName || 'IDLE').toUpperCase();
        this.visualizer.setState(this.currentState);

        const stateLabel = document.getElementById('capsuleState');
        const stateDot = document.getElementById('capsuleDot');

        if (stateLabel) stateLabel.textContent = this.currentState;
        if (stateDot) {
            let color = '#22c55e';
            if (this.currentState === 'SPEAKING') color = this.currentAccent;
            if (this.currentState === 'THINKING') color = '#06b6d4';
            if (this.currentState === 'MUTED') color = '#ef4444';
            stateDot.style.background = color;
            stateDot.style.boxShadow = `0 0 8px ${color}`;
        }
    }

    setAccentColor(colorHex) {
        if (!colorHex) return;
        this.applyAccentCSS(colorHex);
        socket.send('set_accent', { color: colorHex });
        this.appendLog('SYS', `UI accent theme set to ${colorHex.toUpperCase()}`);
    }

    applyAccentCSS(colorHex) {
        this.currentAccent = colorHex;
        document.documentElement.style.setProperty('--accent', colorHex);
        document.documentElement.style.setProperty('--accent-dim', `${colorHex}26`);
        document.documentElement.style.setProperty('--accent-ghost', `${colorHex}14`);
        this.visualizer.setAccent(colorHex);
    }

    updateTelemetry(m = {}) {
        const updateBar = (id, val, text) => {
            const fill = document.getElementById(`bar_${id}`);
            const lbl = document.getElementById(`val_${id}`);
            if (fill) fill.style.width = `${Math.min(100, Math.max(0, val))}%`;
            if (lbl) lbl.textContent = text;
        };

        if (m.cpu !== undefined) updateBar('cpu', m.cpu, `${m.cpu.toFixed(0)}%`);
        if (m.mem !== undefined) updateBar('mem', m.mem, `${m.mem.toFixed(0)}%`);
        if (m.gpu !== undefined) updateBar('gpu', m.gpu >= 0 ? m.gpu : 0, m.gpu >= 0 ? `${m.gpu.toFixed(0)}%` : 'N/A');
        if (m.net !== undefined) {
            const netStr = m.net < 1.0 ? `${(m.net * 1024).toFixed(0)}KB/s` : `${m.net.toFixed(1)}MB/s`;
            updateBar('net', Math.min(100, m.net * 10), netStr);
        }
        if (m.tmp !== undefined) updateBar('tmp', m.tmp >= 0 ? m.tmp : 0, m.tmp >= 0 ? `${m.tmp.toFixed(0)}°C` : 'N/A');
    }

    appendLog(tag, message) {
        const stream = document.getElementById('activityStream');
        if (!stream || !message) return;

        // Suppress internal state transitions from cluttering the activity stream
        if (message.startsWith('State changed to') || message.startsWith('SYS: State changed to')) {
            return;
        }

        const now = new Date();
        const ts = now.toTimeString().split(' ')[0];
        const tagUpper = (tag || 'SYS').toUpperCase();

        let tagClass = 'sys';
        if (tagUpper === 'USER') tagClass = 'user';
        if (tagUpper === 'AI' || tagUpper === 'ZEZO') tagClass = 'ai';
        if (tagUpper === 'FILE') tagClass = 'file';
        if (tagUpper === 'TASK') tagClass = 'task';
        if (tagUpper === 'ERR') tagClass = 'err';

        const row = document.createElement('div');
        row.className = 'log-entry';
        row.innerHTML = `
            <span class="log-ts">${ts}</span>
            <span class="log-tag ${tagClass}">[${tagUpper}]</span>
            <span class="log-msg">${this._escapeHTML(message)}</span>
        `;
        stream.appendChild(row);
        stream.scrollTop = stream.scrollHeight;

        const countEl = document.getElementById('logCountLabel');
        if (countEl) {
            countEl.textContent = `${stream.children.length} lines`;
        }
    }

    _escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
        );
    }

    copyAllLogs() {
        const stream = document.getElementById('activityStream');
        if (!stream) return;
        const text = Array.from(stream.children).map(c => c.textContent.trim()).join('\n');
        navigator.clipboard.writeText(text);
        this.appendLog('SYS', `Copied ${stream.children.length} lines to clipboard`);
    }

    clearLogs() {
        const stream = document.getElementById('activityStream');
        if (stream) stream.innerHTML = '';
        const countEl = document.getElementById('logCountLabel');
        if (countEl) countEl.textContent = '0 lines';
    }

    switchTab(tabKey) {
        this.activeTab = tabKey;
        document.querySelectorAll('.tab-btn').forEach(b => {
            b.classList.toggle('active', b.getAttribute('data-tab') === tabKey);
        });

        const titleEl = document.getElementById('inspectorTitle');
        const bodyEl = document.getElementById('inspectorBody');
        if (!bodyEl || !titleEl) return;

        const tabData = {
            coding: {
                title: '⚡ CODING AGENT INSPECTION',
                text: 'ZEZO Coder Engine: Antigravity CLI bound.\nTarget Workspace: Active Repository\nHardware Affinity: Cores 0-3 (Job Object Active)\n\nReady for code synthesis and multi-file refactoring.'
            },
            web: {
                title: '🔍 WEB RESEARCH & SCRAPING',
                text: 'Web Search & Deep Extraction Engine active.\nCrawler: Async Playwright & DuckDuckGo Scraper.\nSynthesized: Live token matrix & markdown parser.'
            },
            file: {
                title: '📄 MULTIMODAL FILE EXTRACTION',
                text: 'MarkItDown & Multimodal Vision Ingestion Pipeline.\nSupported Formats: PDF, DOCX, XLSX, PPTX, CSV, PNG, JPG.\nTruncation Guard: 64KB per payload with full FTS5 indexing.'
            },
            social: {
                title: '🌐 SOCIAL INTELLIGENCE GRAPH',
                text: 'Social Intelligence Graph & Profile Aggregator.\nEndpoints: GitHub API, YouTube Data API, Research Index.\nBM25 Semantic Ranking: Active.'
            },
            system: {
                title: '📊 HARDWARE TELEMETRY MATRIX',
                text: 'Live Hardware Telemetry Stream:\nCPU Load, RAM Usage, Network IO, and GPU Acceleration online.\nPower Profile: High Performance.'
            },
            voice: {
                title: '🎙️ LIVE TRANSCRIPT & AUDIO STREAM',
                text: 'Real-time Bidirectional Audio Stream:\nProtocol: Gemini Live WebSockets (DirectSound 16kHz PCM)\nSelf-Echo Filter: Active (463ms tail suppression)\nViseme Extraction: 50 Hz formant tracker'
            }
        };

        const current = tabData[tabKey] || tabData.coding;
        titleEl.textContent = current.title;
        bodyEl.textContent = current.text;
    }

    showInspectorContent(title, text) {
        const inspector = document.getElementById('inspectorPanel');
        const titleEl = document.getElementById('inspectorTitle');
        const bodyEl = document.getElementById('inspectorBody');
        if (inspector) inspector.classList.remove('hidden');
        if (titleEl) titleEl.textContent = title;
        if (bodyEl) bodyEl.textContent = text;
    }

    openRemoteModal() {
        if (this.remoteModal) {
            this.remoteModal.classList.add('open');
            socket.send('get_remote_key');
        }
    }

    closeRemoteModal() {
        if (this.remoteModal) this.remoteModal.classList.remove('open');
    }

    renderRemoteKey(url, key) {
        const keyEl = document.getElementById('remoteKeyDisplay');
        const urlEl = document.getElementById('remoteUrlDisplay');
        if (keyEl) keyEl.textContent = key || '8F3A-9K2L';
        if (urlEl) urlEl.textContent = url || 'http://localhost:8765';
    }

    cancelTask(taskId) {
        if (!taskId) return;
        socket.send('task_cancel', { task_id: taskId });
        this.appendLog('TASK', `Cancelled task #${taskId.slice(0, 8)}`);
    }

    submitInput() {
        if (!this.cmdInput) return;
        const text = this.cmdInput.value.trim();
        if (!text) return;
        this.appendLog('USER', text);
        socket.send('user_message', { text });
        this.cmdInput.value = '';
    }

    start() {
        this.visualizer.start();
        this.switchTab('coding');
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.zezoApp = new ZezoApp();
    window.zezoApp.start();
});
