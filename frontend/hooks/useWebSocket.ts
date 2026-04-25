import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketMessage {
  command?: string;
  [key: string]: any;
}

const DEFAULT_WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:7860/ws';

export function useWebSocket(url: string = DEFAULT_WS_URL) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        console.log(`Connected to WebSocket: ${url}`);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
        } catch (err) {
          console.error("Failed to parse WebSocket message:", event.data);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log(`Disconnected from WebSocket: ${url}. Reconnecting in 5s...`);
        reconnectTimeout.current = setTimeout(connect, 5000);
      };

      ws.onerror = (error) => {
        // Use console.warn instead of console.error to prevent the Next.js 
        // dev error overlay from popping up when the backend is offline.
        console.warn(`WebSocket connection failed (${url}). Is the backend running?`);
        ws.close();
      };

      setSocket(ws);
    } catch (err) {
      console.error("Failed to connect to WebSocket:", err);
    }
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (socket) {
        socket.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (socket && isConnected) {
      socket.send(JSON.stringify(message));
    } else {
      console.warn("WebSocket is not connected. Cannot send message.");
    }
  }, [socket, isConnected]);

  return { isConnected, lastMessage, sendMessage };
}
