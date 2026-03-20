from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.dependencies import get_db, get_current_user
from backend.models.user import User
from backend.models.thread import Thread
from backend.models.membership import GroupMembership
from backend.schemas.thread import ThreadCreate, ThreadOut
from backend.utils.exceptions import NotFoundError, ForbiddenError

router = APIRouter(prefix="/groups/{group_id}/threads", tags=["threads"])


def _assert_member(db: Session, group_id: int, user_id: int) -> None:
    m = (
        db.query(GroupMembership)
        .filter(GroupMembership.group_id == group_id, GroupMembership.user_id == user_id)
        .first()
    )
    if not m:
        raise ForbiddenError("You are not a member of this group")


@router.get("", response_model=list[ThreadOut])
def list_threads(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_member(db, group_id, current_user.id)
    return db.query(Thread).filter(Thread.group_id == group_id).all()


@router.post("", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(
    group_id: int,
    body: ThreadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_member(db, group_id, current_user.id)
    thread = Thread(group_id=group_id, title=body.title, created_by=current_user.id)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(
    group_id: int,
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = db.query(Thread).filter(Thread.id == thread_id, Thread.group_id == group_id).first()
    if not thread:
        raise NotFoundError("Thread not found")
    from backend.models.group import Group
    group = db.query(Group).filter(Group.id == group_id).first()
    if thread.created_by != current_user.id and group.owner_id != current_user.id:
        raise ForbiddenError("Only the thread creator or group owner can delete this thread")
    db.delete(thread)
    db.commit()
