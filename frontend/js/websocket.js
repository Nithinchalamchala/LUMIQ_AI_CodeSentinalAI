/**
 * WebSocket client with auto-reconnect for real-time agent events.
 */

class AgentWebSocket {
    constructor() {
        this.ws = null;
        this.jobId = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.handlers = {
            agent_event: [],
            status_update: [],
            heartbeat: [],
            error: [],
            open: [],
            close: []
        };
        this.pingInterval = null;
    }

    connect(jobId) {
        this.jobId = jobId;
        this.reconnectAttempts = 0;
        this._connect();
    }

    _connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/${this.jobId}`;

        try {
            this.ws = new WebSocket(url);
        } catch (e) {
            console.error('WebSocket connection failed:', e);
            this._scheduleReconnect();
            return;
        }

        this.ws.onopen = () => {
            console.log(`[WS] Connected to job ${this.jobId}`);
            this.reconnectAttempts = 0;
            this._emit('open', {});

            // Start ping interval
            this.pingInterval = setInterval(() => {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send('ping');
                }
            }, 25000);
        };

        this.ws.onmessage = (event) => {
            if (event.data === 'pong') return;

            try {
                const message = JSON.parse(event.data);
                const type = message.type || 'unknown';
                const data = message.data || {};
                this._emit(type, data);
            } catch (e) {
                console.warn('[WS] Parse error:', e);
            }
        };

        this.ws.onclose = (event) => {
            console.log(`[WS] Disconnected (code: ${event.code})`);
            clearInterval(this.pingInterval);
            this._emit('close', { code: event.code });

            if (event.code !== 1000) {
                this._scheduleReconnect();
            }
        };

        this.ws.onerror = (error) => {
            console.error('[WS] Error:', error);
            this._emit('error', { error });
        };
    }

    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('[WS] Max reconnect attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => this._connect(), delay);
    }

    on(event, handler) {
        if (!this.handlers[event]) {
            this.handlers[event] = [];
        }
        this.handlers[event].push(handler);
    }

    _emit(event, data) {
        const handlers = this.handlers[event] || [];
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (e) {
                console.error(`[WS] Handler error for ${event}:`, e);
            }
        });
    }

    disconnect() {
        clearInterval(this.pingInterval);
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
    }
}

// Global instance
const agentWS = new AgentWebSocket();
