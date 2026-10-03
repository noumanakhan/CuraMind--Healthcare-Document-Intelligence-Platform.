from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id, utcnow


class Vitals(Base):
    __tablename__ = "vitals"

    id = Column(String(36), primary_key=True, default=new_id)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    bp = Column(String(32), nullable=False)
    hr = Column(Integer, nullable=False)
    temp = Column(Float, nullable=False)
    spo2 = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    recorded_by_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    patient = relationship("Patient", back_populates="vitals")
    workspace = relationship("Workspace")
    recorded_by = relationship("User")
