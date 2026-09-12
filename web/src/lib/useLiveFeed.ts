import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getAccessToken, onAuthChange } from "./auth";
import type { WsMessage } from "./types";

const BASE_RECONNECT_MS = 1000;
const MAX_RECONNECT_MS = 30000;

/** Connects to /ws?token=<access token>; every push (a new call, or a
 * status change on an existing one) invalidates the "calls" query so the
 * feed and any list using useCalls() pick it up without polling. */
export function useLiveFeed() {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<WsMessage[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closedByUsRef = useRef(false);

  useEffect(() => {
    function clearReconnectTimer() {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    }

    function connect() {
      const token = getAccessToken();
      if (!token) return;

      closedByUsRef.current = false;
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const socket = new WebSocket(`${proto}//${window.location.host}/ws?token=${encodeURIComponent(token)}`);
      socketRef.current = socket;

      socket.onopen = () => {
        attemptRef.current = 0;
        setConnected(true);
      };

      socket.onmessage = (evt) => {
        let msg: WsMessage;
        try {
          msg = JSON.parse(evt.data);
        } catch {
          return;
        }
        setEvents((prev) => [msg, ...prev].slice(0, 200));
        queryClient.invalidateQueries({ queryKey: ["calls"] });
      };

      socket.onclose = () => {
        setConnected(false);
        socketRef.current = null;
        if (closedByUsRef.current) return;
        const delay = Math.min(BASE_RECONNECT_MS * 2 ** attemptRef.current, MAX_RECONNECT_MS);
        attemptRef.current += 1;
        clearReconnectTimer();
        reconnectTimerRef.current = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    function teardown() {
      closedByUsRef.current = true;
      clearReconnectTimer();
      attemptRef.current = 0;
      socketRef.current?.close();
      socketRef.current = null;
      setConnected(false);
    }

    if (getAccessToken()) connect();
    const unsubscribe = onAuthChange((authed) => {
      teardown();
      if (authed) connect();
    });

    return () => {
      unsubscribe();
      teardown();
    };
  }, [queryClient]);

  return { connected, events };
}
