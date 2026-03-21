from sqlalchemy.orm import Session
from backend.models.message import Message
from backend.models.thread import Thread
from backend.models.attachment import MessageAttachment
from backend.schemas.message import MessageOut, AttachmentInfo


def _att_info(att: MessageAttachment) -> AttachmentInfo:
    import os
    return AttachmentInfo(
        id=att.id,
        filename=att.filename,
        content_type=att.content_type,
        file_size=att.file_size,
        url=f"/uploads/{os.path.basename(os.path.dirname(att.file_path))}/{att.filename}",
        is_image=att.content_type.startswith("image/"),
    )


def _msg_out(msg: Message) -> MessageOut:
    username = msg.user.username if msg.user else "GroupThink AI"
    return MessageOut(
        id=msg.id,
        thread_id=msg.thread_id,
        user_id=msg.user_id,
        username=username,
        content=msg.content,
        is_ai=msg.is_ai,
        created_at=msg.created_at,
        attachments=[_att_info(a) for a in (msg.attachments or [])],
    )


def save_message(
    db: Session,
    thread_id: int,
    content: str,
    user_id: int | None = None,
    is_ai: bool = False,
    upload_id: int | None = None,
) -> Message:
    msg = Message(thread_id=thread_id, user_id=user_id, content=content, is_ai=is_ai)
    db.add(msg)
    db.flush()
    if upload_id:
        att = db.query(MessageAttachment).filter(MessageAttachment.id == upload_id).first()
        if att and att.thread_id == thread_id:
            att.message_id = msg.id
    db.commit()
    db.refresh(msg)
    return msg


def get_message_history(
    db: Session, thread_id: int, limit: int = 50, before_id: int | None = None
) -> list[MessageOut]:
    query = db.query(Message).filter(Message.thread_id == thread_id)
    if before_id:
        query = query.filter(Message.id < before_id)
    messages = query.order_by(Message.created_at.desc()).limit(limit).all()
    messages.reverse()
    return [_msg_out(m) for m in messages]


def get_all_messages_for_thread(db: Session, thread_id: int) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at.asc())
        .all()
    )


def get_recent_messages_for_context(db: Session, thread_id: int, limit: int) -> list[Message]:
    messages = (
        db.query(Message)
        .filter(Message.thread_id == thread_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()
    return messages
