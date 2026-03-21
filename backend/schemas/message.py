from datetime import datetime
from pydantic import BaseModel


class AttachmentInfo(BaseModel):
    id: int
    filename: str
    content_type: str
    file_size: int
    url: str
    is_image: bool

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    thread_id: int
    user_id: int | None
    username: str | None
    content: str
    is_ai: bool
    created_at: datetime
    attachments: list[AttachmentInfo] = []

    model_config = {"from_attributes": True}


class WSMessagePayload(BaseModel):
    type: str = "message"
    content: str
    upload_id: int | None = None
