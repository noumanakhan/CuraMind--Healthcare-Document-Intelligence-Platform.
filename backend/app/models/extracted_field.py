from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(String(36), primary_key=True, default=new_id)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(160), nullable=False)
    value = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    flagged = Column(Boolean, nullable=False, default=False)
    confirmed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    document = relationship("Document", back_populates="extracted_fields")
    confirmed_by = relationship("User")
