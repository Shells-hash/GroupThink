from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from backend.database.engine import SessionLocal
from backend.services import auth_service
from backend.services.message_service import save_message
from backend.services.ai_service import get_ai_reply
from backend.models.thread import Thread
from backend.models.membership import GroupMembership
from backend.utils.websocket_manager import manager
from backend.schemas.message import WSMessagePayload

router = APIRouter(tags=["websocket"])


def _get_db_session() -> Session:
    return SessionLocal()


@router.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: int, token: str):
    # Authenticate via query param token
    db = _get_db_session()
    try:
        user_id = auth_service.decode_token(token)
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return

        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return

        thread = db.query(Thread).filter(Thread.id == thread_id).first()
        if not thread:
            await websocket.close(code=4004, reason="Thread not found")
            return

        membership = (
            db.query(GroupMembership)
            .filter(
                GroupMembership.group_id == thread.group_id,
                GroupMembership.user_id == user_id,
            )
            .first()
        )
        if not membership:
            await websocket.close(code=4003, reason="Not a group member")
            return
    finally:
        db.close()

    await manager.connect(websocket, thread_id)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = WSMessagePayload.model_validate_json(raw)
            except Exception:
                await manager.send_personal({"type": "error", "detail": "Invalid message format"}, websocket)
                continue

            db = _get_db_session()
            try:
                # Persist and broadcast human message
                msg = save_message(db, thread_id, payload.content, user_id=user_id)
                await manager.broadcast(
                    {
                        "type": "message",
                        "message_id": msg.id,
                        "thread_id": thread_id,
                        "user_id": user_id,
                        "username": user.username,
                        "content": msg.content,
                        "is_ai": False,
                        "created_at": msg.created_at,
                    },
                    thread_id,
                )

                # Trigger AI if @ai is mentioned
                if "@ai" in payload.content.lower():
                    await manager.broadcast(
                        {"type": "ai_thinking", "thread_id": thread_id}, thread_id
                    )
                    ai_text = get_ai_reply(db, thread_id, payload.content, user.username)
                    ai_msg = save_message(db, thread_id, ai_text, user_id=None, is_ai=True)
                    await manager.broadcast(
                        {
                            "type": "message",
                            "message_id": ai_msg.id,
                            "thread_id": thread_id,
                            "user_id": None,
                            "username": "GroupThink AI",
                            "content": ai_msg.content,
                            "is_ai": True,
                            "created_at": ai_msg.created_at,
                        },
                        thread_id,
                    )
            finally:
                db.close()

    except WebSocketDisconnect:
        manager.disconnect(websocket, thread_id)
