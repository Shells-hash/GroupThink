from datetime import datetime
from pydantic import BaseModel


class ActionItem(BaseModel):
    task: str
    assignee: str | None = None
    due_date: str | None = None


class PlanOut(BaseModel):
    id: int
    thread_id: int
    goals: list[str]
    action_items: list[ActionItem]
    decisions: list[str]
    summary: str | None
    generated_at: datetime

    model_config = {"from_attributes": True}
