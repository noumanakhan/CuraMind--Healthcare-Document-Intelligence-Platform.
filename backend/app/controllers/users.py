from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models import AuditEvent, RefreshSession, User
from app.schemas import UserListResponse, UserResponse, UserRoleUpdate, UserStatusUpdate
from app.services.audit import write_audit

router = APIRouter()


@router.get("/users", response_model=UserListResponse)
def list_users(user: User = Depends(require_permission("users:manage")), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.workspace_id == user.workspace_id).order_by(User.created_at.asc()).all()
    return UserListResponse(users=[UserResponse.model_validate(item) for item in users])


@router.patch("/users/{target_user_id}/role", response_model=UserResponse)
def update_user_role(
    target_user_id: str,
    payload: UserRoleUpdate,
    actor: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == target_user_id, User.workspace_id == actor.workspace_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == actor.id and payload.role != "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot remove your own administrator role")
    if target.role == "admin" and payload.role != "admin":
        admin_count = db.query(User).filter(
            User.workspace_id == actor.workspace_id,
            User.role == "admin",
            User.is_active.is_(True),
        ).count()
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The workspace must retain at least one active administrator")

    previous_role = target.role
    target.role = payload.role
    write_audit(db, "user.role_changed", actor, target_user_id=target.id, detail=f"{previous_role} -> {payload.role}")
    db.commit()
    db.refresh(target)
    return UserResponse.model_validate(target)


@router.patch("/users/{target_user_id}/status", response_model=UserResponse)
def update_user_status(
    target_user_id: str,
    payload: UserStatusUpdate,
    actor: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == target_user_id, User.workspace_id == actor.workspace_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == actor.id and not payload.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")
    if target.role == "admin" and target.is_active and not payload.is_active:
        admin_count = db.query(User).filter(
            User.workspace_id == actor.workspace_id,
            User.role == "admin",
            User.is_active.is_(True),
        ).count()
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The workspace must retain at least one active administrator")

    target.is_active = payload.is_active
    if not payload.is_active:
        db.query(RefreshSession).filter(
            RefreshSession.user_id == target.id,
            RefreshSession.revoked_at.is_(None),
        ).update({RefreshSession.revoked_at: datetime.now(timezone.utc)})
    write_audit(db, "user.status_changed", actor, target_user_id=target.id, detail=f"is_active={payload.is_active}")
    db.commit()
    db.refresh(target)
    return UserResponse.model_validate(target)


@router.get("/admin/auth-audit")
def auth_audit(user: User = Depends(require_permission("users:manage")), db: Session = Depends(get_db)):
    events = db.query(AuditEvent).filter(AuditEvent.workspace_id == user.workspace_id).order_by(AuditEvent.created_at.desc()).limit(200).all()
    return [{
        "id": event.id,
        "actor_user_id": event.actor_user_id,
        "target_user_id": event.target_user_id,
        "action": event.action,
        "detail": event.detail,
        "created_at": event.created_at,
    } for event in events]