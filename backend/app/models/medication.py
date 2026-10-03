from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id, utcnow


class Medication(Base):
    __tablename__ = "medications"
    __table_args__ = (
        CheckConstraint("flag IS NULL OR flag IN ('none', 'interaction', 'dosage')", name="ck_medication_flag"),
    )

    id = Column(String(36), primary_key=True, default=new_id)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    dose = Column(String(64), nullable=False)
    flag = Column(String(32), nullable=True)
    flag_note = Column(Text, nullable=True)
    reviewed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    prescribed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    patient = relationship("Patient", back_populates="medications")
    workspace = relationship("Workspace")
    reviewed_by = relationship("User")
