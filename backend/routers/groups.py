from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.dependencies import get_db, get_current_user
from backend.models.user import User
from backend.schemas.group import GroupCreate, GroupOut, GroupDetail, InviteRequest, MemberOut
from backend.services import group_service

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return group_service.get_user_groups(db, current_user.id)


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    body: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return group_service.create_group(db, body.name, body.description, current_user.id)


@router.get("/{group_id}", response_model=GroupDetail)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = group_service.get_group_detail(db, group_id, current_user.id)
    members = [MemberOut(user=m.user, role=m.role, joined_at=m.joined_at) for m in group.memberships]
    return GroupDetail(
        id=group.id,
        name=group.name,
        description=group.description,
        owner_id=group.owner_id,
        created_at=group.created_at,
        members=members,
    )


@router.post("/{group_id}/invite", status_code=status.HTTP_201_CREATED)
def invite_member(
    group_id: int,
    body: InviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group_service.invite_user(db, group_id, current_user.id, body.username)
    return {"detail": f"'{body.username}' added to group"}


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group_service.remove_member(db, group_id, current_user.id, user_id)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group_service.delete_group(db, group_id, current_user.id)
