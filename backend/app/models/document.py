from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id, utcnow


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "type IN ('lab_report', 'clinical_note', 'intake_form', 'referral_letter', 'insurance_claim', 'prescription', 'discharge_summary')",
            name="ck_document_type",
        ),
        CheckConstraint("status IN ('processing', 'needs_review', 'processed')", name="ck_document_status"),
    )

    id = Column(String(36), primary_key=True, default=new_id)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="processing")
    uploaded_by_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    source_file_url = Column(String(512), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)

    patient = relationship("Patient", back_populates="documents")
    workspace = relationship("Workspace")
    uploaded_by = relationship("User")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
