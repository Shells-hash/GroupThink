from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.dependencies import get_db, get_current_user
from backend.models.user import User
from backend.models.thread import Thread
from backend.models.membership import GroupMembership
from backend.schemas.plan import PlanOut, ActionItem
from backend.services.plan_service import get_plan, generate_and_save_plan
from backend.utils.exceptions import NotFoundError, ForbiddenError

router = APIRouter(prefix="/plans", tags=["plans"])


def _assert_thread_access(db: Session, thread_id: int, user_id: int) -> Thread:
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise NotFoundError("Thread not found")
    membership = (
        db.query(GroupMembership)
        .filter(
            GroupMembership.group_id == thread.group_id,
            GroupMembership.user_id == user_id,
        )
        .first()
    )
    if not membership:
        raise ForbiddenError("You are not a member of this group")
    return thread


def _plan_to_out(plan) -> PlanOut:
    return PlanOut(
        id=plan.id,
        thread_id=plan.thread_id,
        goals=plan.goals,
        action_items=[ActionItem(**item) if isinstance(item, dict) else item for item in plan.action_items],
        decisions=plan.decisions,
        summary=plan.summary,
        generated_at=plan.generated_at,
    )


@router.get("/{thread_id}", response_model=PlanOut)
def get_thread_plan(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_thread_access(db, thread_id, current_user.id)
    plan = get_plan(db, thread_id)
    return _plan_to_out(plan)


@router.post("/{thread_id}/generate", response_model=PlanOut, status_code=status.HTTP_200_OK)
def generate_plan_endpoint(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_thread_access(db, thread_id, current_user.id)
    plan = generate_and_save_plan(db, thread_id)
    return _plan_to_out(plan)
