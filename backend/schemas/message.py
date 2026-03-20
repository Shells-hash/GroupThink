from datetime import datetime
from pydantic import BaseModel


class MessageOut(BaseModel):
    id: int
    thread_id: int
    user_id: int | None
    username: str | None
    content: str
    is_ai: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WSMessagePayload(BaseModel):
    type: str = "message"
    content: str
