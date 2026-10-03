from sqlalchemy import Column, DateTime, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id, utcnow


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("name", name="uq_workspace_name"),)

    id = Column(String(36), primary_key=True, default=new_id)
    name = Column(String(160), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    users = relationship("User", back_populates="workspace")