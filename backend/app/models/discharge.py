from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id, utcnow


class DischargeDraft(Base):
    __tablename__ = "discharge_drafts"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'signed')", name="ck_discharge_status"),
    )

    id = Column(String(36), primary_key=True, default=new_id)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="draft")
    generated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    signed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    signed_at = Column(DateTime(timezone=True), nullable=True)

    patient = relationship("Patient", back_populates="discharge_draft")
    workspace = relationship("Workspace")
    signed_by = relationship("User")
    paragraphs = relationship("DischargeParagraph", back_populates="discharge_draft", cascade="all, delete-orphan", order_by="DischargeParagraph.order_index")


class DischargeParagraph(Base):
    __tablename__ = "discharge_paragraphs"

    id = Column(String(36), primary_key=True, default=new_id)
    discharge_draft_id = Column(String(36), ForeignKey("discharge_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    source_citation = Column(String(255), nullable=True)
    order_index = Column(Integer, nullable=False, default=0)

    discharge_draft = relationship("DischargeDraft", back_populates="paragraphs")
