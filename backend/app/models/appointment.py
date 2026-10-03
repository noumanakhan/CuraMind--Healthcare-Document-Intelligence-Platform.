from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id, utcnow


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("status IN ('upcoming', 'completed', 'cancelled')", name="ck_appointment_status"),
    )

    id = Column(String(36), primary_key=True, default=new_id)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(64), nullable=False)
    with_provider_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    with_provider_name = Column(String(160), nullable=False)
    date = Column(String(32), nullable=False)
    time = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="upcoming")
    scheduled_by_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    patient = relationship("Patient", back_populates="appointments")
    workspace = relationship("Workspace")
    with_provider = relationship("User", foreign_keys=[with_provider_id])
    scheduled_by = relationship("User", foreign_keys=[scheduled_by_id])
