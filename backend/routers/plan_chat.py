from datetime import datetime
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.dependencies import get_db, get_current_user
from backend.models.user import User
from backend.models.thread import Thread
from backend.models.membership import GroupMembership
from backend.models.plan_message import PlanMessage
from backend.models.plan import Plan
from backend.services.ai_service import plan_chat_reply, get_plan_chat_stream, extract_plan_update
from backend.database.engine import SessionLocal
from backend.utils.exceptions import NotFoundError, ForbiddenError

router = APIRouter(prefix="/plan-chat", tags=["plan-chat"])


class PlanChatRequest(BaseModel):
    message: str


class PlanMessageOut(BaseModel):
    id: int
    role: str
    content: str
    username: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlanChatResponse(BaseModel):
    message: PlanMessageOut
    ai_message: PlanMessageOut
    plan: dict


def _assert_access(db: Session, thread_id: int, user_id: int) -> Thread:
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


@router.get("/{thread_id}", response_model=list[PlanMessageOut])
def get_plan_chat_history(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(db, thread_id, current_user.id)
    messages = (
        db.query(PlanMessage)
        .filter(PlanMessage.thread_id == thread_id)
        .order_by(PlanMessage.created_at.asc())
        .all()
    )
    result = []
    for msg in messages:
        username = msg.user.username if msg.user else "GroupThink AI"
        result.append(PlanMessageOut(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            username=username,
            created_at=msg.created_at,
        ))
    return result


@router.post("/{thread_id}", response_model=PlanChatResponse, status_code=status.HTTP_200_OK)
def send_plan_chat_message(
    thread_id: int,
    body: PlanChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(db, thread_id, current_user.id)

    # Get current plan for context
    existing_plan = db.query(Plan).filter(Plan.thread_id == thread_id).first()
    current_plan_dict = None
    if existing_plan:
        current_plan_dict = {
            "goals": existing_plan.goals,
            "action_items": existing_plan.action_items,
            "decisions": existing_plan.decisions,
            "summary": existing_plan.summary,
        }

    # Save user message
    user_msg = PlanMessage(
        thread_id=thread_id,
        role="user",
        content=body.message,
        user_id=current_user.id,
    )
    db.add(user_msg)
    db.flush()

    # Get AI response
    result = plan_chat_reply(db, thread_id, body.message, current_user.username, current_plan_dict)
    reply_text = result.get("reply", "")
    updated_plan = result.get("plan", {})

    # Save AI message
    ai_msg = PlanMessage(
        thread_id=thread_id,
        role="assistant",
        content=reply_text,
        user_id=None,
    )
    db.add(ai_msg)
    db.flush()

    # Upsert the plan
    if existing_plan:
        existing_plan.goals = updated_plan.get("goals", existing_plan.goals)
        existing_plan.action_items = updated_plan.get("action_items", existing_plan.action_items)
        existing_plan.decisions = updated_plan.get("decisions", existing_plan.decisions)
        existing_plan.summary = updated_plan.get("summary", existing_plan.summary)
    else:
        existing_plan = Plan(
            thread_id=thread_id,
            goals=updated_plan.get("goals", []),
            action_items=updated_plan.get("action_items", []),
            decisions=updated_plan.get("decisions", []),
            summary=updated_plan.get("summary"),
        )
        db.add(existing_plan)

    db.commit()
    db.refresh(user_msg)
    db.refresh(ai_msg)

    return PlanChatResponse(
        message=PlanMessageOut(
            id=user_msg.id,
            role="user",
            content=user_msg.content,
            username=current_user.username,
            created_at=user_msg.created_at,
        ),
        ai_message=PlanMessageOut(
            id=ai_msg.id,
            role="assistant",
            content=reply_text,
            username="GroupThink AI",
            created_at=ai_msg.created_at,
        ),
        plan=updated_plan,
    )


@router.post("/{thread_id}/stream")
def stream_plan_chat_message(
    thread_id: int,
    body: PlanChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_access(db, thread_id, current_user.id)

    # Get current plan for context
    existing_plan = db.query(Plan).filter(Plan.thread_id == thread_id).first()
    current_plan_dict = None
    if existing_plan:
        current_plan_dict = {
            "goals": existing_plan.goals,
            "action_items": existing_plan.action_items,
            "decisions": existing_plan.decisions,
            "summary": existing_plan.summary,
        }

    # Build conversation history for AI
    history = (
        db.query(PlanMessage)
        .filter(PlanMessage.thread_id == thread_id)
        .order_by(PlanMessage.created_at.asc())
        .all()
    )
    messages_for_ai = [{"role": m.role, "content": m.content} for m in history]
    messages_for_ai.append({"role": "user", "content": f"[{current_user.username}]: {body.message}"})

    # Merge consecutive same-role messages
    merged: list[dict] = []
    for msg in messages_for_ai:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n" + msg["content"]
        else:
            merged.append(dict(msg))

    # Save user message now (before streaming starts)
    user_msg = PlanMessage(
        thread_id=thread_id,
        role="user",
        content=body.message,
        user_id=current_user.id,
    )
    db.add(user_msg)
    db.commit()

    # Snapshot values needed inside generator (no DB session in generator)
    thread_id_snap = thread_id
    username_snap = current_user.username

    def generate():
        import json as _json
        full_text = ""
        try:
            for token in get_plan_chat_stream(merged, current_plan_dict):
                full_text += token
                yield f"data: {_json.dumps({'type': 'delta', 'text': token})}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        # Save AI message and extract plan using a fresh DB session
        import json as _json
        db2 = SessionLocal()
        try:
            from backend.models.plan_message import PlanMessage as PM
            from backend.models.plan import Plan as PlanModel
            from datetime import datetime

            ai_msg = PM(thread_id=thread_id_snap, role="assistant", content=full_text, user_id=None)
            db2.add(ai_msg)
            db2.flush()

            # Extract updated plan using fast Haiku call
            all_msgs = merged + [{"role": "assistant", "content": full_text}]
            updated_plan = extract_plan_update(all_msgs, current_plan_dict)

            # Upsert plan
            existing = db2.query(PlanModel).filter(PlanModel.thread_id == thread_id_snap).first()
            if existing:
                existing.goals = updated_plan.get("goals", existing.goals)
                existing.action_items = updated_plan.get("action_items", existing.action_items)
                existing.decisions = updated_plan.get("decisions", existing.decisions)
                existing.summary = updated_plan.get("summary", existing.summary)
                existing.generated_at = datetime.utcnow()
            else:
                new_plan = PlanModel(
                    thread_id=thread_id_snap,
                    goals=updated_plan.get("goals", []),
                    action_items=updated_plan.get("action_items", []),
                    decisions=updated_plan.get("decisions", []),
                    summary=updated_plan.get("summary"),
                )
                db2.add(new_plan)
            db2.commit()

            yield f"data: {_json.dumps({'type': 'done', 'plan': updated_plan})}\n\n"
        except Exception:
            yield f"data: {_json.dumps({'type': 'done', 'plan': current_plan_dict or {}})}\n\n"
        finally:
            db2.close()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
