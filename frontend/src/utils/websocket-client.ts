export type ConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

export interface WSMessageListeners {
  onMessage: (channel: string, data: any) => void;
  onStateChange: (channel: string, state: ConnectionState) => void;
}

export class MoodMarketWSClient {
  private baseWSUrl: string;
  private baseHttpUrl: string;
  private token: string | null = null;
  private listeners: WSMessageListeners;
  private sockets: Map<string, WebSocket> = new Map();
  private reconnectTimers: Map<string, number> = new Map();
  private backoffDelays: Map<string, number> = new Map();
  private pingIntervals: Map<string, number> = new Map();
  private offlineQueues: Map<string, any[]> = new Map();
  private currentTicker: string = '';
  private isDestroyed: boolean = false;

  constructor(listeners: WSMessageListeners, wsUrl = 'ws://localhost:8000', httpUrl = 'http://localhost:8000') {
    this.baseWSUrl = wsUrl;
    this.baseHttpUrl = httpUrl;
    this.listeners = listeners;
  }

  /**
   * Fetch token and connect to sockets for the given ticker
   */
  async initialize(ticker: string) {
    this.isDestroyed = false;
    this.currentTicker = ticker.toUpperCase().trim();
    
    // Fetch auth token from server if we don't have it yet
    if (!this.token) {
      try {
        const res = await fetch(`${this.baseHttpUrl}/api/v1/auth/token`);
        if (res.ok) {
          const body = await res.json();
          this.token = body.token;
        } else {
          console.warn('Failed to fetch auth token, falling back to HTTP fallback mode.');
        }
      } catch (err) {
        console.error('Error fetching WebSocket token:', err);
      }
    }

    if (!this.token) {
      this.listeners.onStateChange('global', 'disconnected');
      return;
    }

    // Connect to anomaly broadcast channel (only once)
    this.connectChannel('anomaly', `${this.baseWSUrl}/ws/anomaly?token=${this.token}`);

    // Connect to ticker specific channels
    this.connectTickerChannels(this.currentTicker);
  }

  private connectTickerChannels(ticker: string) {
    this.connectChannel(`price:${ticker}`, `${this.baseWSUrl}/ws/price/${ticker}?token=${this.token}`);
    this.connectChannel(`sentiment:${ticker}`, `${this.baseWSUrl}/ws/sentiment/${ticker}?token=${this.token}`);
  }

  /**
   * Change ticker: disconnect previous ticker channels and connect new ones
   */
  changeTicker(newTicker: string) {
    const cleanTicker = newTicker.toUpperCase().trim();
    if (this.currentTicker === cleanTicker) return;

    // Disconnect old ticker specific channels
    this.disconnectChannel(`price:${this.currentTicker}`);
    this.disconnectChannel(`sentiment:${this.currentTicker}`);

    this.currentTicker = cleanTicker;
    
    if (this.token) {
      this.connectTickerChannels(this.currentTicker);
    }
  }

  private connectChannel(channel: string, url: string) {
    if (this.isDestroyed) return;

    // Disconnect previous socket if any
    this.disconnectChannel(channel);

    this.listeners.onStateChange(channel, 'connecting');
    const ws = new WebSocket(url);
    this.sockets.set(channel, ws);

    ws.onopen = () => {
      this.listeners.onStateChange(channel, 'connected');
      this.backoffDelays.set(channel, 1000); // reset backoff delay
      
      // Start heartbeat ping/pong loop (sending keepalive every 30s)
      this.startHeartbeat(channel);

      // Flush offline queue if any messages were queued
      const queue = this.offlineQueues.get(channel) || [];
      while (queue.length > 0) {
        const msg = queue.shift();
        ws.send(JSON.stringify(msg));
      }
      this.offlineQueues.delete(channel);
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        this.listeners.onMessage(channel, parsed);
      } catch (err) {
        console.warn(`Could not parse JSON on channel ${channel}:`, event.data);
      }
    };

    ws.onclose = () => {
      this.cleanupSocketState(channel);
      this.listeners.onStateChange(channel, 'disconnected');
      
      // Trigger reconnect
      this.scheduleReconnect(channel, url);
    };

    ws.onerror = (err) => {
      console.warn(`WebSocket error on channel ${channel}:`, err);
      ws.close();
    };
  }

  private disconnectChannel(channel: string) {
    const ws = this.sockets.get(channel);
    if (ws) {
      // Remove onClose handler to prevent auto-reconnect loops on manual disconnect
      ws.onclose = null;
      ws.close();
      this.cleanupSocketState(channel);
      this.sockets.delete(channel);
    }
    this.listeners.onStateChange(channel, 'disconnected');
  }

  private cleanupSocketState(channel: string) {
    // Clear ping interval
    const timer = this.pingIntervals.get(channel);
    if (timer) {
      window.clearInterval(timer);
      this.pingIntervals.delete(channel);
    }
  }

  private startHeartbeat(channel: string) {
    const timer = window.setInterval(() => {
      const ws = this.sockets.get(channel);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);
    this.pingIntervals.set(channel, timer);
  }

  private scheduleReconnect(channel: string, url: string) {
    if (this.isDestroyed) return;

    // Clear previous reconnection timer
    const prevTimer = this.reconnectTimers.get(channel);
    if (prevTimer) {
      window.clearTimeout(prevTimer);
    }

    const currentDelay = this.backoffDelays.get(channel) || 1000;
    this.listeners.onStateChange(channel, 'reconnecting');

    const nextTimer = window.setTimeout(() => {
      this.connectChannel(channel, url);
    }, currentDelay);

    this.reconnectTimers.set(channel, nextTimer);
    
    // Scale exponential backoff (1s, 2s, 4s, 8s max)
    const nextDelay = Math.min(currentDelay * 2, 8000);
    this.backoffDelays.set(channel, nextDelay);
  }

  /**
   * Queue message to send (supports offline scenario by queueing)
   */
  sendMessage(channel: string, msg: any) {
    const ws = this.sockets.get(channel);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    } else {
      if (!this.offlineQueues.has(channel)) {
        this.offlineQueues.set(channel, []);
      }
      this.offlineQueues.get(channel)!.push(msg);
    }
  }

  /**
   * Clean up all WebSocket connections and timers
   */
  destroy() {
    this.isDestroyed = true;
    
    // Disconnect all sockets
    for (const channel of this.sockets.keys()) {
      this.disconnectChannel(channel);
    }
    
    // Clear reconnect timers
    for (const timer of this.reconnectTimers.values()) {
      window.clearTimeout(timer);
    }
    this.reconnectTimers.clear();
  }
}
