from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id, utcnow


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("workspace_id", "mrn", name="uq_workspace_patient_mrn"),
        CheckConstraint("status IN ('admitted', 'discharge_pending', 'discharged')", name="ck_patient_status"),
    )

    id = Column(String(36), primary_key=True, default=new_id)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    mrn = Column(String(64), nullable=False, index=True)
    name = Column(String(160), nullable=False, index=True)
    dob = Column(String(32), nullable=False)
    sex = Column(String(32), nullable=False)
    blood_type = Column(String(16), nullable=True)
    phone = Column(String(64), nullable=True)
    email = Column(String(320), nullable=True)
    address = Column(String(255), nullable=True)
    emergency_contact = Column(String(255), nullable=True)
    insurance_provider = Column(String(160), nullable=True)
    policy_number = Column(String(64), nullable=True)
    attending_physician_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    ward = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="admitted")
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    workspace = relationship("Workspace")
    attending_physician = relationship("User", foreign_keys=[attending_physician_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    allergies = relationship("Allergy", back_populates="patient", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="patient", cascade="all, delete-orphan")
    labs = relationship("LabTest", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    discharge_draft = relationship("DischargeDraft", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    immunizations = relationship("Immunization", back_populates="patient", cascade="all, delete-orphan")
    vitals = relationship("Vitals", back_populates="patient", cascade="all, delete-orphan")
