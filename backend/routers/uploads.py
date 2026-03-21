import os
import uuid
import base64
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.dependencies import get_db, get_current_user
from backend.models.user import User
from backend.models.thread import Thread
from backend.models.membership import GroupMembership
from backend.models.attachment import MessageAttachment
from backend.models.message import Message
from backend.utils.exceptions import NotFoundError, ForbiddenError

router = APIRouter(tags=["uploads"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "text/plain", "text/markdown", "text/csv",
    "application/json",
}


class AttachmentOut(BaseModel):
    id: int
    filename: str
    content_type: str
    file_size: int
    url: str
    extracted_text: str | None
    is_image: bool

    model_config = {"from_attributes": True}


def attachment_out(att: MessageAttachment) -> AttachmentOut:
    return AttachmentOut(
        id=att.id,
        filename=att.filename,
        content_type=att.content_type,
        file_size=att.file_size,
        url=f"/uploads/{os.path.basename(os.path.dirname(att.file_path))}/{att.filename}",
        extracted_text=att.extracted_text,
        is_image=att.content_type.startswith("image/"),
    )


def _extract_text(file_path: str, content_type: str) -> str | None:
    """Extract text from uploaded file for AI context."""
    try:
        if content_type == "application/pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                return "\n".join(page.extract_text() or "" for page in reader.pages[:20])
            except ImportError:
                return None
        elif content_type.startswith("text/") or content_type == "application/json":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()[:10000]
    except Exception:
        pass
    return None


@router.post("/threads/{thread_id}/upload", response_model=AttachmentOut)
async def upload_file(
    thread_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify thread access
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise NotFoundError("Thread not found")
    membership = db.query(GroupMembership).filter(
        GroupMembership.group_id == thread.group_id,
        GroupMembership.user_id == current_user.id,
    ).first()
    if not membership:
        raise ForbiddenError("Not a member of this group")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {file.content_type}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    # Save to uploads dir
    file_uuid = str(uuid.uuid4())
    file_dir = os.path.join(UPLOAD_DIR, file_uuid)
    os.makedirs(file_dir, exist_ok=True)
    safe_filename = os.path.basename(file.filename or "upload")
    file_path = os.path.join(file_dir, safe_filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    extracted_text = _extract_text(file_path, file.content_type)

    att = MessageAttachment(
        thread_id=thread_id,
        message_id=None,
        filename=safe_filename,
        content_type=file.content_type,
        file_path=file_path,
        file_size=len(contents),
        extracted_text=extracted_text,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return attachment_out(att)


@router.put("/messages/{message_id}", response_model=dict)
def edit_message(
    message_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise NotFoundError("Message not found")
    if msg.user_id != current_user.id:
        raise ForbiddenError("Cannot edit another user's message")
    new_content = body.get("content", "").strip()
    if not new_content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    msg.content = new_content
    db.commit()
    return {"id": msg.id, "content": msg.content}
