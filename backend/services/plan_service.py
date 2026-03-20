from sqlalchemy.orm import Session
from backend.models.plan import Plan
from backend.services.ai_service import generate_plan
from backend.utils.exceptions import NotFoundError


def get_plan(db: Session, thread_id: int) -> Plan:
    plan = db.query(Plan).filter(Plan.thread_id == thread_id).first()
    if not plan:
        raise NotFoundError("No plan generated yet for this thread")
    return plan


def generate_and_save_plan(db: Session, thread_id: int) -> Plan:
    data = generate_plan(db, thread_id)

    plan = db.query(Plan).filter(Plan.thread_id == thread_id).first()
    if plan:
        plan.goals = data.get("goals", [])
        plan.action_items = data.get("action_items", [])
        plan.decisions = data.get("decisions", [])
        plan.summary = data.get("summary")
    else:
        plan = Plan(
            thread_id=thread_id,
            goals=data.get("goals", []),
            action_items=data.get("action_items", []),
            decisions=data.get("decisions", []),
            summary=data.get("summary"),
        )
        db.add(plan)

    db.commit()
    db.refresh(plan)
    return plan
