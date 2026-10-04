from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id, utcnow


class LabResultPoint(Base):
    __tablename__ = "lab_result_points"

    id = Column(String(36), primary_key=True, default=new_id)
    lab_test_id = Column(String(36), ForeignKey("lab_tests.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    lab_test = relationship("LabTest", back_populates="points")
