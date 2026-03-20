import json
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # thread_id -> list of active WebSocket connections
        self._rooms: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, thread_id: int) -> None:
        await websocket.accept()
        self._rooms.setdefault(thread_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, thread_id: int) -> None:
        room = self._rooms.get(thread_id, [])
        if websocket in room:
            room.remove(websocket)
        if not room:
            self._rooms.pop(thread_id, None)

    async def broadcast(self, message: dict, thread_id: int) -> None:
        payload = json.dumps(message, default=str)
        dead = []
        for ws in self._rooms.get(thread_id, []):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, thread_id)

    async def send_personal(self, message: dict, websocket: WebSocket) -> None:
        await websocket.send_text(json.dumps(message, default=str))


manager = ConnectionManager()
