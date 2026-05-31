/* ============================================================
   VIT WebSocket Service — INT2
   Auto-reconnect, message routing, offline queue
   ============================================================ */

type MessageHandler = (data: unknown) => void;

interface WSOptions {
  reconnectDelay?: number;
  maxReconnectDelay?: number;
  maxReconnectAttempts?: number;
}

type WSEvent =
  | "notification"
  | "prediction_update"
  | "price_update"
  | "match_update"
  | "wallet_update"
  | "live_score_update"
  | "system";

class VITWebSocketService {
  private ws: WebSocket | null = null;
  private url = "";
  private handlers: Map<WSEvent, Set<MessageHandler>> = new Map();
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private offlineQueue: unknown[] = [];
  private stopped = false;
  private options: Required<WSOptions>;

  constructor(options: WSOptions = {}) {
    this.options = {
      reconnectDelay: options.reconnectDelay ?? 1000,
      maxReconnectDelay: options.maxReconnectDelay ?? 30000,
      maxReconnectAttempts: options.maxReconnectAttempts ?? 10,
    };
  }

  connect(userId: number | string): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.stopped = false;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const token = localStorage.getItem("vit_token") ?? "";
    this.url = `${proto}://${window.location.host}/api/notifications/ws/${userId}?token=${token}`;
    this._open();
  }

  disconnect(): void {
    this.stopped = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }

  on(event: WSEvent, handler: MessageHandler): () => void {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(handler);
    return () => this.handlers.get(event)?.delete(handler);
  }

  send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      this.offlineQueue.push(data);
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private _open(): void {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this._emit("system", { type: "connected" });
        this._flushQueue();
      };

      this.ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          const type = (msg?.type ?? "notification") as WSEvent;
          this._emit(type, msg);
          this._emit("notification", msg);
        } catch {
          this._emit("notification", { raw: e.data });
        }
      };

      this.ws.onclose = (ev) => {
        this._emit("system", { type: "disconnected", code: ev.code });
        if (ev.code === 4001) {
          // Auth failure — token invalid or missing, redirect to login
          this.stopped = true;
          localStorage.removeItem("vit_token");
          localStorage.removeItem("vit_refresh_token");
          window.dispatchEvent(new Event("vit:logout"));
          return;
        }
        if (!this.stopped) this._scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch {
      if (!this.stopped) this._scheduleReconnect();
    }
  }

  private _emit(event: WSEvent, data: unknown): void {
    this.handlers.get(event)?.forEach((h) => {
      try { h(data); } catch { /* noop */ }
    });
  }

  private _scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) return;
    const delay = Math.min(
      this.options.reconnectDelay * 2 ** this.reconnectAttempts,
      this.options.maxReconnectDelay,
    );
    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => this._open(), delay);
  }

  private _flushQueue(): void {
    while (this.offlineQueue.length > 0) {
      const item = this.offlineQueue.shift();
      this.send(item);
    }
  }
}

export const vitWS = new VITWebSocketService();
export type { WSEvent, MessageHandler };
