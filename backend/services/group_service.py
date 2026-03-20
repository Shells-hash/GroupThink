from sqlalchemy.orm import Session, joinedload
from backend.models.group import Group
from backend.models.membership import GroupMembership
from backend.models.user import User
from backend.utils.exceptions import NotFoundError, ForbiddenError, ConflictError


def create_group(db: Session, name: str, description: str | None, owner_id: int) -> Group:
    group = Group(name=name, description=description, owner_id=owner_id)
    db.add(group)
    db.flush()
    membership = GroupMembership(user_id=owner_id, group_id=group.id, role="owner")
    db.add(membership)
    db.commit()
    db.refresh(group)
    return group


def get_user_groups(db: Session, user_id: int) -> list[Group]:
    return (
        db.query(Group)
        .join(GroupMembership, GroupMembership.group_id == Group.id)
        .filter(GroupMembership.user_id == user_id)
        .all()
    )


def get_group_detail(db: Session, group_id: int, user_id: int) -> Group:
    group = (
        db.query(Group)
        .options(joinedload(Group.memberships).joinedload(GroupMembership.user))
        .filter(Group.id == group_id)
        .first()
    )
    if not group:
        raise NotFoundError("Group not found")
    _assert_member(db, group_id, user_id)
    return group


def invite_user(db: Session, group_id: int, inviter_id: int, username: str) -> GroupMembership:
    _assert_member(db, group_id, inviter_id)
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise NotFoundError(f"User '{username}' not found")
    existing = (
        db.query(GroupMembership)
        .filter(GroupMembership.user_id == target.id, GroupMembership.group_id == group_id)
        .first()
    )
    if existing:
        raise ConflictError(f"'{username}' is already a member")
    membership = GroupMembership(user_id=target.id, group_id=group_id, role="member")
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def remove_member(db: Session, group_id: int, actor_id: int, target_user_id: int) -> None:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise NotFoundError("Group not found")
    # Members can leave themselves; owners can remove anyone
    if actor_id != target_user_id and group.owner_id != actor_id:
        raise ForbiddenError("Only the group owner can remove other members")
    membership = (
        db.query(GroupMembership)
        .filter(GroupMembership.user_id == target_user_id, GroupMembership.group_id == group_id)
        .first()
    )
    if not membership:
        raise NotFoundError("Membership not found")
    db.delete(membership)
    db.commit()


def delete_group(db: Session, group_id: int, user_id: int) -> None:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise NotFoundError("Group not found")
    if group.owner_id != user_id:
        raise ForbiddenError("Only the owner can delete a group")
    db.delete(group)
    db.commit()


def _assert_member(db: Session, group_id: int, user_id: int) -> GroupMembership:
    membership = (
        db.query(GroupMembership)
        .filter(GroupMembership.user_id == user_id, GroupMembership.group_id == group_id)
        .first()
    )
    if not membership:
        raise ForbiddenError("You are not a member of this group")
    return membership
