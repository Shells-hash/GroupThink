from datetime import datetime
from pydantic import BaseModel


class ThreadCreate(BaseModel):
    title: str


class ThreadOut(BaseModel):
    id: int
    group_id: int
    title: str
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}
