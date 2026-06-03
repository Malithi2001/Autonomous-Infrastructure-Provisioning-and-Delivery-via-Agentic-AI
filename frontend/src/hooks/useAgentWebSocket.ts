import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getApiBaseUrl } from "@/services/api";
import type { AgentWebSocketEvent, ConnectionStatus } from "@/types";

interface UseAgentWebSocketOptions {
  sessionId?: string | null;
  onToken?: (token: string) => void;
  onDone?: (sessionId?: string) => void;
  onError?: (message: string) => void;
  onPing?: () => void;
}

interface SendMessageOptions {
  message: string;
  sessionId?: string | null;
}

const MAX_RECONNECT_ATTEMPTS = 5;

function deriveWsUrl(sessionId?: string | null): string {
  const base = new URL(getApiBaseUrl(), window.location.origin);
  const protocol = base.protocol === "https:" ? "wss:" : "ws:";
  const url = new URL(`${protocol}//${base.host}`);
  url.pathname = "/api/v1/agent/ws/agent";
  if (sessionId) url.searchParams.set("session_id", sessionId);
  return url.toString();
}

function parseWebSocketEvent(raw: string): AgentWebSocketEvent | null {
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && "event" in parsed)
      return parsed as AgentWebSocketEvent;
    return null;
  } catch {
    return null;
  }
}

export function useAgentWebSocket({
  sessionId,
  onToken,
  onDone,
  onError,
  onPing,
}: UseAgentWebSocketOptions) {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [lastError, setLastError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const connectTimerRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const manuallyClosedRef = useRef(false);
  const callbacksRef = useRef({ onToken, onDone, onError, onPing });
  callbacksRef.current = { onToken, onDone, onError, onPing };

  const wsUrl = useMemo(() => deriveWsUrl(sessionId), [sessionId]);

  const cleanupReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const cleanupConnectTimer = useCallback(() => {
    if (connectTimerRef.current) {
      window.clearTimeout(connectTimerRef.current);
      connectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    cleanupReconnectTimer();
    cleanupConnectTimer();
    manuallyClosedRef.current = false;
    setStatus("connecting");

    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    socket.onopen = () => {
      reconnectAttemptsRef.current = 0;
      setStatus("connected");
      setLastError(null);
    };

    socket.onmessage = (event) => {
      const data = typeof event.data === "string" ? event.data : "";
      if (!data) return;
      const parsed = parseWebSocketEvent(data);
      if (!parsed) {
        callbacksRef.current.onToken?.(data);
        return;
      }
      if (parsed.event === "done")
        callbacksRef.current.onDone?.(parsed.session_id);
      if (parsed.event === "error") {
        const message =
          parsed.detail || parsed.message || "WebSocket chat failed.";
        setLastError(message);
        callbacksRef.current.onError?.(message);
      }
      if (parsed.event === "ping") callbacksRef.current.onPing?.();
    };

    socket.onerror = () => {
      setStatus("error");
      setLastError("Unable to connect to the streaming chat service.");
    };

    socket.onclose = (event) => {
      if (wsRef.current === socket) wsRef.current = null;
      if (manuallyClosedRef.current) return;
      const reason = event.reason || "WebSocket disconnected.";
      setStatus(event.code === 1000 ? "disconnected" : "error");
      setLastError(reason);
      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current += 1;
        const delay = Math.min(800 * reconnectAttemptsRef.current, 4000);
        reconnectTimerRef.current = window.setTimeout(connect, delay);
      }
    };
  }, [cleanupConnectTimer, cleanupReconnectTimer, wsUrl]);

  useEffect(() => {
    connectTimerRef.current = window.setTimeout(connect, 0);
    return () => {
      manuallyClosedRef.current = true;
      cleanupConnectTimer();
      cleanupReconnectTimer();
      wsRef.current?.close(1000, "Component unmounted");
      wsRef.current = null;
    };
  }, [cleanupConnectTimer, cleanupReconnectTimer, connect]);

  const sendMessage = useCallback(
    ({ message, sessionId: overrideSessionId }: SendMessageOptions) => {
      const socket = wsRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) return false;
      socket.send(
        JSON.stringify({
          message,
          session_id: overrideSessionId || sessionId || undefined,
        }),
      );
      return true;
    },
    [sessionId],
  );

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    wsRef.current?.close(1000, "Manual reconnect");
    connect();
  }, [connect]);

  return { status, lastError, sendMessage, reconnect };
}
