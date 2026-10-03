from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id, utcnow


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(String(36), primary_key=True, default=new_id)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    allergen = Column(String(160), nullable=False)
    noted_by_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    noted_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    patient = relationship("Patient", back_populates="allergies")
    noted_by = relationship("User")
