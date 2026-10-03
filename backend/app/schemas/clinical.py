from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Allergies ---
class AllergyCreate(BaseModel):
    allergen: str


class AllergyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    allergen: str
    noted_by_id: str
    noted_at: datetime


# --- Extracted Fields ---
class ExtractedFieldCreate(BaseModel):
    label: str
    value: str
    confidence: float = 1.0
    flagged: bool = False


class ExtractedFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    label: str
    value: str
    confidence: float
    flagged: bool
    confirmed_by_id: Optional[str] = None
    confirmed_at: Optional[datetime] = None


# --- Documents ---
class DocumentCreate(BaseModel):
    name: str
    type: Literal[
        "lab_report",
        "clinical_note",
        "intake_form",
        "referral_letter",
        "insurance_claim",
        "prescription",
        "discharge_summary",
    ]
    source_file_url: Optional[str] = None
    fields: Optional[List[ExtractedFieldCreate]] = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    workspace_id: str
    name: str
    type: str
    status: str
    uploaded_by_id: str
    uploaded_at: datetime
    source_file_url: Optional[str] = None
    is_deleted: bool
    extracted_fields: List[ExtractedFieldOut] = []


# --- Medications ---
class MedicationCreate(BaseModel):
    name: str
    dose: str
    flag: Optional[Literal["none", "interaction", "dosage"]] = "none"
    flag_note: Optional[str] = None


class MedicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    workspace_id: str
    name: str
    dose: str
    flag: Optional[str] = None
    flag_note: Optional[str] = None
    reviewed_by_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    prescribed_at: datetime


# --- Labs ---
class LabResultPointCreate(BaseModel):
    value: float
    recorded_at: Optional[datetime] = None


class LabResultPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lab_test_id: str
    value: float
    recorded_at: datetime


class LabTestCreate(BaseModel):
    test_name: str
    unit: str
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    initial_value: Optional[float] = None


class LabTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    workspace_id: str
    test_name: str
    unit: str
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    points: List[LabResultPointOut] = []


# --- Appointments ---
class AppointmentCreate(BaseModel):
    type: str
    with_provider_name: str
    with_provider_id: Optional[str] = None
    date: str
    time: str


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    workspace_id: str
    type: str
    with_provider_id: Optional[str] = None
    with_provider_name: str
    date: str
    time: str
    status: str
    scheduled_by_id: str
    scheduled_at: datetime


# --- Discharge Drafts ---
class DischargeParagraphCreate(BaseModel):
    text: str
    source_citation: Optional[str] = None
    order_index: int = 0


class DischargeParagraphOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    discharge_draft_id: str
    text: str
    source_citation: Optional[str] = None
    order_index: int


class DischargeDraftCreate(BaseModel):
    paragraphs: List[DischargeParagraphCreate] = []


class DischargeDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    workspace_id: str
    status: str
    generated_at: datetime
    signed_by_id: Optional[str] = None
    signed_at: Optional[datetime] = None
    paragraphs: List[DischargeParagraphOut] = []


# --- Immunizations ---
class ImmunizationCreate(BaseModel):
    vaccine_name: str
    administered_date: str


class ImmunizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    workspace_id: str
    vaccine_name: str
    administered_date: str
    recorded_by_id: str


# --- Vitals ---
class VitalsCreate(BaseModel):
    bp: str
    hr: int
    temp: float
    spo2: int
    weight: float


class VitalsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    workspace_id: str
    bp: str
    hr: int
    temp: float
    spo2: int
    weight: float
    recorded_at: datetime
    recorded_by_id: str


# --- Patients ---
class PatientCreate(BaseModel):
    name: str
    dob: str
    sex: str
    blood_type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None
    attending_physician_id: Optional[str] = None
    ward: Optional[str] = None
    status: Optional[Literal["admitted", "discharge_pending", "discharged"]] = "admitted"
    allergies: Optional[List[str]] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    blood_type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None
    attending_physician_id: Optional[str] = None
    ward: Optional[str] = None
    status: Optional[Literal["admitted", "discharge_pending", "discharged"]] = None
    is_deleted: Optional[bool] = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    mrn: str
    name: str
    dob: str
    sex: str
    blood_type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None
    attending_physician_id: Optional[str] = None
    ward: Optional[str] = None
    status: str
    is_deleted: bool
    created_by_id: str
    created_at: datetime
    updated_at: datetime
    allergies: List[AllergyOut] = []


class PatientListOut(BaseModel):
    patients: List[PatientOut]
    total: int
    skip: int
    limit: int


# --- Audit Logs ---
class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: Optional[str] = None
    actor_user_id: Optional[str] = None
    action: str
    target_user_id: Optional[str] = None
    patient_id: Optional[str] = None
    detail: Optional[str] = None
    created_at: datetime


class AuditEventListOut(BaseModel):
    events: List[AuditEventOut]


# --- Dashboard Stats ---
class DashboardStatsOut(BaseModel):
    total_patients: int
    admitted: int
    discharge_pending: int
    discharged: int
    pending_reviews: int
    upcoming_appointments: int
