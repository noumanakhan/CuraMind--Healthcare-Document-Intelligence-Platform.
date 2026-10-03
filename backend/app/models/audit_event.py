from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from app.db.session import Base
from app.models.identifiers import new_id, utcnow


class AuditEvent(Base):
    __tablename__ = "auth_audit_events"

    id = Column(String(36), primary_key=True, default=new_id)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True)
    actor_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    target_user_id = Column(String(36), nullable=True, index=True)
    patient_id = Column(String(36), nullable=True, index=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)