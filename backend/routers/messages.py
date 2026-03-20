from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.dependencies import get_db, get_current_user
from backend.models.user import User
from backend.models.thread import Thread
from backend.models.membership import GroupMembership
from backend.schemas.message import MessageOut
from backend.services.message_service import get_message_history
from backend.utils.exceptions import NotFoundError, ForbiddenError

router = APIRouter(prefix="/threads/{thread_id}/messages", tags=["messages"])


@router.get("", response_model=list[MessageOut])
def list_messages(
    thread_id: int,
    limit: int = Query(default=50, le=100),
    before_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise NotFoundError("Thread not found")
    membership = (
        db.query(GroupMembership)
        .filter(
            GroupMembership.group_id == thread.group_id,
            GroupMembership.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise ForbiddenError("You are not a member of this group")
    return get_message_history(db, thread_id, limit, before_id)
