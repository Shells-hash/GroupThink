import { state } from "./state.js";

let socket = null;
let onMessageCallback = null;
let reconnectTimer = null;
let currentThreadId = null;

export function onWsMessage(cb) {
  onMessageCallback = cb;
}

export function connectToThread(threadId) {
  if (socket) {
    socket.close();
    socket = null;
  }
  clearTimeout(reconnectTimer);
  currentThreadId = threadId;
  _connect(threadId);
}

export function disconnectWs() {
  currentThreadId = null;
  if (socket) { socket.close(); socket = null; }
}

export function sendMessage(content) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.warn("WebSocket not connected");
    return;
  }
  socket.send(JSON.stringify({ type: "message", content }));
}

function _connect(threadId) {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocol}://${location.host}/ws/${threadId}?token=${state.token}`;
  socket = new WebSocket(url);

  socket.addEventListener("message", (e) => {
    try {
      const data = JSON.parse(e.data);
      if (onMessageCallback) onMessageCallback(data);
    } catch {
      console.error("Invalid WS message", e.data);
    }
  });

  socket.addEventListener("close", (e) => {
    socket = null;
    // Reconnect unless intentionally closed or auth failure
    if (currentThreadId === threadId && e.code !== 4001 && e.code !== 4003) {
      reconnectTimer = setTimeout(() => _connect(threadId), 3000);
    }
  });

  socket.addEventListener("error", () => {
    socket?.close();
  });
}
