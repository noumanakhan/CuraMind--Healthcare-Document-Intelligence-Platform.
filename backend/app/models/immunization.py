from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id


class Immunization(Base):
    __tablename__ = "immunizations"

    id = Column(String(36), primary_key=True, default=new_id)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    vaccine_name = Column(String(160), nullable=False)
    administered_date = Column(String(32), nullable=False)
    recorded_by_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    patient = relationship("Patient", back_populates="immunizations")
    workspace = relationship("Workspace")
    recorded_by = relationship("User")
