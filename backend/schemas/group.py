from datetime import datetime
from pydantic import BaseModel
from backend.schemas.auth import UserOut


class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupOut(BaseModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberOut(BaseModel):
    user: UserOut
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class GroupDetail(GroupOut):
    members: list[MemberOut] = []


class InviteRequest(BaseModel):
    username: str
