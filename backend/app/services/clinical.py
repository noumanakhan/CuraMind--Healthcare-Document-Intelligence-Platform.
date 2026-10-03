import random
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Allergy,
    Appointment,
    AuditEvent,
    DischargeDraft,
    DischargeParagraph,
    Document,
    ExtractedField,
    Immunization,
    LabResultPoint,
    LabTest,
    Medication,
    Patient,
    User,
    Vitals,
)
from app.models.identifiers import utcnow
from app.schemas.clinical import (
    AllergyCreate,
    AppointmentCreate,
    DischargeDraftCreate,
    DocumentCreate,
    ImmunizationCreate,
    LabResultPointCreate,
    LabTestCreate,
    MedicationCreate,
    PatientCreate,
    PatientUpdate,
    VitalsCreate,
)
from app.services.audit import write_audit


def generate_unique_mrn(db: Session, workspace_id: str) -> str:
    """Generate a workspace-unique Medical Record Number (MRN)."""
    for _ in range(10):
        candidate = f"MRN-{random.randint(100000, 999999)}"
        existing = db.query(Patient).filter(
            Patient.workspace_id == workspace_id,
            Patient.mrn == candidate,
        ).first()
        if not existing:
            return candidate
    # Fallback with timestamp
    return f"MRN-{int(datetime.now(timezone.utc).timestamp())}"


# --- Patient Services ---

def list_patients(
    db: Session,
    workspace_id: str,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Patient], int]:
    query = db.query(Patient).filter(
        Patient.workspace_id == workspace_id,
        Patient.is_deleted.is_(False),
    )
    if status_filter:
        query = query.filter(Patient.status == status_filter)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            (Patient.name.ilike(pattern)) | (Patient.mrn.ilike(pattern))
        )
    total = query.count()
    items = query.order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def create_patient(db: Session, workspace_id: str, user: User, data: PatientCreate) -> Patient:
    mrn = generate_unique_mrn(db, workspace_id)
    patient = Patient(
        workspace_id=workspace_id,
        mrn=mrn,
        name=data.name.strip(),
        dob=data.dob.strip(),
        sex=data.sex.strip(),
        blood_type=data.blood_type,
        phone=data.phone,
        email=data.email,
        address=data.address,
        emergency_contact=data.emergency_contact,
        insurance_provider=data.insurance_provider,
        policy_number=data.policy_number,
        attending_physician_id=data.attending_physician_id,
        ward=data.ward,
        status=data.status or "admitted",
        created_by_id=user.id,
    )
    db.add(patient)
    db.flush()

    if data.allergies:
        for allergen in data.allergies:
            if allergen.strip():
                allergy = Allergy(
                    patient_id=patient.id,
                    allergen=allergen.strip(),
                    noted_by_id=user.id,
                )
                db.add(allergy)

    write_audit(
        db,
        action="patient.created",
        user=user,
        patient_id=patient.id,
        detail=f"Created patient {patient.name} ({patient.mrn})",
    )
    db.commit()
    db.refresh(patient)
    return patient


def get_patient(db: Session, workspace_id: str, patient_id: str, include_deleted: bool = False) -> Patient:
    query = db.query(Patient).filter(
        Patient.workspace_id == workspace_id,
        Patient.id == patient_id,
    )
    if not include_deleted:
        query = query.filter(Patient.is_deleted.is_(False))
    patient = query.first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found in this workspace")
    return patient


def update_patient(db: Session, workspace_id: str, patient_id: str, user: User, data: PatientUpdate) -> Patient:
    patient = get_patient(db, workspace_id, patient_id, include_deleted=True)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)
    
    action = "patient.deleted" if update_data.get("is_deleted") is True else "patient.updated"
    write_audit(
        db,
        action=action,
        user=user,
        patient_id=patient.id,
        detail=f"Updated patient {patient.name} ({patient.mrn})",
    )
    db.commit()
    db.refresh(patient)
    return patient


# --- Document & Field Services ---

def list_documents(db: Session, workspace_id: str, patient_id: str) -> List[Document]:
    # Ensure patient is in workspace
    get_patient(db, workspace_id, patient_id)
    return db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.patient_id == patient_id,
        Document.is_deleted.is_(False),
    ).order_by(Document.uploaded_at.desc()).all()


def create_document(db: Session, workspace_id: str, patient_id: str, user: User, data: DocumentCreate) -> Document:
    patient = get_patient(db, workspace_id, patient_id)
    document = Document(
        patient_id=patient.id,
        workspace_id=workspace_id,
        name=data.name.strip(),
        type=data.type,
        status="processed" if not data.fields else "needs_review",
        uploaded_by_id=user.id,
        source_file_url=data.source_file_url,
    )
    db.add(document)
    db.flush()

    if data.fields:
        for f in data.fields:
            field = ExtractedField(
                document_id=document.id,
                label=f.label,
                value=f.value,
                confidence=f.confidence,
                flagged=f.flagged,
            )
            db.add(field)

    write_audit(
        db,
        action="document.uploaded",
        user=user,
        patient_id=patient.id,
        detail=f"Uploaded document {document.name} ({document.type})",
    )
    db.commit()
    db.refresh(document)
    return document


def confirm_field(db: Session, workspace_id: str, doc_id: str, field_id: str, user: User) -> ExtractedField:
    document = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.id == doc_id,
        Document.is_deleted.is_(False),
    ).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    field = db.query(ExtractedField).filter(
        ExtractedField.document_id == document.id,
        ExtractedField.id == field_id,
    ).first()
    if not field:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extracted field not found")

    if field.confirmed_by_id is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Field has already been confirmed")

    field.confirmed_by_id = user.id
    field.confirmed_at = utcnow()
    field.flagged = False

    # Check if all fields in document are now confirmed
    remaining_unconfirmed = db.query(ExtractedField).filter(
        ExtractedField.document_id == document.id,
        ExtractedField.confirmed_by_id.is_(None),
    ).count()
    if remaining_unconfirmed == 0:
        document.status = "processed"

    write_audit(
        db,
        action="document.field_confirmed",
        user=user,
        patient_id=document.patient_id,
        detail=f"Confirmed extracted field '{field.label}' in {document.name}",
    )
    db.commit()
    db.refresh(field)
    return field


# --- Medication Services ---

def list_medications(db: Session, workspace_id: str, patient_id: str) -> List[Medication]:
    get_patient(db, workspace_id, patient_id)
    return db.query(Medication).filter(
        Medication.workspace_id == workspace_id,
        Medication.patient_id == patient_id,
    ).order_by(Medication.prescribed_at.desc()).all()


def create_medication(db: Session, workspace_id: str, patient_id: str, user: User, data: MedicationCreate) -> Medication:
    patient = get_patient(db, workspace_id, patient_id)
    med = Medication(
        patient_id=patient.id,
        workspace_id=workspace_id,
        name=data.name.strip(),
        dose=data.dose.strip(),
        flag=data.flag or "none",
        flag_note=data.flag_note,
    )
    db.add(med)
    write_audit(
        db,
        action="medication.prescribed",
        user=user,
        patient_id=patient.id,
        detail=f"Prescribed medication {med.name} ({med.dose})",
    )
    db.commit()
    db.refresh(med)
    return med


def review_medication(db: Session, workspace_id: str, med_id: str, user: User) -> Medication:
    med = db.query(Medication).filter(
        Medication.workspace_id == workspace_id,
        Medication.id == med_id,
    ).first()
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")

    med.reviewed_by_id = user.id
    med.reviewed_at = utcnow()
    write_audit(
        db,
        action="medication.reviewed",
        user=user,
        patient_id=med.patient_id,
        detail=f"Marked medication {med.name} as reviewed",
    )
    db.commit()
    db.refresh(med)
    return med


# --- Lab Services ---

def list_labs(db: Session, workspace_id: str, patient_id: str) -> List[LabTest]:
    get_patient(db, workspace_id, patient_id)
    return db.query(LabTest).filter(
        LabTest.workspace_id == workspace_id,
        LabTest.patient_id == patient_id,
    ).all()


def add_lab_point(db: Session, workspace_id: str, test_id: str, user: User, data: LabResultPointCreate) -> LabResultPoint:
    test = db.query(LabTest).filter(
        LabTest.workspace_id == workspace_id,
        LabTest.id == test_id,
    ).first()
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab test not found")

    point = LabResultPoint(
        lab_test_id=test.id,
        value=data.value,
        recorded_at=data.recorded_at or utcnow(),
    )
    db.add(point)
    write_audit(
        db,
        action="lab.point_added",
        user=user,
        patient_id=test.patient_id,
        detail=f"Added result point {data.value} {test.unit} for {test.test_name}",
    )
    db.commit()
    db.refresh(point)
    return point


# --- Appointment Services ---

def list_appointments(db: Session, workspace_id: str, patient_id: Optional[str] = None) -> List[Appointment]:
    query = db.query(Appointment).filter(Appointment.workspace_id == workspace_id)
    if patient_id:
        get_patient(db, workspace_id, patient_id)
        query = query.filter(Appointment.patient_id == patient_id)
    return query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()


def create_appointment(db: Session, workspace_id: str, patient_id: str, user: User, data: AppointmentCreate) -> Appointment:
    patient = get_patient(db, workspace_id, patient_id)
    appointment = Appointment(
        patient_id=patient.id,
        workspace_id=workspace_id,
        type=data.type.strip(),
        with_provider_id=data.with_provider_id,
        with_provider_name=data.with_provider_name.strip(),
        date=data.date.strip(),
        time=data.time.strip(),
        scheduled_by_id=user.id,
    )
    db.add(appointment)
    write_audit(
        db,
        action="appointment.scheduled",
        user=user,
        patient_id=patient.id,
        detail=f"Scheduled {appointment.type} with {appointment.with_provider_name} on {appointment.date}",
    )
    db.commit()
    db.refresh(appointment)
    return appointment


# --- Discharge Services ---

def get_discharge(db: Session, workspace_id: str, patient_id: str) -> DischargeDraft:
    patient = get_patient(db, workspace_id, patient_id)
    draft = db.query(DischargeDraft).filter(
        DischargeDraft.workspace_id == workspace_id,
        DischargeDraft.patient_id == patient.id,
    ).first()
    if not draft:
        # Create initial default draft
        draft = DischargeDraft(
            patient_id=patient.id,
            workspace_id=workspace_id,
            status="draft",
        )
        db.add(draft)
        db.flush()
        # Default introductory paragraph
        p1 = DischargeParagraph(
            discharge_draft_id=draft.id,
            text=f"Patient {patient.name} was admitted and underwent comprehensive diagnostic evaluation and management.",
            source_citation="Admission Record",
            order_index=0,
        )
        db.add(p1)
        db.commit()
        db.refresh(draft)
    return draft


def sign_discharge(db: Session, workspace_id: str, patient_id: str, user: User) -> DischargeDraft:
    draft = get_discharge(db, workspace_id, patient_id)
    if draft.status == "signed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Discharge summary has already been signed")

    draft.status = "signed"
    draft.signed_by_id = user.id
    draft.signed_at = utcnow()

    # Update patient status to discharged
    patient = get_patient(db, workspace_id, patient_id)
    patient.status = "discharged"

    write_audit(
        db,
        action="discharge.signed",
        user=user,
        patient_id=patient.id,
        detail=f"Signed discharge summary for patient {patient.name}",
    )
    db.commit()
    db.refresh(draft)
    return draft


# --- Immunization & Vitals Services ---

def list_immunizations(db: Session, workspace_id: str, patient_id: str) -> List[Immunization]:
    get_patient(db, workspace_id, patient_id)
    return db.query(Immunization).filter(
        Immunization.workspace_id == workspace_id,
        Immunization.patient_id == patient_id,
    ).order_by(Immunization.administered_date.desc()).all()


def record_immunization(db: Session, workspace_id: str, patient_id: str, user: User, data: ImmunizationCreate) -> Immunization:
    patient = get_patient(db, workspace_id, patient_id)
    imm = Immunization(
        patient_id=patient.id,
        workspace_id=workspace_id,
        vaccine_name=data.vaccine_name.strip(),
        administered_date=data.administered_date.strip(),
        recorded_by_id=user.id,
    )
    db.add(imm)
    write_audit(
        db,
        action="immunization.recorded",
        user=user,
        patient_id=patient.id,
        detail=f"Recorded immunization {imm.vaccine_name}",
    )
    db.commit()
    db.refresh(imm)
    return imm


def get_latest_vitals(db: Session, workspace_id: str, patient_id: str) -> Optional[Vitals]:
    get_patient(db, workspace_id, patient_id)
    return db.query(Vitals).filter(
        Vitals.workspace_id == workspace_id,
        Vitals.patient_id == patient_id,
    ).order_by(Vitals.recorded_at.desc()).first()


def record_vitals(db: Session, workspace_id: str, patient_id: str, user: User, data: VitalsCreate) -> Vitals:
    patient = get_patient(db, workspace_id, patient_id)
    vitals = Vitals(
        patient_id=patient.id,
        workspace_id=workspace_id,
        bp=data.bp.strip(),
        hr=data.hr,
        temp=data.temp,
        spo2=data.spo2,
        weight=data.weight,
        recorded_by_id=user.id,
    )
    db.add(vitals)
    write_audit(
        db,
        action="vitals.recorded",
        user=user,
        patient_id=patient.id,
        detail=f"Recorded vitals: BP {vitals.bp}, HR {vitals.hr}, Temp {vitals.temp}",
    )
    db.commit()
    db.refresh(vitals)
    return vitals


# --- Audit & Dashboard Services ---

def list_patient_audit_events(db: Session, workspace_id: str, patient_id: str) -> List[AuditEvent]:
    # Ensure patient in workspace
    get_patient(db, workspace_id, patient_id)
    return db.query(AuditEvent).filter(
        AuditEvent.workspace_id == workspace_id,
        AuditEvent.patient_id == patient_id,
    ).order_by(AuditEvent.created_at.desc()).all()


def get_dashboard_stats(db: Session, workspace_id: str) -> dict:
    patients_q = db.query(Patient).filter(
        Patient.workspace_id == workspace_id,
        Patient.is_deleted.is_(False),
    )
    total_patients = patients_q.count()
    admitted = patients_q.filter(Patient.status == "admitted").count()
    discharge_pending = patients_q.filter(Patient.status == "discharge_pending").count()
    discharged = patients_q.filter(Patient.status == "discharged").count()

    pending_reviews = db.query(Document).filter(
        Document.workspace_id == workspace_id,
        Document.status == "needs_review",
        Document.is_deleted.is_(False),
    ).count()

    upcoming_appointments = db.query(Appointment).filter(
        Appointment.workspace_id == workspace_id,
        Appointment.status == "upcoming",
    ).count()

    return {
        "total_patients": total_patients,
        "admitted": admitted,
        "discharge_pending": discharge_pending,
        "discharged": discharged,
        "pending_reviews": pending_reviews,
        "upcoming_appointments": upcoming_appointments,
    }
