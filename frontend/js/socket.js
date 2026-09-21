/**
 * Resilient WebSocket Client for ZEZO OS.
 * Manages connection to local Python UI Server with auto-reconnect and event pub/sub.
 */

class ZezoSocket {
    constructor() {
        this.ws = null;
        this.handlers = new Map();
        this.connected = false;
        this.reconnectTimer = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 8000;
        this.url = this._getWebSocketUrl();
    }

    _getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host || '127.0.0.1:8765';
        return `${protocol}//${host}/ws`;
    }

    connect() {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            return;
        }

        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                this.connected = true;
                this.reconnectDelay = 1000;
                console.log('[ZEZO-WS] Connected to Python backend at', this.url);
                this._emit('connect', { connected: true });
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    const { type, data } = message;
                    if (type) {
                        this._emit(type, data);
                        this._emit('*', message);
                    }
                } catch (err) {
                    console.warn('[ZEZO-WS] Failed to parse incoming JSON payload:', err, event.data);
                }
            };

            this.ws.onclose = (event) => {
                this.connected = false;
                console.log('[ZEZO-WS] Connection closed, retrying in', this.reconnectDelay, 'ms...');
                this._emit('disconnect', { event });
                this._scheduleReconnect();
            };

            this.ws.onerror = (err) => {
                console.warn('[ZEZO-WS] WebSocket error:', err);
            };
        } catch (err) {
            console.error('[ZEZO-WS] Failed to initialize WebSocket:', err);
            this._scheduleReconnect();
        }
    }

    _scheduleReconnect() {
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        this.reconnectTimer = setTimeout(() => {
            this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
            this.connect();
        }, this.reconnectDelay);
    }

    send(type, payload = {}) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.warn('[ZEZO-WS] Cannot send message, WebSocket not open:', type);
            return false;
        }
        try {
            this.ws.send(JSON.stringify({ type, ...payload }));
            return true;
        } catch (err) {
            console.error('[ZEZO-WS] Error sending message:', err);
            return false;
        }
    }

    on(eventType, callback) {
        if (!this.handlers.has(eventType)) {
            this.handlers.set(eventType, new Set());
        }
        this.handlers.get(eventType).add(callback);
        return () => this.off(eventType, callback);
    }

    off(eventType, callback) {
        if (this.handlers.has(eventType)) {
            this.handlers.get(eventType).delete(callback);
        }
    }

    _emit(eventType, data) {
        const callbacks = this.handlers.get(eventType);
        if (callbacks) {
            callbacks.forEach(cb => {
                try {
                    cb(data);
                } catch (e) {
                    console.error(`[ZEZO-WS] Error in handler for ${eventType}:`, e);
                }
            });
        }
    }
}

export const socket = new ZezoSocket();
