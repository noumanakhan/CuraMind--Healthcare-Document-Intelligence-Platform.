from sqlalchemy import Column, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id


class LabTest(Base):
    __tablename__ = "lab_tests"

    id = Column(String(36), primary_key=True, default=new_id)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    test_name = Column(String(160), nullable=False)
    unit = Column(String(32), nullable=False)
    reference_low = Column(Float, nullable=True)
    reference_high = Column(Float, nullable=True)

    patient = relationship("Patient", back_populates="labs")
    workspace = relationship("Workspace")
    points = relationship("LabResultPoint", back_populates="lab_test", cascade="all, delete-orphan", order_by="LabResultPoint.recorded_at")
