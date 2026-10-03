from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditEvent, User


def write_audit(
    db: Session,
    action: str,
    user: Optional[User] = None,
    target_user_id: Optional[str] = None,
    detail: Optional[str] = None,
    patient_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> None:
    ws_id = workspace_id or (user.workspace_id if user else None)
    db.add(AuditEvent(
        workspace_id=ws_id,
        actor_user_id=user.id if user else None,
        action=action,
        target_user_id=target_user_id,
        patient_id=patient_id,
        detail=detail,
    ))