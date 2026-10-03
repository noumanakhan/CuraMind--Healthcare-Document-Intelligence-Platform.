from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_permission
from app.db.session import get_db
from app.models import User
from app.schemas.clinical import (
    AppointmentCreate,
    AppointmentOut,
    AuditEventListOut,
    AuditEventOut,
    DashboardStatsOut,
    DischargeDraftOut,
    DocumentCreate,
    DocumentOut,
    ExtractedFieldOut,
    ImmunizationCreate,
    ImmunizationOut,
    LabResultPointCreate,
    LabResultPointOut,
    LabTestOut,
    MedicationOut,
    PatientCreate,
    PatientListOut,
    PatientOut,
    PatientUpdate,
    VitalsCreate,
    VitalsOut,
)
from app.services import clinical as clinical_service

router = APIRouter()


# --- Patients ---

@router.get("/patients", response_model=PatientListOut)
def get_patients(
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(require_permission("patients:view")),
    db: Session = Depends(get_db),
):
    items, total = clinical_service.list_patients(
        db,
        workspace_id=user.workspace_id,
        status_filter=status,
        search=search,
        skip=skip,
        limit=limit,
    )
    return PatientListOut(
        patients=[PatientOut.model_validate(p) for p in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/patients", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    user: User = Depends(require_permission("patients:create")),
    db: Session = Depends(get_db),
):
    patient = clinical_service.create_patient(db, workspace_id=user.workspace_id, user=user, data=payload)
    return PatientOut.model_validate(patient)


@router.get("/patients/{id}", response_model=PatientOut)
def get_patient(
    id: str,
    user: User = Depends(require_permission("patients:view")),
    db: Session = Depends(get_db),
):
    patient = clinical_service.get_patient(db, workspace_id=user.workspace_id, patient_id=id)
    return PatientOut.model_validate(patient)


@router.patch("/patients/{id}", response_model=PatientOut)
def update_patient(
    id: str,
    payload: PatientUpdate,
    user: User = Depends(require_permission("patients:edit")),
    db: Session = Depends(get_db),
):
    patient = clinical_service.update_patient(
        db,
        workspace_id=user.workspace_id,
        patient_id=id,
        user=user,
        data=payload,
    )
    return PatientOut.model_validate(patient)


# --- Documents & Field Confirmation ---

@router.get("/patients/{id}/documents", response_model=List[DocumentOut])
def get_patient_documents(
    id: str,
    user: User = Depends(require_permission("documents:view")),
    db: Session = Depends(get_db),
):
    docs = clinical_service.list_documents(db, workspace_id=user.workspace_id, patient_id=id)
    return [DocumentOut.model_validate(d) for d in docs]


@router.post("/patients/{id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_patient_document(
    id: str,
    payload: DocumentCreate,
    user: User = Depends(require_permission("documents:create")),
    db: Session = Depends(get_db),
):
    doc = clinical_service.create_document(
        db,
        workspace_id=user.workspace_id,
        patient_id=id,
        user=user,
        data=payload,
    )
    return DocumentOut.model_validate(doc)


@router.patch("/documents/{doc_id}/fields/{field_id}/confirm", response_model=ExtractedFieldOut)
def confirm_document_field(
    doc_id: str,
    field_id: str,
    user: User = Depends(require_permission("fields:confirm")),
    db: Session = Depends(get_db),
):
    field = clinical_service.confirm_field(
        db,
        workspace_id=user.workspace_id,
        doc_id=doc_id,
        field_id=field_id,
        user=user,
    )
    return ExtractedFieldOut.model_validate(field)


# --- Medications ---

@router.get("/patients/{id}/medications", response_model=List[MedicationOut])
def get_patient_medications(
    id: str,
    user: User = Depends(require_permission("patients:view")),
    db: Session = Depends(get_db),
):
    meds = clinical_service.list_medications(db, workspace_id=user.workspace_id, patient_id=id)
    return [MedicationOut.model_validate(m) for m in meds]


@router.patch("/medications/{id}/review", response_model=MedicationOut)
def review_medication(
    id: str,
    user: User = Depends(require_permission("medications:review")),
    db: Session = Depends(get_db),
):
    med = clinical_service.review_medication(
        db,
        workspace_id=user.workspace_id,
        med_id=id,
        user=user,
    )
    return MedicationOut.model_validate(med)


# --- Labs ---

@router.get("/patients/{id}/labs", response_model=List[LabTestOut])
def get_patient_labs(
    id: str,
    user: User = Depends(require_permission("patients:view")),
    db: Session = Depends(get_db),
):
    labs = clinical_service.list_labs(db, workspace_id=user.workspace_id, patient_id=id)
    return [LabTestOut.model_validate(l) for l in labs]


@router.post("/patients/{id}/labs/{test_id}/points", response_model=LabResultPointOut, status_code=status.HTTP_201_CREATED)
def add_lab_test_point(
    id: str,
    test_id: str,
    payload: LabResultPointCreate,
    user: User = Depends(require_permission("labs:record")),
    db: Session = Depends(get_db),
):
    point = clinical_service.add_lab_point(
        db,
        workspace_id=user.workspace_id,
        test_id=test_id,
        user=user,
        data=payload,
    )
    return LabResultPointOut.model_validate(point)


# --- Appointments ---

@router.get("/patients/{id}/appointments", response_model=List[AppointmentOut])
def get_patient_appointments(
    id: str,
    user: User = Depends(require_permission("appointments:view")),
    db: Session = Depends(get_db),
):
    appts = clinical_service.list_appointments(db, workspace_id=user.workspace_id, patient_id=id)
    return [AppointmentOut.model_validate(a) for a in appts]


@router.post("/patients/{id}/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_patient_appointment(
    id: str,
    payload: AppointmentCreate,
    user: User = Depends(require_permission("appointments:manage")),
    db: Session = Depends(get_db),
):
    appt = clinical_service.create_appointment(
        db,
        workspace_id=user.workspace_id,
        patient_id=id,
        user=user,
        data=payload,
    )
    return AppointmentOut.model_validate(appt)


# --- Discharge Draft ---

@router.get("/patients/{id}/discharge", response_model=DischargeDraftOut)
def get_patient_discharge(
    id: str,
    user: User = Depends(require_permission("clinical:chart_view")),
    db: Session = Depends(get_db),
):
    draft = clinical_service.get_discharge(db, workspace_id=user.workspace_id, patient_id=id)
    return DischargeDraftOut.model_validate(draft)


@router.post("/patients/{id}/discharge/sign", response_model=DischargeDraftOut)
def sign_patient_discharge(
    id: str,
    user: User = Depends(require_permission("discharge:sign")),
    db: Session = Depends(get_db),
):
    draft = clinical_service.sign_discharge(
        db,
        workspace_id=user.workspace_id,
        patient_id=id,
        user=user,
    )
    return DischargeDraftOut.model_validate(draft)


# --- Immunizations & Vitals ---

@router.get("/patients/{id}/immunizations", response_model=List[ImmunizationOut])
def get_patient_immunizations(
    id: str,
    user: User = Depends(require_permission("patients:view")),
    db: Session = Depends(get_db),
):
    imms = clinical_service.list_immunizations(db, workspace_id=user.workspace_id, patient_id=id)
    return [ImmunizationOut.model_validate(i) for i in imms]


@router.get("/patients/{id}/vitals/latest", response_model=Optional[VitalsOut])
def get_latest_patient_vitals(
    id: str,
    user: User = Depends(require_permission("patients:view")),
    db: Session = Depends(get_db),
):
    vitals = clinical_service.get_latest_vitals(db, workspace_id=user.workspace_id, patient_id=id)
    return VitalsOut.model_validate(vitals) if vitals else None


@router.post("/patients/{id}/vitals", response_model=VitalsOut, status_code=status.HTTP_201_CREATED)
def record_patient_vitals(
    id: str,
    payload: VitalsCreate,
    user: User = Depends(require_permission("vitals:record")),
    db: Session = Depends(get_db),
):
    vitals = clinical_service.record_vitals(
        db,
        workspace_id=user.workspace_id,
        patient_id=id,
        user=user,
        data=payload,
    )
    return VitalsOut.model_validate(vitals)


# --- Patient Audit Logs & Dashboard Stats ---

@router.get("/patients/{id}/audit", response_model=AuditEventListOut)
def get_patient_audit(
    id: str,
    user: User = Depends(require_permission("audit:view")),
    db: Session = Depends(get_db),
):
    events = clinical_service.list_patient_audit_events(db, workspace_id=user.workspace_id, patient_id=id)
    return AuditEventListOut(events=[AuditEventOut.model_validate(e) for e in events])


@router.get("/dashboard/stats", response_model=DashboardStatsOut)
def get_dashboard_statistics(
    user: User = Depends(require_permission("patients:view")),
    db: Session = Depends(get_db),
):
    stats = clinical_service.get_dashboard_stats(db, workspace_id=user.workspace_id)
    return DashboardStatsOut(**stats)
