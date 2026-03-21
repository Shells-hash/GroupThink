from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from backend.database.engine import SessionLocal
from backend.services import auth_service
from backend.services.message_service import save_message
from backend.services.ai_service import get_ai_reply_stream, get_ai_vision_reply
from backend.models.thread import Thread
from backend.models.membership import GroupMembership
from backend.models.attachment import MessageAttachment
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
                # Save human message (with optional attachment)
                msg = save_message(
                    db, thread_id, payload.content,
                    user_id=user_id, upload_id=payload.upload_id
                )

                # Build attachment info for broadcast
                att_data = []
                attachment = None
                if payload.upload_id:
                    attachment = db.query(MessageAttachment).filter(
                        MessageAttachment.id == payload.upload_id
                    ).first()
                    if attachment:
                        import os as _os
                        att_data = [{
                            "id": attachment.id,
                            "filename": attachment.filename,
                            "content_type": attachment.content_type,
                            "file_size": attachment.file_size,
                            "url": f"/uploads/{_os.path.basename(_os.path.dirname(attachment.file_path))}/{attachment.filename}",
                            "is_image": attachment.content_type.startswith("image/"),
                        }]

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
                        "attachments": att_data,
                    },
                    thread_id,
                )

                # Trigger AI if @ai is mentioned
                if "@ai" in payload.content.lower():
                    await manager.broadcast(
                        {"type": "ai_thinking", "thread_id": thread_id}, thread_id
                    )

                    # Vision reply if image attached
                    if attachment and attachment.content_type.startswith("image/"):
                        import base64 as _b64
                        with open(attachment.file_path, "rb") as f:
                            img_b64 = _b64.b64encode(f.read()).decode()
                        ai_text = get_ai_vision_reply(payload.content, img_b64, attachment.content_type)
                        ai_msg = save_message(db, thread_id, ai_text, user_id=None, is_ai=True)
                        await manager.broadcast(
                            {
                                "type": "ai_message_complete",
                                "message_id": ai_msg.id,
                                "thread_id": thread_id,
                                "user_id": None,
                                "username": "GroupThink AI",
                                "content": ai_msg.content,
                                "is_ai": True,
                                "created_at": ai_msg.created_at,
                                "attachments": [],
                            },
                            thread_id,
                        )
                    else:
                        # Text context: include extracted file text if present
                        content_with_context = payload.content
                        if attachment and attachment.extracted_text:
                            content_with_context = (
                                f"{payload.content}\n\n"
                                f"[Attached file: {attachment.filename}]\n{attachment.extracted_text[:3000]}"
                            )
                        # Stream tokens via WebSocket
                        full_ai_text = ""
                        async for token in get_ai_reply_stream(db, thread_id, content_with_context, user.username):
                            full_ai_text += token
                            await manager.broadcast(
                                {"type": "ai_delta", "thread_id": thread_id, "token": token},
                                thread_id,
                            )
                        ai_msg = save_message(db, thread_id, full_ai_text, user_id=None, is_ai=True)
                        await manager.broadcast(
                            {
                                "type": "ai_message_complete",
                                "message_id": ai_msg.id,
                                "thread_id": thread_id,
                                "user_id": None,
                                "username": "GroupThink AI",
                                "content": ai_msg.content,
                                "is_ai": True,
                                "created_at": ai_msg.created_at,
                                "attachments": [],
                            },
                            thread_id,
                        )
            finally:
                db.close()

    except WebSocketDisconnect:
        manager.disconnect(websocket, thread_id)
